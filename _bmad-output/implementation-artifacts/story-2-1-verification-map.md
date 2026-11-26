# Story 2.1 · 验证证据索引和上线提案

本文件是运行入口和证据对照，不是通过证明。仅在普通 Windows PowerShell 内用原项目 `.venv`、Chrome 和预建的 `127.0.0.1:5433/test_lab_booking` 执行。不得在该脚本运行时另行修改或使用同一隔离库做独立验证。

本工作区已完成首次迁移、90 项回归、权限组及全部定向复验。[实际逐项结果、原始路径和评审交接](story-2-1-dev-evidence.md#2026-11-26-复验核验与独立评审交接)是当前证据索引。下方首次入口及[定向复验命令](story-2-1-dev-evidence.md#2026-11-26-原始失败取证与定向复验)为历史命令，不重复应用完整补丁或重跑已有结果。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\_bmad-output\implementation-artifacts\verify-story-2-1.ps1
```

凭据或 Chrome 不在预检默认位置时传入 `-Passfile` 和 `-Chrome`。脚本每次写独立目录，包含阶段退出码、命令以及分离的标准输出和错误、迁移计划与 SQL、输入 SHA-256、回归发现/执行/通过/跳过统计、隔离库前后完整行摘要、每组逐例 JSONL 和清理证明。边界组按数据库实际时间等待下一合法的北京时间整点，23:00 不作为开始时间。等待时不持有设备锁，开始前约 12 秒才启动竞争。不以可控时间替换该实测。

| 正式 AC | 断言及证据位置 |
| --- | --- |
| AC-1 | `regression` 师生逐项字段、201、本人链接及立即冲突；`permissions` HTTP 正控制；`nfr001-standard` 独立提交后读回 |
| AC-2 | `permissions` 状态、主体和路径、真实 CSRF、伪造字段控制和逐例前后数据；`interleavings` I6 锁后撤权 |
| AC-3 | `regression` B1 前/等/后及 B2 北京时间矩阵、UTC 往返；`time-boundaries` B3/B4 真实时间 |
| AC-4 | `interleavings` I2/I3 维修及停用各两次方向、独立锁阻塞及已提交设备/预约/历史 |
| AC-5 | `regression` 完整重叠/相邻/跨设备/状态矩阵；`interleavings` I1 实际竞争和相邻/跨设备控制 |
| AC-6 | `interleavings` I4 正反，旧预约/历史/无关设备；`regression` R-04 用 PostgreSQL 检查约束、两类外键和删除约束 |
| AC-7 | `time-boundaries` B3/B4 唯一业务采样、真实阻塞、时序及独立读回，B4 分开记录原行状态与有效占用 |
| AC-8 | `interleavings` I5 不可用、时间非法、仍有冲突分别保存独立前后快照；`regression` 验证 POST 提交业务拒绝后渲染不再读取设备 |
| AC-9 | `faults` F1 各 INSERT 实际 23514、F2 PostgreSQL 延迟约束 23505、F3 实际断连未落库、F4 已真实落库并模拟确认丢失；`regression` 注入提交返回的 55P03、57014、08006、40003 及无 SQLSTATE，验证分类与 Epic 1 兼容 |
| AC-10 | `permissions` 本人已结束待审核及重复读取、他人同不存在、合法 CSRF 的不支持方法；`interleavings` I6/I7 锁后撤权、终态无锁及固定候选 |
| AC-11 | `nfr001-standard` 10 × 20、每轮 20 独立 PID、实际持锁期重叠证明、全部 HTTP 响应及最终存量。无响应、其他失败不算冲突，无速度结论 |

## 正式库迁移和最小权限提案（未执行）

另行取得正式库授权后，由既有迁移角色和连接守卫核验精确数据库、角色、地址、端口、版本、目标 schema、对象所有者及迁移计划。备份并按依赖顺序应用 `reservations.0001_initial`、`audit.0001_initial`。先审阅经隔离库生成的迁移 SQL 和实际运行语句。以下是 ACL 审阅范围，不是可直接运行的正式库脚本。

| 表 | 拟给应用角色的列权限 |
| --- | --- |
| `public.reservations_reservation` | SELECT `id, applicant_id, equipment_id, start_at, end_at, status, applied_at`；INSERT `applicant_id, equipment_id, start_at, end_at, status, applied_at`；UPDATE `status` |
| `public.audit_operationhistory` | INSERT `object_type, reservation_id, equipment_id, action, before_status, after_status, actor_type, actor_id, reason, decision_at, recorded_at`；仅 SELECT `id` 供 ORM 的 RETURNING |

不预授序列权限，先核验实际 identity 和 INSERT 所需权限。沿用已有设备读取及基础字段 UPDATE 以支持行锁，不扩展设备状态写权限或账号权限。不授 DELETE、对象所有权、DDL、转授权、整表通配或默认全权。权限变更前后应核对 schema 限定列、角色、对象所有者、迁移和有效 ACL。正式环境不运行故障注入、标准竞争、回归或 fixture 清理命令。


## D-042 当前验收结果

上文是设计及历史入口，不是待重复命令。当前正式 AC-1～AC-11 通过，Story 2.1 已最终验收。D-040 的实际隔离批次 91/91、导航 1/1、Chrome 1/1、13/13 拒绝、15/15 交错，与旧 20×10、5/5、18:00 分组保存，不重复运行。正式库备份、迁移、ACL 22023 失败、修复、只读恢复、单次实际授权、Chrome 和独立回读均可追踪。 [最终验收及逐 AC](story-2-1-final-acceptance.md) · [D-040 原始图谱](story-2-1-targeted-independent-recheck/d040-independent-final-review.md) · [正式运行实际索引](story-2-1-runtime-evidence.md) · [R-04/T-01～T-04 与保留项](story-2-1-final-acceptance.md#正式-ac-核验)
