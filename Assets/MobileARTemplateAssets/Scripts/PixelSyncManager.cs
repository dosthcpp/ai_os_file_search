using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System.Linq;

[Serializable]
public class PixelBatch
{
    public List<Pixel> pixels;
}

public class PixelSyncManager : MonoBehaviour
{
    [Header("Server")]
    public string serverUrl;
    public float syncInterval = 3f;
    public int maxRetryAttempts = 3;

    [Header("Runtime Assigned")]
    public string buildingId;

    PixelTextureCanvas canvas;
    BuildingState buildingState;

    Coroutine syncRoutine;
    public Dictionary<PixelFace, PixelTextureCanvas> canvases;

    private double lastSyncTimestamp = 0;
    private List<Pixel> pendingPixels = new List<Pixel>();
    private bool isUploadingBatch = false;

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
        this.lastSyncTimestamp = 0; // Reset timestamp for new building

        if (syncRoutine != null)
            StopCoroutine(syncRoutine);

        StartCoroutine(RegisterBuilding(buildingName));
        syncRoutine = StartCoroutine(SyncLoop());
    }

    IEnumerator RegisterBuilding(string buildingName)
    {
        if (string.IsNullOrEmpty(serverUrl)) yield break;

        var payload = $"{{\"name\":{(buildingName != null ? "\"" + buildingName + "\"" : "null")}}}";
        
        yield return SendRequestWithRetry(() => {
            var req = new UnityWebRequest($"{serverUrl}/buildings/{buildingId}", "PUT");
            byte[] body = Encoding.UTF8.GetBytes(payload);
            req.uploadHandler = new UploadHandlerRaw(body);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            return req;
        });
    }

    IEnumerator SyncLoop()
    {
        while (true)
        {
            yield return SyncPixels();
            yield return SyncBuildingState();
            yield return ProcessPendingPixels();
            yield return new WaitForSeconds(syncInterval);
        }
    }

    IEnumerator SyncPixels()
    {
        string url = $"{serverUrl}/buildings/{buildingId}/pixels";
        if (lastSyncTimestamp > 0)
        {
            url += $"?updated_after={lastSyncTimestamp}";
        }

        UnityWebRequest req = UnityWebRequest.Get(url);
        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogWarning($"[PixelSync] Failed to sync pixels: {req.error}");
            yield break;
        }

        Pixel[] pixels = JsonHelper.FromJson<Pixel>(req.downloadHandler.text);

        if (pixels != null && pixels.Length > 0)
        {
            foreach (var p in pixels)
            {
                if (!canvases.TryGetValue(p.face, out var targetCanvas))
                    continue;

                targetCanvas.SetPixel(
                    p.x,
                    p.y,
                    HexToColor(p.color)
                );
            }

            // ⭐ 면별로 Apply
            foreach (var c in canvases.Values)
                c.Apply();
            
            // Update timestamp to now (server time would be better, but local is okay for delta)
            lastSyncTimestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        }
    }

    // 🔴 픽셀 찍을 때 서버 전송 (이제 큐에 추가)
    public void SendPixel(PixelFace face, int x, int y, Color color)
    {
        if (string.IsNullOrEmpty(buildingId)) return;
        
        pendingPixels.Add(new Pixel
        {
            buildingId = buildingId,
            face = face,
            x = x,
            y = y,
            color = ColorToHex(color)
        });
    }

    IEnumerator ProcessPendingPixels()
    {
        if (isUploadingBatch || pendingPixels.Count == 0) yield break;

        isUploadingBatch = true;
        List<Pixel> batchToUpload = new List<Pixel>(pendingPixels);
        pendingPixels.Clear();

        var batch = new PixelBatch { pixels = batchToUpload };
        string json = JsonUtility.ToJson(batch);

        yield return SendRequestWithRetry(() => {
            var req = new UnityWebRequest($"{serverUrl}/pixels/batch", "POST");
            byte[] body = Encoding.UTF8.GetBytes(json);
            req.uploadHandler = new UploadHandlerRaw(body);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            return req;
        });

        isUploadingBatch = false;
    }

    public IEnumerator SyncBuildingState()
    {
        UnityWebRequest req = UnityWebRequest.Get($"{serverUrl}/buildings/{buildingId}");
        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
            yield break;

        var state = JsonUtility.FromJson<BuildingResponse>(req.downloadHandler.text);
        buildingState.ApplyServerState(state);
    }

    // Helper for retries and error handling
    IEnumerator SendRequestWithRetry(Func<UnityWebRequest> requestFactory)
    {
        int attempts = 0;
        bool success = false;

        while (attempts < maxRetryAttempts && !success)
        {
            attempts++;
            using (var req = requestFactory())
            {
                yield return req.SendWebRequest();

                if (req.result == UnityWebRequest.Result.Success)
                {
                    success = true;
                }
                else
                {
                    bool isNetworkError = req.result == UnityWebRequest.Result.ConnectionError;
                    Debug.LogWarning($"[PixelSync] Request failed (Attempt {attempts}/{maxRetryAttempts}): {req.error}");
                    
                    if (attempts < maxRetryAttempts)
                    {
                        // Exponential backoff
                        yield return new WaitForSeconds(Mathf.Pow(2, attempts));
                    }
                }
            }
        }
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
        
        yield return SendRequestWithRetry(() => {
            return UnityWebRequest.Delete(url);
        });
    }

    public IEnumerator PostRecommendCoroutine()
    {
        var json = JsonUtility.ToJson(
            new RecommendRequest { buildingId = buildingId }
        );

        yield return SendRequestWithRetry(() => {
            var req = new UnityWebRequest($"{serverUrl}/buildings/recommend", "POST");
            byte[] body = System.Text.Encoding.UTF8.GetBytes(json);
            req.uploadHandler = new UploadHandlerRaw(body);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            return req;
        });
    }
}
