using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;

public class PixelSyncManager : MonoBehaviour
{
    [Header("Server")]
    public string serverUrl;

    [Header("Runtime Assigned")]
    public string buildingId;

    PixelTextureCanvas canvas;
    BuildingState buildingState;

    Coroutine syncRoutine;
    public Dictionary<PixelFace, PixelTextureCanvas> canvases;

    void Awake()
    {
        canvases = new Dictionary<PixelFace, PixelTextureCanvas>();

        foreach (var c in GetComponentsInChildren<PixelTextureCanvas>())
        {
            var surface = c.GetComponent<PixelSurface>();
            if (surface != null)
                canvases[surface.face] = c;
        }
    }

    // 🔹 BuildingSpawner에서 호출
    public void Initialize(
        string buildingId,
        PixelTextureCanvas canvas,
        BuildingState buildingState,
        string buildingName = null
    )
    {
        this.buildingId = buildingId;
        this.canvas = canvas;
        this.buildingState = buildingState;

        if (syncRoutine != null)
            StopCoroutine(syncRoutine);

        StartCoroutine(RegisterBuilding(buildingName));
        syncRoutine = StartCoroutine(SyncLoop());
    }

    IEnumerator RegisterBuilding(string buildingName)
    {
        if (string.IsNullOrEmpty(serverUrl)) yield break;

        var payload = $"{{\"name\":{(buildingName != null ? "\"" + buildingName + "\"" : "null")}}}";
        var req = new UnityWebRequest($"{serverUrl}/buildings/{buildingId}", "PUT");
        byte[] body = Encoding.UTF8.GetBytes(payload);
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        yield return req.SendWebRequest();
    }

    IEnumerator SyncLoop()
    {
        while (true)
        {
            yield return SyncPixels();
            yield return SyncBuildingState();
            yield return new WaitForSeconds(3f);
        }
    }

    IEnumerator SyncPixels()
    {
        var req = UnityWebRequest.Get(
            $"{serverUrl}/buildings/{buildingId}/pixels"
        );

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
            yield break;

        Pixel[] pixels =
            JsonHelper.FromJson<Pixel>(req.downloadHandler.text);

        foreach (var p in pixels)
        {
            if (!canvases.TryGetValue(p.face, out var canvas))
                continue;

            canvas.SetPixel(
                p.x,
                p.y,
                HexToColor(p.color)
            );
        }

        // ⭐ 면별로 Apply
        foreach (var c in canvases.Values)
            c.Apply();
    }


    // 🔴 픽셀 찍을 때 서버 전송
    public void SendPixel(PixelFace face, int x, int y, Color color)
    {
        if (string.IsNullOrEmpty(buildingId)) return;
        StartCoroutine(PostPixel(face, x, y, color));
    }


    IEnumerator PostPixel(PixelFace face, int x, int y, Color color)
    {
        var payload = new Pixel
        {
            buildingId = buildingId,
            face = face,   // ⭐ 중요
            x = x,
            y = y,
            color = ColorToHex(color)
        };

        string json = JsonUtility.ToJson(payload);

        var req = new UnityWebRequest($"{serverUrl}/pixels", "POST");
        byte[] body = Encoding.UTF8.GetBytes(json);

        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();
    }


    public IEnumerator SyncBuildingState()
    {
        var req = UnityWebRequest.Get(
            $"{serverUrl}/buildings/{buildingId}"
        );

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
            yield break;

        var state =
            JsonUtility.FromJson<BuildingResponse>(
                req.downloadHandler.text
            );

        buildingState.ApplyServerState(state); // ⭐ 여기!
    }


    string ColorToHex(Color c)
        => $"#{ColorUtility.ToHtmlStringRGB(c)}";

    Color HexToColor(string hex)
    {
        ColorUtility.TryParseHtmlString(hex, out Color c);
        return c;
    }

    public void PostRecommend()
    {
        if (string.IsNullOrEmpty(buildingId))
            return;

        StartCoroutine(PostRecommendCoroutine());
    }

    // 🔴 픽셀 지울 때 서버 전송
    public void DeletePixel(PixelFace face, int x, int y)
    {
        if (string.IsNullOrEmpty(buildingId)) return;
        StartCoroutine(DeletePixelCoroutine(face, x, y));
    }

    IEnumerator DeletePixelCoroutine(PixelFace face, int x, int y)
    {
        string url = $"{serverUrl}/pixels?buildingId={UnityWebRequest.EscapeURL(buildingId)}&face={(int)face}&x={x}&y={y}";
        var req = UnityWebRequest.Delete(url);
        yield return req.SendWebRequest();
    }

    public IEnumerator PostRecommendCoroutine()
    {
        var json = JsonUtility.ToJson(
            new RecommendRequest { buildingId = buildingId }
        );

        var req = new UnityWebRequest(
            $"{serverUrl}/buildings/recommend", "POST"
        );

        byte[] body = System.Text.Encoding.UTF8.GetBytes(json);
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();
    }
}
