# Story 2.5 · 独立 Code Review 交接

新会话启动安装版 BMAD 6.12.4 的 `$bmad-code-review`，只评审「管理员查询预约详情并按设备筛选」。本开发会话完成 Step 3 的真实证据核对和评审状态同步，未运行独立评审层。规格 `in-review`，Sprint `review`，不标 `done`。三位成员共同操作与审阅。

## 输入与边界

- 基线 `1cedf9687208b20645b1acce3c7755e8525cd9fc`。对比本 Story 代码差异，纳入未跟踪的新文件，不暂存。排除历史日志、锁、临时目录、原始大批证据和其他 Story；证据另读。已应用的共享权限补丁不得重复应用。
- 产品代码：`accounts/policies.py`、`accounts/views.py`、`accounts/templates/accounts/identity.html`、`equipment/services.py`、`audit/services.py`、`reservations/{forms,services,urls,views}.py`、`reservations/templates/reservations/admin_{detail,list}.html`。验证代码：`reservations/test_{admin,own}_reservations.py`、`reservations/management/commands/verify_admin_reservations.py`、`verify-story-2-5.ps1`。规格、状态、决策与证据与代码差异分开审阅。
- [正式 Story 与 AC](../planning-artifacts/epics.md#story-25-管理员查询预约详情并按设备筛选) · [冻结意图与规格](spec-2-5-admin-reservation-query.md) · [开发证据与 AC 对照](story-2-5-dev-evidence.md) · [脱敏计数与散列](story-2-5-development-evidence.json) · [首批失败与整改](story-2-5-regression-remediation.md)

重点包括先授权、按设备／预约限定并冻结候选、升序设备锁和锁后撤权、唯一时刻和严格结束边界、实际历史投影和最小字段、原子失败/提交未知、导航和旧接口不回归。区分明确的真实 PostgreSQL 故障、实际持久化后模拟确认丢失、单测精确边界和交错真实边界。125 项全量、5 项针对性、17 项真实探针均通过，NFR-001 标准 20×10 是已经复算的历史证据。

独立评审优先检查正式 AC、安全性、数据一致性，不提前执行正式库授权或浏览器发布。若要独立真跑，只用 `127.0.0.1:5433/test_lab_booking`、原 `.venv` 和同库串行模式，证据另建目录。不改 Sprint 8／5 或实验 A，不提前 Sprint 2、不自动 commit/push。正式 ACL 五列缺口和现场验证另批，开发通过不能取代最终验收。

可直接在新会话发送：`$bmad-code-review 请按 Story 2.5 独立 Code Review 交接（_bmad-output/implementation-artifacts/story-2-5-code-review-handoff.md）执行，保留 review，不标 done。`
