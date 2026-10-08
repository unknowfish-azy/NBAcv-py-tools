# Scene gate contract

The 521 labels were validated as 521 records: `game_wide=378`, `closeup=92`, `ad_graphic=19`, `other=17`, `replay=13`, `transition=2`; splits are `train=361`, `val=79`, `test=81`. They are annotated by `zcode_visual_review`, so they are seed labels and audit metadata, not independent human ground truth.

The C# job request carries `sceneLabels` and `allowedScenes`. The Python worker must read the same JSONL and emit a per-frame gate decision before detector/pose work:

```json
{"frame": 123, "scene": "game_wide", "gate": "allow", "reason": "allowed_scene"}
{"frame": 124, "scene": "ad_graphic", "gate": "skip", "reason": "scene_not_allowed"}
```

`transition` and `replay` require additional labels before they are used as a trained classifier target: two transition samples cannot support a reliable test score. A C# orchestrator may schedule the worker and expose its stream, but it must not silently convert skipped frames into negative training examples.

The OpenAI proxy is only a transport adapter. It must not send raw frames or credentials to an upstream model unless the job explicitly requests that operation.
