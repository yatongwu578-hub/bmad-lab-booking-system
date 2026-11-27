# Story 2.3 隔离验证交接

当前状态为 `in-progress`。BMAD 6.12.4 Step 3 已落实实现与验证入口，真实执行尚待普通 PowerShell。源文件已直接落盘，当前工作区不需要应用补丁。基线 `c4912cb911ffeccbd4a8cfefa0b7eaaf26dab64d`。 [规格](spec-2-3-query-own-reservations.md) · [Checkpoint 1](story-2-3-checkpoint-1.md)

## 在普通 Windows PowerShell 运行一次

与其他验证入口串行运行。不停旧的 8000、8001 服务，不读取或打印密码文件。默认使用现有受保护 `PGPASSFILE`；不在默认位置时向脚本传绝对路径 `-Passfile`。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
Get-Content -Encoding UTF8 -LiteralPath '.\_bmad-output\implementation-artifacts\verify-story-2-3.ps1'
& '.\_bmad-output\implementation-artifacts\verify-story-2-3.ps1' -OutputRoot 'F:\softwork\outputs'
```

脚本先核对原 `.venv` 的 Python 3.13.17、Django 5.2.19、现有 Chrome 和 PostgreSQL 17.12 隔离身份，仅连接 `127.0.0.1:5433/test_lab_booking`。它不创建测试库、不迁移、不 flush、不接触正式库、不执行 GRANT，也不运行旧 20 请求 × 10 轮。新探针使用 OS 分配的独立 loopback 端口和独立会话，不共享旧服务的 Cookie。

仅在本次运行真实完成时预期出现一行 `STORY23_VERIFICATION_OK`。新目录 `story-2-3-run-*` 将记录命令、退出码、原始响应与日志、实际 103 个历史用例的逐名对照、10 个新增 Django 用例、15 个探针、前后输入散列和隔离基线。某阶段失败时保留其目录和输出，不把部分执行标成成功。若 PowerShell 组织策略阻止脚本，保留原错误，改在可运行现有本地仓库脚本的普通终端执行，不改系统级策略。

## 取证边界

- 沙箱本次对原解释器复核退出 `103`，因此未运行 Django 或 PostgreSQL 应用用例。静态代码检查、PowerShell 解析、历史测试清单计数、差异检查均不算本轮实测。
- 基线历史证据仅在核心路径未变时复用。2.3 扩展了本人详情的 SELECT 形状，2.1 旧独立 I7 的硬编码 SQL 快照仍按当时实现留存，本轮以新探针验证本入口，不重写历史评审工具或以旧 I7 代替本轮自测。
- 正式运行及浏览器体验不在本次执行范围。历史原因列级 SELECT 仍需先只读核对现权，再另行审批；本轮不部署、不执行 GRANT。
- 请回传新目录及最终回执或失败阶段。核对原始输出、散列、业务基线及全部 AC 后，才能推进 `review`，再开新会话执行独立 `bmad-code-review`。
