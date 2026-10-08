---
name: nba-player-evidence
description: Use when extracting NBA player tracks, jersey OCR, appearance cues and conservative presence evidence from local match video for ZCode annotation review.
---
# 使用说明：NBA 人物证据 skill

当任务涉及 NBA 视频人物识别、球衣号码 OCR、球衣/球鞋颜色、体型比例、轨迹和在场状态时使用本 skill。

1. 先用 FFmpeg/ffprobe 读取视频元数据，按固定 `frame_step` 解码；保存视频 SHA、时间戳和解码参数。
2. 用现有 YOLO 人物权重生成检测框，用 ByteTrack 或已有 track_id 关联；每帧输出 bbox、检测置信度和镜头段。
3. 从人物框的上身和鞋部 ROI 提取 HSV/LAB 颜色直方图；颜色是候选证据，不是身份结论。球鞋颜色只在鞋部像素足够且无遮挡时记录。
4. 号码 OCR 只保留文本、OCR 置信度、ROI、时间戳和引擎；多帧同号且球队一致才进入身份候选。
5. 用 bbox 高宽比、人体关键点高度比例和可见点数记录体型特征；不要从像素比例直接声称真实身高。
6. 用 IdentityResolver 聚合证据。号码+球队、跨多个独立时间戳的重复证据才可提升身份分数；外貌/颜色/鞋色只能产生候选；冲突输出 `unknown`。
7. presence 状态分为 `visible`、`off_screen_or_occluded`、`confirmed_substituted_out`、`unknown`。连续未检测不能证明已下场；只有明确换人事件才可确认。
8. 给 ZCode 的 JSON 必须带 `source`, `video_sha256`, `frame`, `timestamp_s`, `track_id`, `evidence`, `confidence`, `status`；所有未校准分数命名为 `evidence_score`，不得写成概率。
9. 每次运行生成低置信/冲突队列和可视化复核图；原始视频、帧、标注和模型不覆盖。

禁止：凭外貌臆测姓名、把球衣颜色当唯一身份、从未检测到某人推断他被换下、把模型分数写作校准概率、跳过视频/模型/roster provenance。

推荐命令：
`python E:\NBA-Audit-Toolkit\cv_tools\video_identity_pipeline.py --video <mp4> --model E:\NBA_Dataset_20261008\models\players_v25i_v1\best.pt --out <run-dir>`

把 `evidence.jsonl`、`review_queue.jsonl`、`presence.jsonl` 和 `run_manifest.json` 交给 ZCode；使用 `unknown` 和 `human_pending` 作为不可绕过的状态。
