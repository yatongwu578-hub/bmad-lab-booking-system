# Story 2.3 · 正式库授权与 Chrome 运行交接（尚未执行）

独立隔离复验已通过，无新增隔离验收阻塞。**W1 仍未关闭。本文件是就绪方案，不是访问正式库、授权或演示写入的批准。** 没有 schema 改动、无需新增迁移。不重放用于 2.1 或 2.2 的旧部署命令。 [独立复验](story-2-3-independent-recheck.md) · [负责人处置 D-047](../../decision-log.md#d-047-2026-11-27-负责人处置-story-23-独立评审)

## 1. 正式只读复核，再对确实缺少的四列授权

1. 在获批的正式窗口，于仓库根目录、普通 Windows PowerShell 执行下示只读脚本。使用现存受保护、仓库外的绝对 `PGPASSFILE`，不读出文件内容、不传明文密码。不存在时停，不能用其他库或角色替代。
2. 只读脚本固定 `lab_booking_app@127.0.0.1:5433/lab_booking`、PostgreSQL 17.12，事务只读，检查身份、12 个不重复物理列及表级读权。仅记录 0 退出、完整矩阵、唯一 `STORY23_ACL_READONLY_OK`。若 `EXACT_COLUMNS_PRESENT`，不授；若 `NEEDS_FOUR_COLUMN_GRANT`，只有在已经批准四列授权的前提下才执行下段。其他权限漂移、表级 SELECT、任何转授权或错误的身份即停。
3. 最近一次已核验正式回执的有效和直接 SELECT 都只有 `id`。新的投影 `SELECT DISTINCT ON (h.reservation_id) h.reservation_id, h.reason` 使用 `h.action`、`h.actor_type` 过滤，`h.id` 排序。当前角色范围内只增加 `reservation_id, action, actor_type, reason`。历史表和所有字段都显式限定，避免含歧义的 `id` 或 `status`。使用 `has_column_privilege`／`has_table_privilege`，**不展开 aclitem[]，不会把 NULL ACL 变为零维空数组**。如另读原始显式 ACL，应沿用已验证的 `aclexplode(CASE WHEN cardinality(acl)>0 THEN acl END)`，不要用 `COALESCE(acl, '{}'::aclitem[])`。
4. 未来获批后，用表所有者 `lab_booking_migrator` 运行独立 SQL。它事务内复核库、端点、角色及 ACL，只有精确 `id` 单列状态才执行唯一 GRANT；已齐全则回滚空事务并输出无需重复；其他状态拒绝。提交前再次检查终态矩阵，不授权 `actor_id`、历史时间、表级 SELECT、转授权、序列或其他表，不执行迁移。记录实际 psql 退出码和唯一 `STORY23_HISTORY_SELECT_COMMITTED` 或 `STORY23_HISTORY_SELECT_ALREADY_EXACT`。如果提交结果未知，先只读复核，不重复 GRANT。
5. 授权后仍须由 `lab_booking_app` 新连接只读验收，结果为 **只有** `action,actor_type,id,reason,reservation_id` 可读、`table_select|f|f`、无转授权，唯一 `ACL_RESULT=EXACT_COLUMNS_PRESENT` 和只读成功标记。通过后才启动正式浏览器。授权前后及浏览器后各留真实回执，候选 SQL 静态核对不冒充 PostgreSQL 执行。

```powershell
# 只在另行批准的正式窗口执行。先运行只读复核，保存实际输出。
$psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
& '.\_bmad-output\implementation-artifacts\read-story-2-3-audit-acl.ps1' -Psql $psql
```

```powershell
# 仅当上一步确认为 NEEDS_FOUR_COLUMN_GRANT 且四列授权已明确获批。
# 使用与上一步相同的既有受保护 passfile，先排除 PGHOST/PGPORT/PGDATABASE/PGUSER、
# PGHOSTADDR/PGSERVICE/PGSERVICEFILE/PGOPTIONS/PGPASSWORD 连接覆盖；拒绝凭据或环境漂移。
$psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
$grantFile = '.\_bmad-output\implementation-artifacts\story-2-3-history-select-reviewed.sql'
& $psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5433 -U lab_booking_migrator -d lab_booking -f $grantFile
if ($LASTEXITCODE -ne 0) { throw '保存原始错误。只读确认实际 ACL 后再决定，不重放。' }
& '.\_bmad-output\implementation-artifacts\read-story-2-3-audit-acl.ps1' -Psql $psql
```

授权 CLI 需要当前 PowerShell 环境中的 `PGPASSFILE` 已明确设为前一步所用现存受保护路径。若只读入口使用本机默认路径，`PGPASSFILE` 仍需先设为该路径（README 所述 `%LOCALAPPDATA%\LabBooking\PostgreSQL17\pgpass.conf`）。不将密码内容写进回执。 [只读核对脚本](read-story-2-3-audit-acl.ps1) · [四列事务授权稿](story-2-3-history-select-reviewed.sql) · [旧正式 ACL 原证](story-2-2-runtime-20261127-000918-77eb9198/acl.jsonl)

## 2. 端口、旧版本和真实 Chrome 会话

2026-11-27 11:50（北京时间）的只读本机检查发现 `127.0.0.1:8000` PID 1964 与 `127.0.0.1:8001` PID 38704 在监听，启动时间分别为 11-25 21:24:47 与 11-26 21:48:15。两个启动均早于 Story 2.3 文件修改，**无法从进程启动时间确认已加载的源码版本**，不视为 2.3，不向这两个监听发请求、不接管、不停止。8003 当时未监听，正式开窗时重新核对；如占用再选空闲端口，不抢占。Chrome 二进制文件版本读到 159.0.8154.34，尚未启动 Chrome 体验。

- 开窗时核对 [独立复验输入清单](story-2-3-independent-run-20261127-114813-950-de7b7f2c/before.sha256) 的运行源码。规格状态文档之后更新，源码及测试文件未动。此工作树的变更未提交，**不要用单独的 Git HEAD SHA 代替工作树版本证明**。记录输入清单散列、repo 路径的受控证明、新监听 PID 及启动时间。
- 在单独普通 PowerShell，按 README 设置受保护环境，选定空闲端口，使用原 `.venv\Scripts\python.exe` Python 3.13.17，以 runtime 模式、`--noreload` 启动新前台服务。启动后再从第二个终端核对实际监听地址和 PID，并在身份页看到经本 Story 加入的入口，避免旧页面冒充当前运行。
- 每个角色使用不同的全新 Chrome user-data-dir。Cookie 按主机而不是端口隔离，不能用「换端口＋同窗口」替代配置隔离。全程固定一个 origin，如 `http://127.0.0.1:8003`，不混用 `localhost`、其他端口或旧标签页。每个会话从当前服务重新 GET 登录或预约表单取得 CSRF。出现 403 后记录实际链路，再从该会话重新 GET 正确表单，不盲重放尤其是不确定结果的 POST。
- 仅用 Ctrl+C 停止本次实际启动的前台服务，不操作旧端口。若新监听出现错误，保存当前输出和 PID，不切回旧 8000/8001 当作已验。

```powershell
# 正式 ACL 后置只读矩阵通过后，且仅在另行批准的窗口。
$storyPort = 8003
if (@(netstat -ano -p tcp | Select-String (':{0}\s+\S+\s+LISTENING\s+' -f $storyPort)).Count) {
    throw '端口已占用。选择另一空闲端口并同步更新整个验证 origin。'
}
$env:LAB_BOOKING_DB_MODE = 'runtime'
& '.\.venv\Scripts\python.exe' manage.py runserver "127.0.0.1:$storyPort" --noreload
```

## 3. 演示数据、实操和证据

1. **预约业务只读烟测**：选获准的学生、教师账号。先只读核对其全部待审候选集合在预定结束时间（含安全余量）前不会到期。只选设备或日期不够，因为列表会处理本账号所有到期待审记录。如有可能触发 FR-018，不访问该账号的列表或到期详情，换获准安全样本，或待另行批准精确业务写入。记相关设备、预约、有效占用和审计前置摘要。登录的技术性会话写单列。
2. **两角色真实操作**：每个角色从身份页点击「我的预约」，进入一条本人详情再返回，记录列表范围、设备当前状态、预约状态、日期时间及实际两跳链接。合法拒绝／管理员取消原因若有安全既有样本，验证内容及授权；没有则记未覆盖并沿用隔离 AC-3，不造正式终态历史。管理员无入口及直访 403、获准同角色异主与缺失同形 404、匿名 302、空态按实际样本着录。
3. **201 成功链路须有另批的实际预约写入**。如果批准，两角色各挑获准专用设备和合法未来北京时间整点区间，预读设备可用、有效占用无冲突及到期收尾范围。区间须互不冲突，确保不会触发未批准的 FR-018 变更，只提交一次，记录允许的唯一新预约及关联增量。从成功页同时核对旧详情和「我的预约」两链接并实际点击。只批准读时不发 POST，201 正式浏览器分支如实记未执行。未知结果先只读确认，不补写、不借后续取消功能、不直接删记录。
4. **当场记事实**：每个请求分别记录实际角色/脱敏账号、对象归属、设备编号和 ID、预约 ID 与北京时段、完整实际 URL 和方法、HTTP 与重定向链、页面文字和脱敏截图编号。分开预期和实际；不用完整未脱敏 HAR，也不留账号密码、Cookie、CSRF。前后只读对照业务摘要及正式权限；仅允许记录已批准的增量。用空表当场记录，不从旧成功验收推断角色、设备或日期。 [Chrome 现场取证单](story-2-3-chrome-receipt-template.md)

三位组员共同操作和审阅，不分派个人任务。继续保持 Sprint 8／5、实验 A 和 Story 2.5 backlog。现阶段不标 `done`，不 commit/push。
