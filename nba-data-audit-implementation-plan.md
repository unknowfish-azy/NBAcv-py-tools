# NBA CV 数据审计与 Agent 编排 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 E 盘建立可复现的 NBA 数据审计、交接手册、Agent prompts 和本地 smoke test 工具，并把 `unknowfish-azy/NBA-CV-` 作为可追踪的外部来源纳入审计。

**Architecture:** PowerShell 负责 Windows 路径、AWS CLI 只读预检和流程编排；Python 负责清单、标注解析、分割泄漏检查、抽样和报告。所有结果写入一个 run 目录，原始数据只读。云端创建、上传、训练和删除命令只生成计划，不由第一阶段自动执行。

**Tech Stack:** Python 3.11+、PowerShell 7、标准库 `pathlib/json/csv/hashlib/zipfile/subprocess`；可选使用已安装的 `ffprobe`、Ultralytics 和 PyTorch；AWS CLI v2；Git。

**Spec:** `E:/NBA-Audit-Toolkit/2026-10-08-nba-data-audit-orchestration-design.md`

## Global Constraints

- AWS 命令必须使用 `--profile nba --region us-east-1`。
- 外部 GitHub 来源必须记录 commit SHA 和许可证状态；同步失败必须输出 `UNSYNCED`。
- 不读取、打印、复制或上传 `.pem`、凭证、SSO 缓存文件。
- Annotation JSON 是事实源，YOLO/COCO 是投影视图。
- 训练/Valid/测试按视频或比赛段隔离，禁止跨 split 泄漏。
- 第一阶段不创建 AWS 资源、不上传数据、不启动长训练、不安排删除。
- 人工标注状态必须区分 `human_pending`、`human_verified` 和模型建议。

## Review Focus

- E 盘路径包含中文、空格、ZIP 和超大视频；测试路径枚举、哈希和输出编码。
- GitHub 网络中断；测试 commit 查询失败时仍生成带错误的 manifest。
- JSON、YOLO、COCO 混合标注；测试空标签、越界框、未知类别和坏 JSON。
- 同一视频帧出现在不同 split；测试按视频 ID 和文件名两级泄漏检测。
- 私钥与凭证混入递归扫描；测试拒绝纳入清单内容和复制清单。

### Task 1: 工具目录、配置和安全过滤

**Files:**
- Create: `E:/NBA-Audit-Toolkit/README.md`
- Create: `E:/NBA-Audit-Toolkit/config.json`
- Create: `E:/NBA-Audit-Toolkit/tools/safety.py`
- Test: `E:/NBA-Audit-Toolkit/tests/test_safety.py`

**Interfaces:**
- `load_config(path: Path) -> dict`
- `is_sensitive(path: Path) -> bool`
- `safe_relative(path: Path, roots: list[Path]) -> str`

- [ ] **Step 1: Write failing tests**

```python
def test_private_key_is_sensitive(tmp_path):
    assert is_sensitive(tmp_path / "id_rsa.pem") is True

def test_normal_json_is_allowed(tmp_path):
    assert is_sensitive(tmp_path / "labels.json") is False
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_safety.py -q`
Expected: FAIL because safety functions do not exist.

- [ ] **Step 3: Implement safety and config**

Use a denylist for `.pem`, `.key`, `.p12`, credential/cache path fragments, and AWS token directories. `config.json` stores read-only roots, Git URL, output root, sample seed, and sample count 600.

- [ ] **Step 4: Run tests**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_safety.py -q`
Expected: PASS.

### Task 2: Local source manifest

**Files:**
- Create: `E:/NBA-Audit-Toolkit/tools/scan_sources.py`
- Create: `E:/NBA-Audit-Toolkit/schemas/source_manifest.schema.json`
- Test: `E:/NBA-Audit-Toolkit/tests/test_scan_sources.py`

**Interfaces:**
- `scan_root(root: Path, output_root: Path) -> dict`
- `write_manifest(manifest: dict, path: Path) -> None`

- [ ] **Step 1: Write failing tests**

```python
def test_scan_excludes_sensitive_files(tmp_path):
    (tmp_path / "labels.json").write_text("{}", encoding="utf-8")
    (tmp_path / "secret.pem").write_text("PRIVATE", encoding="utf-8")
    result = scan_root(tmp_path, tmp_path / "out")
    paths = [item["relative_path"] for item in result["files"]]
    assert "labels.json" in paths
    assert "secret.pem" not in paths
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_scan_sources.py -q`
Expected: FAIL because scanner is absent.

- [ ] **Step 3: Implement scanner**

Record relative path, size, extension, modified time, SHA-256 for files under configured roots. Do not hash sensitive files. Include per-root totals and error list.

- [ ] **Step 4: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_scan_sources.py -q`
Expected: PASS.

