# Story 2.4 · M01 开发专项通过与复审交接

**BMAD 6.12.4 原 Build 的 M01 开发专项通过，Story 回到 `review`。** M01 保持开放，交回**原独立 Code Review 会话**执行针对性复审及一次完整独立复验。本页不是独立复验、最终验收或关闭决定。 [D-055 检查与处置](story-2-4-review-disposition.md) · [待复审规格](spec-2-4-cancel-own-reservation.md)

## 真实专项证据

团队从普通 Windows PowerShell 执行 `verify-story-2-4.ps1 -M01Only`。批次 `story-2-4-run-20261128-093324-529-61fd0ea2d3034839a2d9567cf9016e3d`，2026-11-28 09:33（北京时间）。实际环境为原 `.venv` Python 3.13.17、Django 5.2.19、PostgreSQL 17.12、`127.0.0.1:5433/test_lab_booking`、角色 `lab_booking_test`、显式 `read committed`。

- **5/5 项定向 Django、2/2 组探针。** 从 Django 原始逐名输出和 `STORY24_PROBE_OK cases=2` 复算，零跳过、缺失或额外测试。8 个阶段原生回执均退出 0，stdout／stderr 字节与散列一致；最终唯一 `STORY24_M01_DEV_OK`。外层控制台进程的独立退出码未单独归档，不补造。 [逐名结果](story-2-4-m01-dev-run-20261128-093324/passed-tests.txt) · [阶段](story-2-4-m01-dev-run-20261128-093324/stages.txt) · [终标记](story-2-4-m01-dev-run-20261128-093324/batch-marker.txt)
- **V01-M01 格式拒绝 20/20，补充 CSRF 拒绝 4/4。** 均用真实 HTTP 和已登录的预约本人。未来及到期待审核各 10 个格式用例，如命名或无名 multipart 分段、缺失和不完整内容、畸形百分号编码及重复字段；带有效 CSRF 头仍由业务入口在服务前返回 400。同两张夹具各 2 个缺失／无效 CSRF 由 Django 返回 403。拒绝全部零业务 SQL、零设备锁、零取时、零写或提交；逐次独立快照预约、设备、有效占用、历史均不变。补例不混入此前 NFR-002 权限分母。Django 定向用例还覆盖短读／不可读流、同形 404 及有效头不能替代错误请求体令牌。
- **合法控制与 Chrome 均通过。** 同一未来目标合法提交 200，原占用释放并原子记录一条本人取消；同一到期待审合法 POST 409，但正常提交恰一条系统失效。其重复请求都 409 且零业务写。真实 SQL 顺序为权限 → 设备锁 → 锁后权限与归属重读 → 唯一数据库时钟 → 状态／历史。Chrome 159.0.8154.34 对学生、教师各完成 6 个真实文档响应，含放弃确认零写、URL 编码原生提交及结果返回。 [HTTP、SQL 与独立快照](story-2-4-m01-dev-run-20261128-093324/independent.jsonl) · [学生确认](story-2-4-m01-dev-run-20261128-093324/chrome-student-confirm.png) · [教师结果](story-2-4-m01-dev-run-20261128-093324/chrome-teacher-result.png)
- **来源与清理。** 91 项运行前后输入清单相同，归档前与当时工作树重算。与整改前清单相比，仅取消视图、定向 Django、探针、现有运行器及本 Story 规格 5 项变化；共享取消服务、归属和角色复核、设备锁、时间边界、事务及模型未变。三份业务行摘要／ACL／表及迁移基线和探针首尾相同，`cleanup=true`，不推断序列未递增。48 个脱敏原件、执行时规格和机器回执均封存。 [机器回执](story-2-4-m01-dev-run-20261128-093324/verified-receipt.json) · [归档散列](story-2-4-m01-dev-run-20261128-093324/archive.sha256) · [运行时规格](story-2-4-m01-dev-run-20261128-093324/spec-at-run.md)

## 交回原独立评审会话

1. 复审仅针对这四个实施文件的 M01 差异：`reservations/views.py`、`reservations/test_own_cancellation.py`、`reservations/management/commands/verify_own_cancellation.py`、`_bmad-output/implementation-artifacts/verify-story-2-4.ps1`。先看原始表单长度和编码的拒绝闸口、原生确认正例及保障 AC-3 的零副作用证据。不处理 P01～P13、D01，R01 保持原裁决。
2. **一次独立全量应使用现工作树同一个运行器，不带 `-M01Only`。** 已静态核对：125 项既有同名测试 + 10 项本 Story Django（含两个 M01 新增）＝ **135 项**。17 组探针保留原 16 组并在 Chrome 前执行 `V01-M01`。新版包装 SHA-256 为 `71140E67C4BBB69F8C12F29C5F4CFBCD4E4EC12AA71E670BBDBE7D31344CC465`，与专项实际输入相符。启动后同时核对 91 项实际输入，不用整改前 133 项／16 组脚本版本，不将本次 5 项／2 组当成独立全量。
3. 完整路径按正式 AC 覆盖：A01-A05 及 Django 精确时间／终态覆盖 AC-1/2，P 组、V01-M01 和 Chrome 覆盖 AC-3 与原生确认，I08/09 覆盖 AC-4，A01-A05 及 A06、I06/07 覆盖 AC-5/6，I01～I09 覆盖 AC-7，A08 覆盖 AC-8。比对 T-01～T-04 和本 Story NFR-002 的原分母及补例。20×10 NFR-001 标准组沿用未失效的历史原证，新交错另计。 [正式 AC](../planning-artifacts/epics.md#story-24-取消本人尚未开始的预约) · [整改前证据](story-2-4-development-evidence.md)

原独立评审复核后才在普通 PowerShell 启动下面的完整批次，当前 Build 未运行。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\verify-story-2-4.ps1' -OutputRoot 'F:\softwork\outputs'
```

完整批次标记 `STORY24_VERIFICATION_OK`，另建目录，仍仅连接隔离库并串行。必须以真实独立原证判定 M01 是否可关闭。正式库权限及迁移实际核验仍在另行批准的发布前窗口，当前未操作正式库、未迁移或授权、未自动提交推送。Sprint 原 8／5、三人共同操作和审阅、实验 A 的冻结要求及 2.6／2.7 未开发状态不变。PPT 第 20～39 页沿课程基线及团队核对记录执行，不宣称取得原页。
