# NBA CV Engine 0.1.0

C# orchestration layer for the existing Python CV tools. It provides:

- resumable job state (`queued`, `running`, `succeeded`, `failed`);
- a scene-gated job contract through `AllowedScenes` and `SceneLabels`;
- an OpenAI-compatible `/v1/chat/completions` and `/v1/responses` proxy;
- configurable upstream URL through `OPENAI_BASE_URL` and secret-only `OPENAI_API_KEY`.

The engine does not reimplement YOLO, pose estimation, OCR, or training. It launches the versioned Python worker and records its exit state. A production version should persist `JobState` to SQLite or a queue before multi-machine execution; the in-memory store here is a working local reference implementation.

## Build and run

Requires the .NET 8 SDK:

```powershell
dotnet build nba-cv-engine.csproj
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_API_KEY = "<set outside source control>"
dotnet run --project nba-cv-engine.csproj --urls http://127.0.0.1:5080
```

Start a Python job:

```powershell
Invoke-RestMethod http://127.0.0.1:5080/v1/jobs -Method Post -ContentType application/json -Body (@{
  input = "E:\阿门汤普森\pose17_labelme"
  output = "E:\runs\v032"
  python = "python"
  arguments = "E:\NBA-Audit-Toolkit\cv_tools\run_cv_tools.py skeleton ..."
  sceneLabels = "E:\阿门汤普森\scene_labels.jsonl"
  allowedScenes = @("game_wide")
} | ConvertTo-Json)
```

The OpenAI proxy forwards request bodies and streaming response bytes without logging prompts, keys, or images. It is compatible with clients that accept an OpenAI `base_url` pointing at this service.

This workspace currently has only the .NET runtime, not the SDK, so compilation must be run on a machine with the SDK installed.
