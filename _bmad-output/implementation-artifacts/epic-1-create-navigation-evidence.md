# Epic 1 新增设备导航改进证据

2026-11-26，团队实际体验报告管理员登录后找不到新增设备入口。只读确认身份页和目录均无链接，详情只有既有编辑入口，而 Story 1.2 的真实 Chrome 已验证 `/equipment/new/` 表单及服务端角色限制。这与 Epic 1 回顾记录一致。负责人在 D-037 接受诊断，批准独立的非阻塞集成可用性改进，不重开 Story 1.1～1.4。 [Epic 1 回顾](epic-1-retro-2026-11-26.md) · [1.2 正式运行](story-1-2-runtime-evidence.md) · [D-037](../../decision-log.md#d-037-2026-11-26-负责人批准-epic-1-新增设备导航改进)

## 候选与实际状态

四文件 [增量补丁](epic-1-create-navigation.patch)，SHA-256 为 `A4392ED98CC2D8406A6BC708252181344D5E7481D94D302F39F7ABC30D951799`。

- `accounts/templates/accounts/identity.html` 在原「查看设备目录」旁包含共享链接。退出表单不变。
- `equipment/templates/equipment/catalog.html` 在列表／空态判断前包含同一链接。
- `equipment/templates/equipment/_create_link.html` 仅显示给启用且业务角色为 `admin` 的账号，使用已有 `equipment-create` 命名路由。模板隐藏不替代服务端鉴权。
- `equipment/test_create_navigation.py` 新增四项隔离测试。校验管理员从身份页及非空目录的真实渲染链接发 GET 进入既有表单，以及空目录管理员链接。检查师生原导航、隐藏新增及直达 403，包括教师即使有 Django staff／superuser 标记也不能越权。匿名及停用管理员保留登录 302，链接目标和 CSRF 隐藏字段正常。不提交新增表单，不创建正式演示设备。

**最初的沙箱受阻记录。** 沙箱拒绝写入现有目录模板，当时撤回身份页的局部写入。原虚拟环境 `--version` 在沙箱退出 103。补丁在真实工作区 `git apply --check` 通过，在独立临时副本应用和反向检查通过。当时只有离线语法检查与进程拒绝分支模拟，未实跑。之后团队已在普通 PowerShell 实际应用并验证，结果见下。

## 针对性独立评审

新独立会话 `nav_review` 仅评审该散列的四文件候选，未重审 Epic。静态未发现阻塞。两个视图使用真实 `request.user` 作为 `account`，已安装 equipment 模板目录可解析共享片段，空态之前渲染。路由、视图、鉴权、CSRF、数据库权限和详情模板均无改动。独立会话查阅安装版 Django 5.2.19 确认 `force_login`、停用用户的会话恢复和跳转行为与测试设计一致。测试从渲染 HTML 取 href 走同一客户端，而非真实 Chrome 点击。本次独立评审无实际 Django 执行、数据库访问或源码写入。

## 2026-11-26 15:55 实际隔离验证与服务重启

团队于 15:55:47～15:55:52（+08:00）在普通 PowerShell 执行，汇总自报操作者为 `w`。当前源码反向预检匹配已独立评审的候选，四文件 SHA-256 与运行前后清单逐条相同。原 Python 3.13.17 退出 0。PostgreSQL 17.12、`lab_booking_test@127.0.0.1:5433/test_lab_booking` 运行 4/4 通过、无跳过，耗时 0.185 秒，退出 0。测试前后均为 10 张表、17 条迁移、0 个账号、0 条会话。正常 stderr 包装中的 `RemoteException` 不构成失败，原始记录保留。 [回归原始输出](epic-1-create-navigation-run-20261126-155547-825/raw.txt) · [运行汇总](epic-1-create-navigation-run-20261126-155547-825/run-summary.txt) · [前散列](epic-1-create-navigation-run-20261126-155547-825/before.sha256) · [后散列](epic-1-create-navigation-run-20261126-155547-825/after.sha256)

| 项目 | 已核对的结果 |
| --- | --- |
| 启用管理员 | 身份页、非空目录各有一个正确的新增链接，从渲染的 href 发 GET 均进入原新增表单，CSRF 隐藏字段仍在。 |
| 空目录 | 「暂无设备」和管理员新增链接同时出现，跟随链接 200，无设备新增。 |
| 学生与教师 | 保留查看目录与返回身份导航，无新增链接，直达新增仍为 403。带 Django staff／superuser 标记的教师同样无业务权限。 |
| 匿名及停用管理员 | 身份页、目录及直达新增均 302 进入登录页，保留原 next，不泄露新增入口。 |

新服务启动器 PID 41208、8001 监听 PID 18648，与脚本汇总和本轮只读进程查询相符。旧 39000／5364 已退出，8000 仍由 1964 监听。启动日志显示 Django 系统检查无问题。自动运行验证只向新服务发两个无会话 GET。登录页 200，匿名新增 302 至 `/login/?next=/equipment/new/`。使用新运行密钥，需要重新登录。 [服务冒烟原始输出](epic-1-create-navigation-run-20261126-155547-825/runtime-smoke.txt)

**真实体验范围。** 新服务的后续访问日志另见登录、身份页、目录请求及两次新增表单 GET 200。15:55～15:56 的脱敏摘录仅保留时间、方法、路径和状态，未出现新增表单 POST。它不包含个人、角色映射或点击来源，不能将两次 200 归给特定组员或入口。隔离测试证明两个入口的链接行为，不冒充额外的真人 Chrome 逐角色验收。 [运行访问脱敏摘录](epic-1-create-navigation-run-20261126-155547-825/runtime-access-redacted.txt)

**结论。** 负责人在回执会话批准验证全部通过后收尾和同步，本轮证据满足条件，无新增正式 AC 回归。Story 1.1～1.4 及 Epic 1 保持 `done`，Story 2.1 保持 `backlog`。本轮仅核验既有输出，没有复跑、重新授权或修改正式业务数据。

## 普通 PowerShell 应用、隔离验证和安全重启（历史命令，勿重放）

有两条独立证据须保留。第一条为隔离库，第二条为通过后服务重启。使用当前项目原 `.venv` 和 Python 3.13.17。如果已应用补丁，不重复执行 `git apply`，直接使用验证脚本。凭据路径不同可给脚本传受保护的绝对 `-Passfile`，不要把文件或值交回。

```powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-Location -LiteralPath 'F:\softwork\SE-Management\bmad-lab-booking-system'
    $artifacts = '.\_bmad-output\implementation-artifacts'
    $patch = Join-Path $artifacts 'epic-1-create-navigation.patch'
    git apply --check -- $patch
    if ($LASTEXITCODE -ne 0) { throw 'Patch preflight failed.' }
    git apply -- $patch
    if ($LASTEXITCODE -ne 0) { throw 'Patch application failed.' }
    & (Join-Path $artifacts 'verify-epic-1-create-navigation.ps1') -ExecutedBy (Read-Host '实际操作者姓名') -Restart8001
}
```

[验证脚本](verify-epic-1-create-navigation.ps1) 只在 `lab_booking_test@127.0.0.1:5433/test_lab_booking` 运行四项 Django 回归，依赖既有防越界及回滚 runner。四项全过且前后散列相同后，才可重启 8001。当前只读观察到旧服务 PID 5364、启动器 39000，与 D-035 证据匹配。普通 PowerShell 中再次核对证据散列、路径、创建时间、命令行和父子关系，再停止这组已验证的旧进程。身份不明不停止，8000 不处理。以原项目 runtime 启动后仅匿名 GET 探测登录页及新增登录限制，脚本不登录、不 POST，不执行迁移或 GRANT。如未保留原运行密钥，重启后需要重新登录。

完成后给团队本机地址 `http://127.0.0.1:8001/login/`。请保留脚本打印的证据目录及其中 `raw.txt`、`run-summary.txt`、前后散列、实际生成的 `runtime-smoke.txt`。团队共同体验可登录后实际点击新增链接，只查看表单，不提交新设备。没有回执前，不声称新版本已运行。

## 状态与课程追溯

第 26 页核对 FR-016／002、现有 ADR／PC 和接受标准，未扩 PRD。第 27 页保留已验收 Story 与 Epic 1 的 `done`，本改进另行验证及独立评审。第 33 页保留补丁、验证入口、静态和实际运行证据。第 34 页实验 A 条件和数据不变。第 36 页在 D-037 登记真实团队反馈和负责人决定，不代填三位组员个人意见。未开始 Story 2.1。

本次收尾前只读核对，本地此前提交 `20fb2a8bd506b1a28911fe0ae2c46db904e55024` 尚未推送，GitHub `main` 当时仍为 `e200fee335536941e0705c112aefbf6751b244c3`。本次导航提交基于此前本地提交，远程同步以实际 push 和 SHA 回读为准。旧运行服务在关闭前对原 Story 1.4 的 `server-stderr.txt` 有追加，保留在工作区，不覆盖或混入本改进提交。