### Task 3: GitHub source audit

**Files:**
- Create: `E:/NBA-Audit-Toolkit/tools/audit_github.py`
- Create: `E:/NBA-Audit-Toolkit/sources/README.md`
- Test: `E:/NBA-Audit-Toolkit/tests/test_audit_github.py`

**Interfaces:**
- `audit_remote(url: str, destination: Path) -> dict`
- `classify_sync_result(returncode: int, stdout: str, stderr: str) -> str`

- [ ] **Step 1: Write failing tests**

```python
def test_failed_git_sync_is_unsynced():
    assert classify_sync_result(128, "", "network failure") == "UNSYNCED"

def test_successful_git_sync_is_synced():
    assert classify_sync_result(0, "1888ac9\n", "") == "SYNCED"
```

- [ ] **Step 2: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_audit_github.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement read-only audit**

Run `git ls-remote`, optionally perform a shallow filtered clone only when explicitly enabled in config. Record URL, observed SHA, license filenames, file extensions, byte totals, command exit status, and stderr. Never treat a stale directory as current without matching SHA.

- [ ] **Step 4: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_audit_github.py -q`
Expected: PASS.

### Task 4: Annotation parser and quality audit

**Files:**
- Create: `E:/NBA-Audit-Toolkit/tools/audit_annotations.py`
- Create: `E:/NBA-Audit-Toolkit/schemas/annotation_audit.schema.json`
- Test: `E:/NBA-Audit-Toolkit/tests/test_audit_annotations.py`

**Interfaces:**
- `audit_json(path: Path) -> dict`
- `audit_yolo_label(path: Path, image_size: tuple[int, int] | None) -> dict`
- `audit_annotation_roots(roots: list[Path]) -> dict`

- [ ] **Step 1: Write failing tests**

```python
def test_yolo_box_out_of_range_is_invalid(tmp_path):
    label = tmp_path / "a.txt"
    label.write_text("0 1.2 .5 .2 .2\n", encoding="utf-8")
    result = audit_yolo_label(label, (1280, 720))
    assert result["invalid_rows"] == 1
```

- [ ] **Step 2: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_audit_annotations.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement parsers**

Support unified JSON, LabelMe/X-AnyLabeling (`shapes`, `imagePath`, `imageWidth`, `imageHeight`), YOLO TXT and basic COCO JSON. Count valid/invalid files, empty labels, unknown classes, coordinate violations, duplicate frame IDs and missing required fields. Preserve source path and do not rewrite originals. Detect YOLO detection versus segmentation versus pose from dataset configuration, never assume all TXT rows have five columns. Empty `shapes` means unlabelled or reviewed-negative only when reviewer provenance says so; it does not prove a negative example. Class allowlists come from the dataset mapping, not the four object classes for all tasks.

- [ ] **Step 4: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_audit_annotations.py -q`
Expected: PASS.

### Task 5: Split leakage check and 600-frame review sample

**Files:**
- Create: `E:/NBA-Audit-Toolkit/tools/split_and_sample.py`
- Create: `E:/NBA-Audit-Toolkit/reports/human_review_template.csv`
- Test: `E:/NBA-Audit-Toolkit/tests/test_split_and_sample.py`

**Interfaces:**
- `check_split_leakage(records: list[dict]) -> dict`
- `sample_review_candidates(records: list[dict], count: int, seed: int) -> list[dict]`

- [ ] **Step 1: Write failing tests**

```python
def test_same_video_in_train_and_test_is_leakage():
    rows = [{"video_id": "g1", "split": "train"}, {"video_id": "g1", "split": "test"}]
    assert check_split_leakage(rows)["leakage_count"] == 1
```

