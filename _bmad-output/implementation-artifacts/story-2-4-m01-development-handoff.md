# Story 2.4 · M01 开发专项验证交接

2026-11-28（北京时间）。原 BMAD 6.12.4 Build 按 D-055 仅整改 AC-3 的 M01。代码已落盘，规格和 Sprint 仍为 `in-progress`，M01 尚未标关闭。本轮 Python／PowerShell 静态解析、测试名称、既有 125 项账本散列及差异范围已核对。未重复尝试沙箱已有的原 `.venv` 退出 103，当前无新版 Django、PostgreSQL 或 Chrome 实测结果。 [独立评审原处置](story-2-4-remediation-handoff.md)

- 本人取消 POST 只接受实际确认页使用的 URL 编码表单。校验原始字节、声明长度、百分号编码和恰一项有效形状的 `csrfmiddlewaretoken`，拒绝空缺、重复、未知字段、额外分隔符、流不可读和 multipart。Django 继续负责实际 CSRF 令牌匹配。输入拒绝先于取消服务、预约／设备查询、锁、取时和历史写入。设备锁、归属、FR-018、占用和事务未改。HTTP 服务器未交付给 Django 的报文分帧不由视图解析。
- 复用现有验证脚本、预检、真实 HTTP／SQL 与基线探针、Chrome、UTF-8／原生退出码及 Windows 文件共享。专项预期 5 项 Django（含两个新增、三个受影响的原用例）和 2 组探针 `V01-M01`、`Chrome`。探针核对未来及到期待审各 10 个格式负例、各 2 个 CSRF 拒绝，拒绝零业务 SQL／锁／取时／写入，观察连接逐例比对预约、设备、占用、历史。合法同目标控制验证 200 取消或 409 且持久失效，重复零写，师生用浏览器原生表单对照。格式与 CSRF 补例独立记录，不改变原 NFR-002 分母。Django 另外覆盖流截断和读取失败。
- 不重跑整改前有效的 133 项历史批次或 NFR-001 标准组。独立评审会话完成针对性复审后再跑一次完整隔离复验，去掉 `-M01Only`，预期为 125 项同名既有 + 10 个本 Story Django 测试、17 个探针组。开发专项与独立全量结果不混用。P01～P13、D01、R01 维持原处置。

## 普通 Windows PowerShell

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\verify-story-2-4.ps1' -M01Only -OutputRoot 'F:\softwork\outputs'
```

只连接 `127.0.0.1:5433/test_lab_booking`，沿用原 Python 3.13.17、Django 5.2.19、PostgreSQL 17.12、Read Committed。脚本自动建立新证据目录，保存原生阶段退出码、逐名测试、原始输入散列、HTTP／SQL 附证、三份隔离基线和夹具清理、两角色 Chrome 截图。完整成功标记 `STORY24_M01_DEV_OK`。失败保留本批原始文件和基线读回，不假报成功。

专项原证核对通过后才同步回 `review`，交回原独立 Code Review 会话。不操作正式库、不迁移或授权、不开发 2.6／2.7、不标 `done`、不自动提交或推送。课程执行仍按仓库课程基线及团队 PPT 核对记录，不声称直接取得原页。三人共同操作和审阅，Sprint 8／5 和实验 A 冻结条件不变。
