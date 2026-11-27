# Story 2.5 · 开发自测交接

2026-11-27（北京时间）｜BMAD 6.12.4 Build Step 3 · `in-progress`。负责人已批准规格，不等同于正式数据库授权、独立评审或最终验收。 [实施规格](spec-2-5-admin-reservation-query.md) · [正式 AC 与验收设计](story-2-5-checkpoint-1.md)

**后续状态。** 共享补丁已由团队成功应用。首次实际回归的失败和最新复验命令见[整改复验](story-2-5-regression-remediation.md)。下文保留首次交接记录，不再重复应用原补丁。

## 一次普通 PowerShell 运行

用普通 Windows PowerShell 打开项目仓库根目录。先应用已经落盘的单文件补丁，再读取或运行验证脚本。补丁只连接 `equipment/services.py` 的原管理员谓词与共享策略，验证脚本本身已经落盘，不在补丁内。不要暂存旧日志、锁或证据。

```powershell
$story25Patch = '.\_bmad-output\implementation-artifacts\story-2-5-equipment-policy.patch'
git apply --check -- $story25Patch
if ($LASTEXITCODE -ne 0) { throw 'Story 2.5 patch check failed' }
git apply -- $story25Patch
if ($LASTEXITCODE -ne 0) { throw 'Story 2.5 patch apply failed' }
& '.\_bmad-output\implementation-artifacts\verify-story-2-5.ps1'
```

执行器沿用原 `.venv`、Python 3.13.17、Django 5.2.19 与 PostgreSQL 17.12。它仅连接 `127.0.0.1:5433/test_lab_booking`，检查 `lab_booking_test`、Read Committed、现存迁移、无越权及清理。若该机的受保护 passfile 或 Chrome 不在默认位置，使用脚本现有 `-Passfile` 和 `-Chrome` 参数传实际路径，不上传凭据。不要并跑其他隔离验证。不重装解释器、不重建 `.venv`。

## 必须获得的实际结果

- 从真实输出核对原 113 项测试同名执行、12 项新增测试，合计 **125 项、零跳过**。17 项独立探针不算作 Django 测试。它们覆盖 AC-1～8 的五态与历史字段、筛选、双状态、升序锁、固定候选、锁后撤权、交错、跨时刻和已确认回滚／提交未知。未授权各例独立保存前后预约、设备、有效占用和历史并查 SQL、响应及授权对照。
- 只认 `STORY25_VERIFICATION_OK` 唯一完整行、执行器成功退出，以及新目录内原始日志、阶段退出、三份隔离基线、真实逐例 JSONL 和前后输入散列。回传新证据目录路径和实际成功或失败，不需要填写表格。
- 现有 NFR-001 标准竞争为 [D-040 原证据](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)。本次未改旧申请／冲突／时钟／失效写入机制，不重复跑 20×10，也不等待整点；2.5 交错和故障另行真跑。

## 已发生的结果与限制

- 已读 Story 范围内的统一差异。补丁只改 `equipment/services.py` 两处，通过 `git apply --check`。已有 CRLF 不重写，Git 以 `core.whitespace=cr-at-eol` 检查真实尾随空白。PowerShell 语法检查通过，原基线清单为 113 个唯一名称，12 个新增名称与执行器逐项相同。这些只是静态检查。
- 沙箱原解释器启动返回 `103`。实际包装批次在预检退出 `1`，未连 PostgreSQL、未跑任何 Django 用例或探针。保留原失败及一致的该批次前后散列清单，不冒充本版测试回执。 [预检错误原文](story-2-5-run-20261127-173818-443-937b04c8b2124b5a9a93053ff31509e9/preflight.stderr.txt) · [原阶段状态](story-2-5-run-20261127-173818-443-937b04c8b2124b5a9a93053ff31509e9/stages.txt)
- 真实自测前保持 `in-progress`，不执行独立评审、正式浏览器、正式库授权、提交或推送。证据矩阵通过后才进 `review`，由新会话进行 `bmad-code-review`。正式运行和 AC-6 所需五列权限仍单独批准。旧日志、锁、Story 2.2 证据和中央延期台账不改。
