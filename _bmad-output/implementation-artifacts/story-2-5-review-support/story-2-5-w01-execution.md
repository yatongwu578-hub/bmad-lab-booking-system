# Story 2.5 · W01 实际运行准备与取证手册

**D-051 后续。** 首批正式运行在 GRANT 前回滚。原执行命令停用，当前安全入口见[故障与恢复记录](../story-2-5-w01-recovery-evidence.md)。以下是历史设计，只作追溯，不作为手工操作、授权或恢复入口。

M01 整改后隔离实跑已经具备代码问题关闭条件。W01 仍是 High 正式发布门槛。这里的只读检查和取证工具已准备，**尚未连接正式库或执行 GRANT、迁移、正式浏览器验证**。只读准备、授权和正式运行结果分三段记证。 [隔离独立回执](../story-2-5-m01-independent-run-result.md) · [最小正式运行边界](story-2-5-minimal-formal-run.md)

## 1. 现在只做正式只读预检

本轮沙箱无法使用现有受保护 passfile，在凭据预检查阶段返回访问拒绝，因此没有当前 ACL 或样本实测。普通 PowerShell 从项目根运行：

```powershell
Set-Location -LiteralPath 'F:\softwork\SE-Management\bmad-lab-booking-system'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\_bmad-output\implementation-artifacts\story-2-5-review-support\inspect-story-2-5-w01.ps1'
```

如使用非默认的已批准本机密码文件，只加 `-Passfile` 的绝对路径，不提交文件内容。预检查用原 psql、无交互 `-X -w`，校验 `127.0.0.1:5433/lab_booking`、`lab_booking_app`、17.12 和只读事务。只要有环境连接覆盖、角色异常、现权意外、端口探测失败或原生 SQL 非零退出，不猜测、不执行第二命令，先保留首次失败目录。

- SQL 始终限定 schema、表和字段别名，区分有效权限及显式 ACL。NULL／空 ACL 经 `CROSS JOIN LATERAL aclexplode` 无行，然后聚合为合法 JSON 空数组。读回使用类型化对象比较授权列和布尔值，不比较 tuple/list 的外观。
- 新目录自动记录原始输出、错误、退出码、有效及显式 ACL、已存在的账号角色统计、现有预约状态数、安全详情 ID、目标设备和 20 分钟风险窗口、实测端口状态。不输出密码、会话、真实用户名或申请原因。只接受退出 0 和唯一整行 `STORY25_W01_INSPECT_OK`。请只保留/回传这一目录，无需手填数据。
- `acl_result=EXACT_COLUMNS_PRESENT` 即不需要 GRANT。若显示 `MISSING_COLUMNS`，`proposed-grant-not-executed.txt` 只列当前缺量，**脚本不会执行它**。允许差集仅为 `actor_id, before_status, after_status, decision_at, recorded_at`。若五列全缺，完整差集示例如下。只有实际缺量获授权后才由既有有权角色操作。不可授表级权限、WITH GRANT OPTION、新写权或其他列，无迁移。

```sql
GRANT SELECT (actor_id, before_status, after_status, decision_at, recorded_at)
ON TABLE public.audit_operationhistory TO lab_booking_app;
```

## 2. 精确 ACL 到位后的一次正式窗口

以下是待执行程序，不是现有正式回执。步骤 1 的 JSON 保留为 `$AclBefore` 的绝对路径。再次运行上述预检脚本，追加 `-BeforeEvidence $AclBefore -CaptureSnapshot`。该步保留精确有效和显式差集，并捕获业务基线的有序行数及 SHA-256。若本来已具备精确列权，同样用初始回执比较，不重授。此后关联本次生成的 `w01-inspect.json` 为 `$SmokeBefore`，其父目录为 `$Smoke`。任何新增列 SELECT 以外的有效或显式 ACL 漂移停止，不借机改权。

安全范围以该机实测为准。筛选只选择一个现有设备，详情优先选已有历史的终态预约。全量、目标设备、单详情分别计算 FR-018 风险，有已到期待审或窗口内会到点则不访问该范围。优先用已存在的安全记录，无有效筛选匹配时可证现有设备的空态。正式 AC 的范围明确允许用测试夹具验证预约与处理历史，AC-6/7 后续验证也明确要求真实持久化历史夹具。因此欠缺状态由本次真实隔离证据支撑，报告标注现场缺项，不创建演示预约、不改时钟。

