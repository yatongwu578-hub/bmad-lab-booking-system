# Story 2.4 · M01 针对性独立复审

2026-11-28（北京时间）｜续接原 BMAD 6.12.4 full Code Review 的 D-055 整改回交。**未发现新增验收阻塞，可进入一次完整的普通 PowerShell 独立隔离复验。** M01 的关闭仍待实际独立运行，规格 `in-review`、看板 `review` 不变。本轮为独立静态复审与开发原证复算，不是独立实跑。 [正式 AC-3](../planning-artifacts/epics.md#story-24-取消本人尚未开始的预约) · [回交](story-2-4-m01-code-review-return.md) · [原处置](story-2-4-review-disposition.md)

## 范围与裁决

- 对照原审查基线 `33ff1eb86a1101db5033a4232a121a08d66a4c03` 及整改前、后 91 项 SHA-256 清单。实际实施差异限于取消视图、本人取消 Django 用例、真实探针和 PowerShell 包装四个文件，另有本 Story 规格变动。确认模板、本人取消服务、角色及归属、共享事务、设备锁、失效及数据库结构没有 M01 差异。
- **格式与原始字节。** `reservations/views.py::_valid_cancellation_form` 不再依赖可能丢弃信息的 `request.POST` 投影来决定业务是否开始。只接受 URL 编码，声明长度有界且与 Django 可见的字节数相等。拒绝空、不可读、截断的请求体、非法百分号转义，以及解码后不构成恰一项令牌字段的内容。字段名和令牌形状均按字节校验，多字段、重复和尾部分隔不能成为有效令牌。Django 仍负责 CSRF 真实性，错误表单令牌不能靠正确备用头替代。该验证范围是 Django 接收的实体，不宣称重验上游 HTTP 分帧。
- **业务副作用。** 格式闸口先于取消服务。专项未来和到期待审各有 10 个格式 400、2 个 CSRF 403。逐条按实际预约本人、方法、SQL/绑定、设备锁、取时、写入、事务尝试和独立快照复算，预约、设备、有效占用及历史全部不变。合法对照中未来目标 200 并写一条本人取消，到期待审核 409 并写一条系统失效，两者重复均 409 无业务写。补例不改变原 16/16 权限分母，也不外推为全项目 NFR-002。
- **原生表单。** 开发 Chrome 真实点击学生、教师的确认按钮，两角色共 12 条真实文档响应和 4 张截图。确认 DOM 为 URL 编码，放弃确认读回无写，合法提交后均成已取消、各一条历史并可返回。本轮查看了已归档截图，未启动新浏览器。继续保留 D-055 的 P01～P13、D01 与 R01，中央延期台账 SHA-256 未变。

## 机器原证核对

复算了 48 个开发原始文件、执行时规格和回执的 50 项归档散列，逐路核对 8 个实际阶段原生退出码、stdout/stderr 字节和散列。Django 实测 5/5 定向、零跳过，PostgreSQL/HTTP 与 Chrome 为 2/2 个专项探针组。运行前后 91 项散列一致，当前可直接匹配除评审过程规格以外的 90 项，运行规格由已封存快照匹配。三份隔离库基线逐字节一致，探针首尾快照一致，`cleanup=true`。外层控制台退出未独立入档，不代填。 [开发回执](story-2-4-m01-dev-run-20261128-093324/verified-receipt.json) · [HTTP/SQL 原证](story-2-4-m01-dev-run-20261128-093324/independent.jsonl)

申请竞争核心与已核验的 NFR-001 原始 JSONL 均未改变，将原 20 请求 × 10 轮留在历史标准组，不重复测试。其它原开发批、已批准延期和驳回不改。 [历史 NFR-001 索引](sprint-1-final-acceptance-2026-11-27.md#非功能实证)

## 一次完整的独立复验

从普通 Windows PowerShell 执行现版包装，**不带 `-M01Only`**。已静态确认实际账本和 Python/PowerShell 两端探针 ID 一致。只连接 `127.0.0.1:5433/test_lab_booking`，沿用受保护的 passfile、原 `.venv`、PostgreSQL 17.12 和真实 Chrome。不要并行跑其他验证器。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\verify-story-2-4.ps1' -OutputRoot 'F:\softwork\outputs'
```

完成信号为新证据目录、外层进程退出 0 和唯一 `STORY24_VERIFICATION_OK`。核对实际 135 项 Django（125 个既有同名 + 10 个 Story 2.4，零跳过）、17 组真实探针（含 V01-M01 及 Chrome）、8 阶段、权限原分母与补例分列、输入散列及隔离基线/清理。只需交回机器生成的目录，不填人工表格。失败保留原始阶段，不覆盖或当作通过，不并行补跑。正式运行方案在独立批通过后再按实际原证准备，优先复用 2.5 只读 ACL、样本检查、Chrome/CDP 和阶段归档。不得直接重放 2.5 授权或管理入口的正式脚本。 [2.5 参考方案](story-2-5-review-support/story-2-5-minimal-formal-run.md)

保留 FR→ADR／PC→AC→Test、真实决策及 Sprint 8／5。课程按仓库基线和既有 PPT 第 20～39 页页码核对，未直接取得 PPT 原件。三位组员共同操作与审阅，实验 A 未冻结前不开发 2.6 或 2.7。本轮未改业务代码、访问正式库、迁移或授权、标 `done`、自动提交或推送。
