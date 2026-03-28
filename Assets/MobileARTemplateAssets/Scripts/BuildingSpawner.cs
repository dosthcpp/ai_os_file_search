using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class BuildingSpawner : MonoBehaviour
{
    public WorldOrigin worldOrigin;
    public Material buildingMaterial;
    public GameObject buildingPrefab;
    private Camera arCamera;
    Vector3 lastCamPos;
    List<BuildingLabel> buildingLabels = new();

    public void SpawnBuildings(List<BuildingDTO> buildings)
    {
        if (!worldOrigin.isReady || worldOrigin.BuildingAnchor == null)
            return;
        if (arCamera == null)
            arCamera = Camera.main;

        // foreach (var dto in buildings)
        //     CreateBuilding(dto);
        StartCoroutine(BuildBuildingsGradually(buildings));
        StartCoroutine(UpdateLabelsPeriodically());
    }

    IEnumerator BuildBuildingsGradually(List<BuildingDTO> list)
    {
        int spawned = 0;

        foreach (var dto in list)
        {
            CreateBuilding(dto);
            spawned++;

            // ⭐ 핵심: 1~2개 생성 후 프레임 양보
            if (spawned % 2 == 0)
                yield return null;
        }
    }

    void CreateBuilding(BuildingDTO dto)
    {
        if (dto == null)
        {
            Debug.LogError("DTO is null");
            return;
        }

        if (buildingPrefab == null)
        {
            Debug.LogError("buildingPrefab is null");
            return;
        }

        if (worldOrigin == null || worldOrigin.BuildingAnchor == null)
        {
            Debug.LogError("WorldOrigin or BuildingAnchor is null");
            return;
        }

        if (dto.footprint == null || dto.footprint.Count < 3)
        {
            Debug.LogWarning($"Invalid footprint for {dto.id}");
            return;
        }

        // ===== Mesh 생성 =====
        List<Vector3> baseVerts = new();
        foreach (var p in dto.footprint)
            baseVerts.Add(worldOrigin.LatLonToWorld(p.lat, p.lon));

        Vector3 origin = baseVerts[0];
        List<Vector3> localVerts = new();

        foreach (var v in baseVerts)
            localVerts.Add(v - origin);

        // Mesh mesh = SimpleExtrude(baseVerts, dto.height);
        Mesh mesh = Extrude(localVerts, dto.height);

        // Vector3 spawnPos =
        //     arCamera.transform.position +
        //     arCamera.transform.forward * 2f;
        // Vector3 spawnPos = origin;

        // ===== Building 생성 =====
        GameObject building = Instantiate(
            buildingPrefab,
            Vector3.zero,
            Quaternion.identity,
            worldOrigin.BuildingAnchor
        );

        building.transform.localPosition = origin;

        int buildingLayer = LayerMask.NameToLayer("Building");
        building.layer = buildingLayer;
        foreach (Transform t in building.GetComponentsInChildren<Transform>(true))
            t.gameObject.layer = buildingLayer;

        building.name = $"Building_{dto.id}";

        // ===== 필수 컴포넌트 =====
        var sync = building.GetComponent<PixelSyncManager>();
        var state = building.GetComponent<BuildingState>();
        var canvas = building.GetComponentInChildren<PixelTextureCanvas>(true);
        var label = building.GetComponentInChildren<BuildingLabel>(true);

        if (label != null)
        {
            buildingLabels.Add(label);

            if (IsNear(building))
            {
                label.SetName(dto.name);
                label.gameObject.SetActive(true);
            }
            else
            {
                label.gameObject.SetActive(false);
            }
        }

        if (sync == null || state == null || canvas == null)
        {
            Debug.LogError(
                "Missing PixelSyncManager / BuildingState / PixelTextureCanvas"
            );
            Destroy(building);
            return;
        }

        // ===== ⭐ 1️⃣ buildingId 먼저 Initialize ⭐ =====
        state.buildingId = dto.id;
        state.buildingName = dto.name;

        sync.Initialize(
            dto.id,
            canvas,
            state,
            dto.name
        );

        // ===== Mesh / Material =====
        var mf = building.AddComponent<MeshFilter>();
        var mr = building.AddComponent<MeshRenderer>();

        mf.sharedMesh = mesh;
        mr.material = buildingMaterial;

        // 🔥 여기서만 fitting
        BuildingSpawner_FitHelper.FitByMesh(building, mf, mr);

        // (선택) 자동 선택
        // BuildingSelectionManager.Instance?.Select(sync);
    }


    bool IsNear(GameObject building, float maxDistance = 40f) // 40m 정도가 AR에서 이름 보이기 좋은 거리
    {
        if (Camera.main == null)
            return false;

        Vector3 camPos = Camera.main.transform.position;
        Vector3 bPos   = building.transform.position;

        camPos.y = 0;
        bPos.y   = 0;

        float sqrDist = (camPos - bPos).sqrMagnitude;

        return sqrDist <= maxDistance * maxDistance;
    }



    Mesh SimpleExtrude(List<Vector3> baseVerts, float height)
    {
        Mesh mesh = new Mesh();

        if (baseVerts == null || baseVerts.Count < 4)
            return mesh;

        // 0~3 : 바닥
        // 4~7 : 천장
        Vector3[] vertices = new Vector3[8];

        for (int i = 0; i < 4; i++)
        {
            vertices[i] = baseVerts[i];
            vertices[i + 4] = baseVerts[i] + Vector3.up * height;
        }

        int[] triangles =
        {
            // 옆면
            0,1,5, 0,5,4,
            1,2,6, 1,6,5,
            2,3,7, 2,7,6,
            3,0,4, 3,4,7,

            // 윗면
            4,5,6,
            4,6,7
        };

        mesh.vertices = vertices;
        mesh.triangles = triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();

        return mesh;
    }

    public static Mesh Extrude(List<Vector3> basePolygon, float height)
    {
        Mesh mesh = new Mesh();

        int count = basePolygon.Count;
        var vertices = new List<Vector3>();
        var triangles = new List<int>();

        // bottom
        for (int i = 0; i < count; i++)
            vertices.Add(basePolygon[i]);

        // top
        for (int i = 0; i < count; i++)
            vertices.Add(basePolygon[i] + Vector3.up * height);

        // sides
        for (int i = 0; i < count; i++)
        {
            int next = (i + 1) % count;

            int a = i;
            int b = next;
            int c = i + count;
            int d = next + count;

            triangles.Add(a); triangles.Add(c); triangles.Add(b);
            triangles.Add(b); triangles.Add(c); triangles.Add(d);
        }

        mesh.SetVertices(vertices);
        mesh.SetTriangles(triangles, 0);
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();

        return mesh;
    }

    IEnumerator UpdateLabelsPeriodically()
    {
        lastCamPos = Camera.main.transform.position;

        while (true)
        {
            if ((Camera.main.transform.position - lastCamPos).sqrMagnitude > 0.5f)
            {
                lastCamPos = Camera.main.transform.position;

                for (int i = 0; i < buildingLabels.Count; i++)
                {
                    var label = buildingLabels[i];
                    if (label == null) continue;

                    bool near = IsNear(label.transform.root.gameObject);
                    label.SetVisible(near);
                }
            }

            yield return new WaitForSeconds(0.3f);
        }
    }

}
