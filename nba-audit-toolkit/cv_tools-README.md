# NBA CV 骨骼与人物识别辅助工具

工具只写输出文件，不覆盖原始帧、LabelMe、YOLO、pose17 或 roster 文件。

## 骨骼规范化

```powershell
python E:\NBA-Audit-Toolkit\cv_tools\run_cv_tools.py skeleton `
  E:\AWS-NBA-Workspace\NBA-AWS-CV-Agent\tools\pred_pose17\pose17.json `
  E:\NBA-Audit-Toolkit\cv_tools\outputs\pose17_normalized.json
```

LabelMe points 输入可以指定 `--expected-points 17`。33 点球场关键点必须使用单独的任务配置，不能当作人体 17 点姿态。缺失点、越界点和跨帧跳点进入复核状态。`checked=true` 只有同时有 `reviewer` 字段才会成为人工确认。

## 人物识别

轨迹 JSON 每行至少包含 `track_id`、`frame`、可选 `jersey_number` 和 `team`；roster JSON 是球员对象数组，字段包括 `player_id`、`name`、`team`、`jersey_number`。

```powershell
python E:\NBA-Audit-Toolkit\cv_tools\run_cv_tools.py identity `
  E:\NBA-Audit-Toolkit\cv_tools\inputs\tracks.json `
  E:\NBA-Audit-Toolkit\docs\player_sources.json `
  E:\NBA-Audit-Toolkit\cv_tools\outputs\identity.json
```

工具仅把唯一的号码+球队匹配作为强证据；冲突、缺失或跨镜头证据不足都输出 `unknown`，并进入 `unknown_queue`。现有 `player_sources.json` 是来源声明，不是可直接作为完整 roster 的机器输入，需先整理为字段纯净的 roster 文件。

## 证据边界

它不会自动调用 ZCode、DeepSeek Harness、GLM 或远程 GitHub；对话和仓库内容只能作为规则与来源证据。画面识别建议仍由 ZCode/CVAT/GLM-5.3-flash 生成候选，再由这个工具执行 schema、轨迹跳变和身份证据门禁。
# 视频人物识别管线追加说明

文件：`video_identity_pipeline.py`

## 输出

- `evidence.jsonl`：每个检测的 frame、timestamp、track、bbox、检测分数、球衣颜色、鞋色、HSV 外观直方图、体型高宽比、可选 17 点关键点、号码 OCR 候选和身份证据。
- `trajectories.json`：按镜头和 track_id 的像素脚点轨迹、体型比例。
- `presence.jsonl`：`on_screen`、`off_screen`、`unknown` 和有来源才允许的 `confirmed_substituted_out`。
- `review_queue.jsonl`：低置信、冲突和未确认项。
- `review_*.jpg`：前几帧复核叠加图。
- `run_manifest.json`：视频/模型版本、FFmpeg 参数、帧数、检测数和限制。

## 建议分阶段运行

```powershell
python E:\NBA-Audit-Toolkit\cv_tools\video_identity_pipeline.py `
  --video E:\NBA_CCTV_1080P\2026-02-01_独行侠vs火箭_CCTV_1080P\2026-02-01_独行侠vs火箭_CCTV_1080P.mp4 `
  --model E:\NBA_Dataset_20261008\models\players_v25i_v1\best.pt `
  --out E:\NBA-Audit-Toolkit\cv_tools\runs\game01 `
  --start 3300 --seconds 60 --fps 5 --width 960 --ocr
```

OCR 需要本机已有 EasyOCR 权重。球衣颜色、球鞋颜色和高宽比是未校准候选特征，不能单独命名球员；应通过 `identity_evidence.py` 的多帧、球队和号码证据再进入候选。完整视频运行前先用 2–10 秒片段检查解码和模型。

## 已验证样例

- `runs/smoke-ocr`：真实比赛片段 6 帧、43 次人物检测、FFmpeg 正常退出；OCR 开启但该片段没有达到号码候选阈值。
- `runs/smoke-video`：4 帧、24 次人物检测。
- `identity_evidence.py`：14 项身份边界测试通过；总 CV 工具测试 24 项通过。
- 17 点姿态权重测试片段未产生检测框，已记录为工程结果，不把零检测当作准确率结论。