- [ ] **Step 2: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_split_and_sample.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement split and sampling**

Group by canonical game/video ID first, then content SHA-256; equal stems are warnings, not proof of duplicate content. Unknown video IDs or split assignments yield NOT_RUN, never a leakage PASS. Use deterministic seed 20261008 and default count 600, capped by available unique candidates; fewer than 500 means insufficient evidence and fails sample acceptance. Exclude held-out test videos from development review. Output `human_pending` rows with source path, hash, split, reviewer fields, and suggestions only when an existing model actually provides them. Valid/val/validation denote the same validation set for model selection; test denotes a separate frozen final evaluation set. Never tune from test results.

- [ ] **Step 4: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_split_and_sample.py -q`
Expected: PASS.

### Task 6: Agent prompts and runbook

**Files:**
- Create: `E:/NBA-Audit-Toolkit/prompts/main_orchestrator.md`
- Create: `E:/NBA-Audit-Toolkit/prompts/subagents.md`
- Create: `E:/NBA-Audit-Toolkit/reports/agent_runbook.md`
- Create: `E:/NBA-Audit-Toolkit/tools/validate_prompts.py`

**Interfaces:**
- Prompt templates consume `dataset_manifest.json`, `annotation_audit.json`, `repo_sources.json`, and smoke test JSON.
- Each prompt emits named report files and a gate status.

- [ ] **Step 1: Write prompt contract examples**

Include objective, inputs, outputs, allowed paths, prohibited actions, stop conditions, and exact validation commands for the main Agent and six Subagents.

- [ ] **Step 2: Validate prompt references**

Run a script that checks every referenced input and output filename is defined in the runbook.

- [ ] **Step 3: Run validation**

Run: `python E:/NBA-Audit-Toolkit/tools/validate_prompts.py`
Expected: `PASS` with zero undefined artifacts.

### Task 7: Local smoke test and report assembly

**Files:**
- Create: `E:/NBA-Audit-Toolkit/tools/run_smoke_test.py`
- Create: `E:/NBA-Audit-Toolkit/tools/build_reports.py`
- Create: `E:/NBA-Audit-Toolkit/tools/run_audit.ps1`
- Create: `E:/NBA-Audit-Toolkit/tools/run_audit.py`
- Test: `E:/NBA-Audit-Toolkit/tests/test_report_assembly.py`

**Interfaces:**
- `run_smoke_test(project_root: Path, output_dir: Path) -> dict`
- `build_reports(run_dir: Path) -> list[Path]`

- [ ] **Step 1: Write failing report test**

```python
def test_report_lists_failed_gate(tmp_path):
    (tmp_path / "annotation_audit.json").write_text('{"gate":"FAIL"}', encoding="utf-8")
    report = build_reports(tmp_path)[0].read_text(encoding="utf-8")
    assert "FAIL" in report
```

- [ ] **Step 2: Run test**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests/test_report_assembly.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement smoke test**

Inspect `E:/NBA_Workspace/sagemaker/train_court.py` before reusing its data contract; do not execute its cloud launcher. Prefer local `E:/court_v4_train/` checkpoint candidates after checking existence and dataset class mapping. Use a dedicated environment under the toolkit; log any dependency installation and do not modify shared environments. A successful smoke requires real audited train/val samples, finite training loss, checkpoint save/reload and validation execution. Import or synthetic probes are explicitly preliminary and cannot satisfy that gate. Limit the local smoke to one epoch, 32 training images, 16 validation images, workers=0 and 15 minutes wall time; save all outputs under the run directory. Record exact sample hashes, dependency versions, device and duration. If no valid train/val groups exist, stop that stage with NOT_RUN and continue reports. CPU fallback is permitted. Estimate full-epoch time only from measured step throughput and target dataset size, with validation and checkpoint overhead; otherwise output null.

- [ ] **Step 4: Implement report assembly**

Create a timestamped run directory under `E:/NBA-Audit-Toolkit/runs/`, write JSON artifacts and Markdown reports, and include a final gate table with `PASS`, `FAIL`, `NOT_RUN`, or `UNSYNCED`.

- [ ] **Step 5: Add PowerShell entrypoint**

`run_audit.ps1` invokes source scan, GitHub audit, annotation audit, split/sample, smoke test, and report assembly with `-WhatIf` behavior for any AWS command.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest E:/NBA-Audit-Toolkit/tests -q`
Expected: all tests pass.

