# Story 2.2 开发进度与验证交接

> 2026-11-26 补记：下文保留当时交接步骤。设备详情补丁已完整应用，真实批次已通过并核验，不要再应用或重跑。当前入口为 [开发证据及独立评审交接](story-2-2-dev-evidence.md)。

2026-11-26。负责人已批准 Checkpoint 1（D-043），实施规格与 Sprint 均为 `in-progress`。尚无本 Story 的动态结果。 [批准记录](../../decision-log.md#d-043-2026-11-26-负责人批准-story-22-checkpoint-1) · [逐 AC 验收设计](story-2-2-checkpoint-1.md#验收设计)

## 已落盘与仍未应用

- `reservations/` 已写入三角色日期占用路由、日期表单、固定候选查询、最小展示与错误分支。Story 2.1 的提交、本人结果、失效与历史、数据库判定时钟和事务分类实现未改。
- `equipment/views.py` 与详情模板的原路径拒绝写入，保留原文件。请在普通 PowerShell 先应用 [设备详情入口补丁](story-2-2-detail-wiring.patch)。仅这两处仍缺应用，补丁只增加查询入口和目标设备主键，不影响原导航，也不包含历史日志、锁或脚本。
- 12 项新增 Django 测试、21 项真实隔离 HTTP／PostgreSQL 验证场景均已编写。原 `.venv` 在本沙箱探测返回 103 后未重试。静态核对通过（六份 Python AST、PowerShell 语法、受控文件 diff 检查），补丁通过 `git apply --check`，并在隔离副本实际应用、核对改后的 Python 与入口导航。未连接测试库或正式库，未启动或停止原服务，未执行迁移、授权、暂存、提交或推送。

## 普通 PowerShell 单次验证

在仓库根目录运行。先应用补丁，再读取及执行验证脚本。若旧验证或部署正在运行，等它结束再运行本入口，不删除或覆盖旧锁和日志。

```powershell
$story22Patch = '.\_bmad-output\implementation-artifacts\story-2-2-detail-wiring.patch'
git apply --check -- $story22Patch
if ($LASTEXITCODE -ne 0) { throw 'Story 2.2 补丁预检失败，停止。' }
git apply -- $story22Patch
if ($LASTEXITCODE -ne 0) { throw 'Story 2.2 补丁未应用，停止。' }
Get-Content -Encoding UTF8 -LiteralPath '.\_bmad-output\implementation-artifacts\verify-story-2-2.ps1'
& '.\_bmad-output\implementation-artifacts\verify-story-2-2.ps1'
```

脚本使用原 Python 3.13.17、Django 5.2.19、PostgreSQL 17.12 和现存保护凭据。默认路径不同时可提供 `-Psql`、`-Passfile` 或 `-Chrome`，不要把凭据内容发回。它锁定本验证批次，先核对运行环境、模式、数据库身份和基线，再要求 103 项完整回归全部通过、零跳过，以及 21 项新增隔离探针及清理一致性通过。真实成功时最后应恰有一行 `STORY22_VERIFICATION_OK`。若失败，不覆盖本批原始结果。

请回传新 `story-2-2-run-*` 目录路径和最终阶段结果。需实际审计原始日志、退出码、输入散列、逐 AC 对应与清理后，才同步至 review 并交新会话独立评审。 [验证脚本](verify-story-2-2.ps1)
