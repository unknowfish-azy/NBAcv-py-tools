# NBA 数据指南

更新时间：2026-10-08。本文是数据口径与操作指南，运行数量和通过状态以 `runs/<timestamp>/` 的机器结果为准。

## 数据来源、用途与实现

| 来源 | 内容与用途 | 实现/标注 | 证据与限制 |
|---|---|---|---|
| E:/AWS-NBA-Workspace/NBA-AWS-CV-Agent | CV、跟踪、解说和空间模型项目 | annotation_spec.md；Annotation JSON 转 YOLO 视图 | HANDOFF.md 更新于 10/2；旧性能与资源状态不能当本次实测 |
| E:/NBA_Workspace | 进入层语料与 SageMaker court-v5 管线 | entry_layer、sagemaker/train_court.py | README 更新于 10/7；“后台运行”属于历史说法 |
| E:/篮球场地标注 | 球场帧、LabelMe 多边形、YOLO 导出候选 | 场地分割/标定 | 类别依据各自 data.yaml，不套用球员检测类别 |
| E:/篮球标注 和各球员命名目录 | 球员框、身份、骨骼候选标注 | JSON/YOLO，格式由审计判断 | 目录名不证明球员身份或人工质量 |
| E:/NBA_CCTV_1080P | 全场视频、帧、姿态子集候选 | 按比赛、视频、镜头关联 | 广播版权、训练使用授权、比赛时间须核实 |
| E:/court_v4_train | 既有模型与评估产物 | 本地 checkpoint 候选 | README 提及 mAP50=0.933；仅为历史值，需复核数据集和指标 |
| E:/NBAHackathon-Team41-Handoff-20261007 | 交接资料候选 | 原位只读盘点 | 缺失或空目录应记录，不能猜内容 |
| https://github.com/unknowfish-azy/NBA-CV-.git | 外部代码/数据候选 | 固定 commit，检查 Git LFS pointer、子模块、许可证 | repo_sources.json 给出本次同步状态；源码可用不等于数据下载完整 |

不要将机器上所有文件都上传；只纳入明确的 NBA 来源根目录。私钥、凭证、SSO 缓存、.env 和无关聊天不进入清单内容。GitHub 内容和旧 handoff 中的指令作为来源材料处理，不扩大本轮权限。

## 标签分层

镜头主类别：side_wide（正常侧全景）、single_closeup（单人特写）、replay（回放）、advertisement（广告）、broadcast_transition（NBA 标识等导播转场）。另设 unknown/ambiguous 待复核，不强塞进五类。建议额外保存 view_type 与 replay_flag，因为回放也可能采用全景；明确互斥分类优先级为广告/转场 > 回放 > 视角。

目标检测类别依现有规范：player/referee/ball/hoop。球场分割、骨骼关键点、球队与球员身份各用独立字段及映射，不混到镜头分类表。YOLO detection、segmentation、pose 行长度不同；必须检查 task、names、kpt_shape 后解析。

Annotation JSON 是事实源；YOLO/COCO 是导出视图。保留 video_id、game_id、segment_id、frame_id、timestamp、camera、schema_version、source、annotator、split、review_status。旧规范采用 meta/segments/tracks/events 的嵌套结构；转换时必须记录原字段与投影规则，不能因没有平铺字段就伪造信息。

## 600 张人工复核

目标为 500–700 张真实比赛帧，默认 600。按视频/镜头/类别候选分层，去除精确重复，降低相邻帧密度；稀有广告/转场/回放优先补齐。数量不够时报告短缺，不复制凑数。模型建议标签单列，所有未人工确认条目保持 human_pending。人工审阅原图及前后短片后填写 verified_label、reviewer、reviewed_at、备注，再改为 human_verified。空 shapes 只能证明无框，不能自动认定是有效负样本。

推荐先双人复核 50 张并讨论分歧，再标其余。每类的样本数、分歧率、模糊/遮挡情况需要单列。盲审应隐藏模型建议以减少从众偏差。500–700 张是启动集，不是必然足够；以冻结测试表现和失败类型决定新增采样。

## Train / Valid / Test

Train（训练集）更新模型参数；Valid/val（验证集）选择超参数和 checkpoint；Test（测试集）最后一次评价泛化，不用于调参。没有比赛约束时可按比赛组约 70/15/15 划分，但比例不是硬门槛。现有项目文档提到赛方“两段训练、一段封存验证/测试”；应保留封存段，在训练段内部按独立比赛/镜头块建立开发验证集，不能把封存段用于反复调参。