1. 验证现有学生、教师、管理员三类预置账号可用，登录使用同源原生表单和现有 CSRF，不复用旧会话，不改受信来源配置。备选端口 8005 必须在开窗时再次确认；不复用 8000／8001，服务器绑定即验证无冲突。原 `.venv` 使用既有受保护 runtime 环境变量，无其他数据库连接。另一个 PowerShell 窗口启动下列证据守卫服务器，且不要自动重载。只在批准的正式窗口使用。

   ```powershell
   $Support = '.\_bmad-output\implementation-artifacts\story-2-5-review-support'
   & '.\.venv\Scripts\python.exe' -B "$Support\serve-story-2-5-w01-smoke.py" --inspection $SmokeBefore --events (Join-Path $Smoke 'server-http.jsonl')
   ```

   只接受 `STORY25_W01_SMOKE_READY`。它不使用会让合法设备行锁失败的数据库只读会话代替服务端守卫。浏览器请求内只允许受控读取、合法锁及登录／登出的会话技术写入，原生登录仅另允许 `last_login` 单列更新。预约、设备、历史 DML、其他账户写入和未知 SQL 都不执行。已锁候选在窗口内发生意外跨界时，守卫拒绝而不是把错误当成空态，保留首批证据。观察连接本身始终只读。

2. 每个角色用独立本机 Chrome profile，profile 存系统临时目录，不能放入证据或 Git。开专用 loopback CDP 端口（Chrome `--remote-debugging-port=0` 并从该 profile 的 `DevToolsActivePort` 取实际端口）。只开一个页签，初始 `about:blank`。启动采集器后等 `STORY25_CHROME_CAPTURE_READY` 再正常操作。同一正式 origin，用户名和密码只输入本机浏览器原生登录表单。

   ```powershell
   # $Role 取 anonymous、student、teacher、admin；$CdpPort 为该专用 Chrome 端口。
   node "$Support\capture-story-2-5-browser.mjs" --origin "http://127.0.0.1:$SmokePort" --debug $CdpPort --role $Role --out (Join-Path $Smoke "$Role.jsonl")
   ```

   匿名对所有安全范围预期 302 到登录，学生和教师以本角色登录后相同范围直访 403。管理员从身份进入安全的全量或用已审查设备编号进入筛选，查看安全详情和历史；若筛选有结果，使用该行详情与原筛选返回导航。全量路径因到期风险不可用时不点击通往全量的链接，安全筛选可直接进入，正式全量记未实测。机器采集 Chrome 实际请求、状态、跳转、缓存头、正文 SHA-256 与大小，服务端同步记录路径、状态和守卫；不归档 Cookie、Authorization、输入的密码、CSRF、正式响应的明文个人数据或原始 CDP 帧。若仍需截图，只对必要区域脱敏。每个角色须等采集器完成后才关闭专用 Chrome。三位组员共同确认业务身份、入口、摘要／历史、返回及空态体验，不填逐例表。

3. 关闭本次服务器（不得终止旧实例），再用只读预检脚本追加 `-BeforeEvidence $SmokeBefore -CaptureSnapshot`，获得 `$SmokeAfter`。SQL 快照的账密只在数据库内参与安全摘要，不输出明文，业务摘要对比不包含 session 和获准的登录时间。最后离线归档自动裁决：

   ```powershell
   & '.\.venv\Scripts\python.exe' -B "$Support\check-story-2-5-w01-smoke.py" --before $SmokeBefore --after $SmokeAfter --server (Join-Path $Smoke 'server-http.jsonl') --anonymous (Join-Path $Smoke 'anonymous.jsonl') --student (Join-Path $Smoke 'student.jsonl') --teacher (Join-Path $Smoke 'teacher.jsonl') --admin (Join-Path $Smoke 'admin.jsonl') --result (Join-Path $Smoke 'smoke-result.json')
   ```

   机器比对真实方法／路径／参数散列／状态分布、每角色预期、正文散列、禁止缓存、守卫结果、业务数据和 ACL 前后。只接受退出 0 和唯一 `STORY25_W01_SMOKE_EVIDENCE_OK`；采集工具的 `READY` 不是通过。归档文件都独占创建，脚本不重用旧目录或重试，失败也保留首批。该终行仅说明机器实测完成，不能代替负责人最终决定。

本轮只完成准备和离线语法检查，以上正式流程还没有现场结果。不为补样本扩大授权、添写预约、执行迁移或改变 Sprint 边界。
