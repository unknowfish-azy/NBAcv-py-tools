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