## Final Verification

### Task 8: Player/spatial provenance and AWS read-only preflight

**Files:**
- Create: `E:/NBA-Audit-Toolkit/tools/audit_player_sources.py`
- Create: `E:/NBA-Audit-Toolkit/tools/aws_preflight.py`
- Test: `E:/NBA-Audit-Toolkit/tests/test_preflight.py`
- Outputs per run: `player_sources.json`, `cloud_preflight.json`, `cloud_preflight.md`.

**Interfaces:**
- `audit_player_sources(paths: list[Path]) -> dict`: emits source file, source URL when documented, as-of date, units, feature name, measured/proxy/missing status. Unknown height, wingspan or probability stays null. Pose heading is a gaze proxy, not measured eye gaze; spatial Gaussian scores are not calibrated scoring probabilities.
- `preflight_commands() -> list[list[str]]`: returns only STS get-caller-identity, EC2 describe-instances/describe-volumes, S3API list-buckets, ECR describe-repositories, SageMaker list-training-jobs. Each command includes `--profile nba --region us-east-1 --no-cli-pager`; set timeouts and never print tokens.

- [ ] **Step 1: Pin the permission boundary with a test**

```python
from tools.aws_preflight import preflight_commands

def test_read_only_explicit_profile_region():
    allowed = {("sts", "get-caller-identity"), ("ec2", "describe-instances"),
               ("ec2", "describe-volumes"), ("s3api", "list-buckets"),
               ("ecr", "describe-repositories"), ("sagemaker", "list-training-jobs")}
    for cmd in preflight_commands():
        assert tuple(cmd[1:3]) in allowed
        assert cmd[cmd.index("--profile") + 1] == "nba"
        assert cmd[cmd.index("--region") + 1] == "us-east-1"
```

- [ ] **Step 2:** Run `python -m pytest tests/test_preflight.py -q` from the toolkit root, implement the allowlist and account check (`766815611718`, assumed role `NBAHackathonParticipantRole`), rerun to PASS. Other cloud queries must not run if identity verification fails.
- [ ] **Step 3:** With `--aws-preflight`, collect query status, instance types and volume capacity. Cloud API metadata cannot prove current GPU utilization, filesystem free space or network throughput: these remain unmeasured until a permitted host probe exists.
- [ ] **Step 4:** Read the existing court-v5 local status/log timestamps without running its launcher or changing processes. Document the old README's active-training claim as historical unless fresh evidence confirms it.
- [ ] **Step 5:** Build source/use/implementation/annotation/limitations tables into the handoff manual. Missing licenses or player-source evidence remain explicit unresolved items.

### Execution and model routing

The requested GLM5.3 and GLM5.3flash names are requested routes, not verified provider model IDs. Main Agent and difficult review tasks route to the configured GLM5.3 ID; bounded inventory/report tasks route to the configured flash ID. Verify both IDs through the user-selected provider before any call. No API key is copied from another agent's logs. Without a verified provider, deliver portable prompts and record MODEL_UNAVAILABLE; do not claim GLM executed them or silently substitute another model. Three concurrent workers maximum, isolated output paths, one main writer for shared artifacts. Dependencies: source audit -> annotation audit -> split checks -> smoke -> final report; player provenance and read-only cloud preflight can run alongside source audit.

### Acceptance run

- Run `python E:/NBA-Audit-Toolkit/tools/run_audit.py --config E:/NBA-Audit-Toolkit/config.json` in read-only mode.
- Confirm the output contains source manifest, GitHub SHA or `UNSYNCED`, annotation audit, leakage result, 600-row human review CSV, smoke test status and handoff manual.
- Confirm no `.pem`, AWS cache or credential value appears in any output using a filename and content scan.
- Confirm `aws sts`, `ec2`, `s3`, `ecr`, and `sagemaker` calls are absent unless the explicit read-only preflight flag is set.
- Review all reports before considering the first phase complete.

Self-review note: this document describes planned work only. No tests, data audit, training or model-provider invocation has run as part of writing the plan. Insufficient evidence must keep the corresponding gate unresolved even if report generation succeeds.
