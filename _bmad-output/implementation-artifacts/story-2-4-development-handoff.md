# Story 2.4 · 开发自测交接

当前为 BMAD 6.12.4 Build Step 3，规格和看板均为 `in-progress`。D-054 已获实施和隔离自测批准，但尚无新的真实 Django、PostgreSQL 或 Chrome 回执。原虚拟环境已有沙箱退出 103 记录，本轮不重试、未替换解释器。现有日志辅助脚本在沙箱内的加载也被 PowerShell 执行策略拒绝。静态检查不计入验收。 [负责人决定](../../decision-log.md#d-054-2026-11-27-负责人批准-story-24-checkpoint-1) · [正式矩阵](story-2-4-checkpoint-1.md)

- 已在工作树实现「我的预约」列表／详情的取消入口、只读确认、CSRF POST、结果反馈与返回。事务复用原权限复核、设备锁、数据库取时、FR-018 和异常分类；只修改目标预约状态，状态和新增历史同事务。开始时刻待审失效，已批准不变。
- 父执行者读取了隔离范围 unified diff。Python／PowerShell 语法、既有 125 名称原始 SHA-256、所有 148 个展开的历史工作树文件散列及 NFR-001 原 10 轮／200 响应只读核验通过。现有申请、冲突、设备锁及环境配置未变，不重跑 20×10，不把原证计为本轮。没有迁移文件或 GRANT 增量，发布前实际只读核验仍需后续授权。
- 预期批次含 125 项既有 + 8 项新增 Django，16 组 HTTP／PostgreSQL／Chrome 探针。其中权限拒绝计 14 个直接访问和 2 个锁中撤权，另列不入分母的非法输入、缺失和合法对照。真实数值以原回执核对后报告。

## 普通 Windows PowerShell 单次验证

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\verify-story-2-4.ps1' -OutputRoot 'F:\softwork\outputs'
```

[验证入口](verify-story-2-4.ps1) 复用原有受保护 passfile 和 Chrome，可通过 `-Passfile`、`-Chrome`、`-Psql` 传现有工具绝对路径，不提供密码内容。仅用 `127.0.0.1:5433/test_lab_booking` 上的 `lab_booking_test`，不连接正式库。运行时打印新的 `story-2-4-run-*` 证据目录，成功标记为唯一整行 `STORY24_VERIFICATION_OK`。失败也保留原始日志、实际退出及基线读回；不要覆盖原目录或据标记单独判断。

回传证据目录后核验输入散列、逐名结果、权限和时序断言、权限／数据库快照、Chrome 回执以及真实清理。满足冻结矩阵后才勾选通过并推进至 `review`，独立 `bmad-code-review` 另开会话。不提前 `done`，不改其他 Story、实验 A、正式库或 Git 索引，不 commit/push。