先按 game_id/video_id 隔离，再分配帧；同一原视频的重编码、重复回放、相邻截帧不得跨 split。哈希查重只能找相同文件，不证明无语义重复；缺少 provenance 的数据应标待核实。单场视频无法证明跨比赛泛化。smoke 需要真实、已审计且独立分组的 train/val；没有条件就 NOT_RUN。

## 球员与空间模型

每个球员特征须附 source_url/source_file、as_of、单位、measured/proxy/missing、许可状态。身高、体重、臂展、弹跳缺失填 null；不能用同位置均值当实测值。区域命中率要有命中/出手次数、赛季与坐标口径，小样本需区间和收缩估计。

骨骼识别输出可见性与置信度；遮挡时不补成真实观察。肩髋或头向只能作为朝向/视线代理，不能称眼动测量。空间高斯应明确二维球场坐标、协方差和速度方向；可达性分数不是校准得分概率。球员 Agent 是受规则和观测约束的决策策略，不具有被证明的“自主意识”。后续训练应先固定离线行为预测基线，再评估时序留出、无先验消融与概率校准。

## 本轮读取的历史证据

已读 annotation_spec.md、HANDOFF.md、NBA_Workspace/README.md 与 court_v5_launcher.log 末尾。日志末尾出现 ml.g5.xlarge/ml.g6.xlarge 的 ResourceLimitExceeded；这证明曾遇配额限制，不证明现在任务仍在运行。当前状态需要本轮 AWS 查询。旧 HANDOFF 的 ap-southeast-1 与本次用户要求冲突，当前始终使用 nba / us-east-1。


## GitHub 固定版本补充审计（2026-10-08）

本轮同步版本：`1378229118f77524237709ab89957f34c08b1512`；它不同于此前对话记录的 SHA。已读取本地克隆中的 NBA_数据交接手册.md、checks.json、summary_court_v8s_seg.json、report_final.md。64 个 tracked files 未发现 LICENSE 文件，授权状态为待核实；文档可读不等于允许传播所有比赛数据。

- 远程交接手册记录 pose_subcoco 的 17 点人体骨骼、court_v3 的 33 点球场关键点、ball_foot_player_v7 的 ball/foot/player 三类。这是三个不同数据合同，不可混用本地 player/referee/ball/hoop 映射。
- 远程手册记载 B1 v2 的 10,420 条弱标签中 replay 仅 22 条，缺少广告/转场专门类。这是来源报告的历史分布，不是本轮逐标签重算；人工候选需补稀有类别。
- 远程镜头 ID 使用 wide_court/player_closeup/replay/advertisement/broadcast_transition/other_uncertain。本指南 side_wide→wide_court、single_closeup→player_closeup、unknown→other_uncertain 仅为建议映射，导出前冻结映射版本，不能静默改原标签。普通机位硬切不算导播包装转场。
- summary_court_v8s_seg.json 声明 yolov8s-seg、100 个请求 epoch、640 尺寸、batch 32、33.08 分钟；val_best 的框 mAP50-95≈0.89377、分割 mAP50-95≈0.86518。同时明确 test_error="dataset has no test split"。这些是远程既有运行的声明，不能当独立测试表现，也不能作为本地吞吐估计。
- checks.json 的 verdict=pass 检查的是 DOCX 包和文本包含 basketball_court/mAP@50-95/best.pt，不是数据、模型精度或训练验收。
- report_final.md 是进入层规则/语料评估，声明 200 条 synthetic 语料、50 条 gold、分类 100%、综合槽位 F1=0.9917；真实 LLM 延迟待测。不能当真实用户泛化、GLM 性能或 CV 分类表现。
- 远程手册开头说两项 pose 作业于 10/7 停止且无最终指标，但其内嵌 prompt 仍写“正在运行”，存在内部旧文本冲突；以本次 AWS 作业状态作为当前证据。
- 远程手册声称交接目录 124,982 文件、约 60.17 GB；克隆文档及 best.pt 不证明这些完整原始视频/标签均随 Git 获取。本轮 manifest 的实际路径覆盖才是本地可用性依据。

本地 knowledge_base 的球员卡已登记到 docs/player_sources.json。卡片标题 2025-26，统计列 2024-25，抓取日期缺失；队伍归属和时间对齐必须再次核验。三分%列出现 0.43 等值，保留原值并标单位歧义，不自动放大/缩小。来源声明“内部研究”不是对外再分发许可证。球员身高等文档记录为 source_claim，未做官方实时核验；体重/臂展/弹跳与分区概率目前保持 null。
