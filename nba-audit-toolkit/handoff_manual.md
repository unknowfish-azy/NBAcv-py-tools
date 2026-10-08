# NBA 数据与训练交接 — 实测验收

目录：E:\NBA-Audit-Toolkit\runs\20261008-103426

扫描文件 515,125；标注文件 149,770；几何违规计数 5,018；空标注文件 47,300。

人工复核候选 600 张，原始标注关联图片、SHA256 去重；全部 human_pending。

|验收项|结果|
|---|---|
|审计工具运行|完成，含发现项|
|本地工程训练/保存/重载/验证|PASS，32/16 图、1 epoch、23.89 秒|
|数据划分|FAIL，已发现比赛跨 train/val/test|
|模型独立精度|NOT_RUN|
|AWS资源|NOT_RUN，SSO接口超时|
|GLM执行|MODEL_UNAVAILABLE，仅交付 prompts|

## 目录盘点
|目录|文件数|GB|
|---|---:|---:|
|E:\篮球场地标注|27,682|4.11|
|E:\篮球标注|13,875|3.60|
|E:\杜兰特人物标注|37,845|9.34|
|E:\阿门汤普森|52,340|9.81|
|E:\塔里伊森球员标记|13,839|3.38|
|E:\小贾巴里史密斯|24,828|4.87|
|E:\阿尔佩伦申京标注|108,039|5.12|
|E:\NBA_Workspace|28|0.00|
|E:\NBAHackathon-Team41-Handoff-20261007|124,984|60.18|
|E:\court_v4_train|34|0.06|
|E:\NBA_CCTV_1080P|80,719|147.74|
|E:\AWS-NBA-Workspace\NBA-AWS-CV-Agent|30,918|0.62|

## 关键问题与交接动作
1. court-v3 33点姿态格式与 court-v4 分割权重不兼容，分别管理配置。
2. court-v3 查到14个比赛组 train/valid 重叠、15个开发/test 重叠，612张图比赛来源未确认；需按比赛重建划分。
3. court-v4 按同场帧随机划分，短训练仅证明工程能运行，分数不证明泛化。
4. 600张候选需要人工填写镜头类别/复核人/来源；重复相邻帧与回放必须按视频分组。
5. 球员身高等资料在 player_sources.json 有来源记录；臂展、弹跳和区域命中概率等缺失字段保留 null。
6. GitHub已下载并固定commit，64文件逐个哈希；未找到许可证，不能由此推定数据与权重再分发权。
7. 本次未创建云端训练、上传或定时删除任务。

## 文件入口
- dataset_manifest.json：元数据、部分哈希及扫描错误。
- annotation_audit.json：格式和几何初检；非检测YOLO行标为未核验，不能当有效标签。
- human_review.csv：人工复核队列。
- split_audit.json：失败证据。
- repo_sources.json：指定GitHub提交与全部64文件哈希。
- smoke_status.json：实际GPU、依赖、工程训练证据与限制。
- ../../docs/data_guide.md、../../docs/agent_runbook.md：数据规则、每步prompt与验收。
- ../../smoke/diagnostic/result.json：不可覆盖的原始工程实测。

此报告未完成全量视觉人工验收、全媒体内容哈希、网络带宽测量或云GPU探测；不能据此推算长训epoch数。