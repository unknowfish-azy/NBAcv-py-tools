# NBA CV Audit Toolkit

NBA 比赛视频分析与数据审计工具链，采用 C# 编排引擎 + Python 视觉 worker。C# 负责任务、批处理、场景门控和 OpenAI 兼容接口；Python 负责 LabelMe/pose17 规范化、骨骼时序门禁、人物身份证据、FFmpeg 解码和 OCR。

工具坚持 unknown 优先和证据可追溯，不会把未知身份强行猜成球员，也不会把视觉模型自证当成人工确证。

## 能力与目录

- LabelMe、pose17、tracks JSON/JSONL 规范化和 COCO17 校验。
- 按时间戳/FPS 的速度门禁、断档感知、逐关节 REVIEW 明细。
- LabelMe 目录跨文件时序分析，支持 track-map、group_id、--group-id-is-track。
- 身份门禁：号码、球队、多帧累积、外观候选、真人证据、AI 辅助人工抽检、过期和撤销。
- 视频或帧目录输入，自动探测 FFmpeg/FFprobe。
- 统一输出 review_queue.jsonl 和运行 manifest。
- C# .NET 8 服务：任务状态、场景门控、/v1/chat/completions、/v1/responses。

目录：cv_tools 是 Python worker；tools 是只读审计和 AWS 预检；smoke 是本地环境检查；schemas 是数据 schema；tests 是测试；docs 是交接文档；prompts 是 Agent 编排；sources/NBA-CV- 是 GitHub 数据副本。

C# 引擎源码包在 outputs/nba-cv-engine，它启动 Python worker，不重复实现 YOLO、姿态估计或 OCR。

## 安装

    cd E:\NBA-Audit-Toolkit\cv_tools
    python -m pip install .
    python -m pip install ".[video,ocr]"

模型权重和 FFmpeg 需另行提供。C# 引擎需要 .NET 8 SDK，使用 dotnet build nba-cv-engine.csproj --configuration Release。

## Python CLI

骨骼规范化与门禁：

    python E:\NBA-Audit-Toolkit\cv_tools\run_cv_tools.py skeleton <input> <output> --format auto --fps 2.5 --max-speed 900 --max-gap 2

目录模式必须提供稳定轨迹：

    python run_cv_tools.py skeleton <labelme-dir> <output.json> --track-map <track-map.json>

没有稳定 track_id、group_id 或映射时输出 NOT_RUN，不会用文件序号伪造轨迹。--suggest-speed 只报告建议，不修改门槛。

身份解析：

    python E:\NBA-Audit-Toolkit\cv_tools\run_cv_tools.py identity tracks.jsonl roster.json identity.json

轨迹观察应包含 timestamp、track_id、team_score、jersey_score。输出保留平铺字段、resolution 和原始 input。

视频管线：

    python E:\NBA-Audit-Toolkit\cv_tools\video_identity_pipeline.py --video game.mp4 --model players.pt --out runs/game01 --seconds 10 --fps 5 --ocr

也支持 --frames-dir；默认每秒采样 5 帧，不代表逐原视频帧分析。

## 身份证据

- human_confirmed：具名真人、evidence_id、作用域和有效期齐全。
- ai_confirmed_spot_checked：AI 只提供候选，必须有真人抽检记录和证据 ID。
- provisional：号码/球队等机器证据达到阈值，仍可进入复核。
- unknown：证据不足、冲突、镜头切换、轨迹断裂或确证过期。

球衣颜色、鞋色和体型比例只是候选特征；鞋色是 bbox proxy，不能单独命名球员。人工证据支持 shot/video/track 作用域、过期和撤销。

## 输出与数据

视频运行目录通常包含 evidence.jsonl、trajectories.json、presence.jsonl、review_queue.jsonl、run_manifest.json。骨骼 schema 为 nba.pose17.v2，身份 schema 为 nba.identity.v1；evidence_score 不是校准概率。

当前场景种子集共 521 帧（视觉模型逐帧复核，不能当作独立真人 ground truth）：game_wide 378、closeup 92、ad_graphic 19、other 17、replay 13、transition 2；切分 train 361、val 79、test 81。

数据和复现命令见 docs/handoff_manual.md、docs/data_guide.md 及 sources/NBA-CV- 下的交接文档。

## C# 编排引擎

    $env:OPENAI_BASE_URL = "https://api.openai.com/v1"
    $env:OPENAI_API_KEY = "<set outside source control>"
    dotnet run --project nba-cv-engine.csproj --urls http://127.0.0.1:5080
    Invoke-RestMethod http://127.0.0.1:5080/health

引擎当前使用内存任务表，适合本地验收；多机生产环境应替换为 SQLite/队列。OpenAI 代理只转发请求和流式响应，不会自动上传原始视频或帧。

## 审计、测试与验证

    cd E:\NBA-Audit-Toolkit
    python tools/run_audit.py --config config.json
    python tools/aws_preflight.py
    cd E:\NBA-Audit-Toolkit\cv_tools
    python -m unittest discover -s tests -v
    python run_cv_tools.py --version

真实规模验证：10,420 个 LabelMe 文件规范化，0 invalid；稳定轨迹门禁 PASS 3,650、REVIEW 44、NOT_RUN 74。这是工程门禁统计，不是球员识别准确率。

## 已知限制

- 没有人工 ground truth 时不报告识别准确率。
- 无稳定轨迹 ID 时，时序状态为 NOT_RUN。
- 可见性列缺失会使关键点无法进入时序门禁。
- 颜色、鞋色、体型和单帧 OCR 易受灯光、遮挡和切镜影响。
- C# 引擎尚无持久化队列、GPU 调度和训练集版本锁定。
- AWS 长期训练、上传和删除不属于默认流程，云端写操作需单独审查。

## 文档入口

根 README 是唯一功能说明入口。详细文档包括 cv_tools/README.md、cv_tools/AI_SPOT_CHECK.md、cv_tools/skills/nba-player-evidence/SKILL.md、outputs/nba-cv-engine/SCENE_GATE_CONTRACT.md、docs/agent_runbook.md、prompts/ 和 docs/implementation_status.md。

不要将 .pem、API key、token、模型权重、视频、__pycache__、bin、obj 或运行产物提交到 GitHub。
