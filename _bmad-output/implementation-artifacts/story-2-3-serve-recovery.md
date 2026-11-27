# Story 2.3 Serve 已有证据冲突与续跑交接

> 最新执行：已确认当前样本存在 FR-018 写入风险。先按[样本阻塞与只读检查](story-2-3-formal-sample-hold.md)执行，不直接重放以下历史命令。

**原批次 ACL 已实际精确读回，无需再次执行 Recover、Acl 或 GRANT。** 本轮只修复正式验证入口。当前 8003 尚无监听，Story 保持 `review`，正式浏览器核验待执行。 [完整原始文件指纹](story-2-3-formal-20261127-120858-648-0dcaa5b4-serve-original/archive.sha256) · [之前的授权故障](story-2-3-formal-recovery.md)

## 根因与隔离措施

- 14:50:41 和 14:53:54 的两次实际 Recover 均由 PostgreSQL 17.12 运行角色 `lab_booking_app` 在 `127.0.0.1:5433/lab_booking` 只读复核。有效和显式 ACL 精确相同，仅 `id` 加获批四列可读；无表级 SELECT 或转授。迁移和现有权限一致，76 项矩阵中允许项为 30。 [第二次运行角色回执](story-2-3-formal-20261127-120858-648-0dcaa5b4-serve-original/recover-20261127145353762-app.stdout.txt) · [第二次完整目录矩阵](story-2-3-formal-20261127-120858-648-0dcaa5b4-serve-original/recover-20261127145353762.json)
- 14:53:40，首次 Serve 的真实 `sample-before-catalog` 退出 1，stderr 为「Authorized student account is absent, inactive or has a different role」。这只能证明所输入账号未通过存在／启用／角色校验，不推断具体错因或账号值。该阶段只留空 stdout 和原始 stderr，没有 `sample-before.json`、`launch.txt`、`listener.txt` 或 server 日志，不能当作完成的前置快照。14:54:21 的第二次 Serve 尚未重新查询，就被原目录内同名 stdout/stderr 的防覆盖断言拒绝。更早两次 Chrome 因没有 8003 监听而退出。 [原始阶段](story-2-3-formal-20261127-120858-648-0dcaa5b4-serve-original/stages.txt) · [最初账号校验错误](story-2-3-formal-20261127-120858-648-0dcaa5b4-serve-original/sample-before-catalog.stderr.txt)
- 新 [PowerShell 入口](run-story-2-3-formal.ps1) 为每次 Serve 先建独立 smoke 子目录，只绑定父批次必要 ACL 回执和运行源码清单，验证 SHA-256，不从旧批次复制候选或日志。每次仍新做全部师生待审范围和截止时间检查，校验新的前置快照；不放宽防覆盖断言。Chrome 和 Finish 分别在同一 smoke 下的新子目录落证。Chrome 验证仅 8003 loopback、实际 PID/时间、原运行参数和本次专属进程标识，不能把别次服务当成当前页。Finish 只用该次带散列前置快照、已完成的三窗口启动回执和实际只读后置；依然要求先停本次 8003。原 8000/8001 保留。真实页面验收仍以每请求已填写的 Chrome 回执为准。
- 离线 PowerShell 演练覆盖 Serve 前置失败后新尝试、Chrome 重试隔离、Finish 出错后再做同基线读回、拒绝重复已存在路径和拒绝错误进程标识。实际验证脚本分支的进程、Chrome 和数据库调用均替换为模拟，未连接正式库或启动应用。脚本语法通过，77/77 运行源码仍匹配独立复验。原父目录 32 份原始文件逐字节保留。 [离线检查摘要](story-2-3-serve-recovery-offline.txt)

## 终端 A · 新建并运行本次 smoke

在普通 Windows PowerShell 完整复制。只输入三类账号在登录表单使用的真实**用户名**，不是「学生」等角色标签、显示名或密码。如果仍不匹配，可检查所用预置账号身份后在父目录用不带 `-SmokeName` 的 Serve 创建另一次全新尝试；原输出不删除。正式数据不可用时如实记录，不新增演示数据。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$parent = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4'
& $tool -Phase Serve -RunDirectory $parent -SmokeName 'smoke-20261127-145741-081-70fac945'
```

## 终端 B · 验证实际监听后打开三套隔离 Chrome

等待终端 A 完成账号、ACL、新候选和 FR-018 安全核对并启动。以下命令指向与 A 相同的新子目录，不用旧父目录。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$smoke = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4\smoke-20261127-145741-081-70fac945'
& $tool -Phase Chrome -RunDirectory $smoke
```

同一 origin 固定 `http://127.0.0.1:8003`，在各新配置从当前服务重新 GET 登录表单。启用 Network / Preserve log，只留脱敏证据。学生和教师在安全截止前用对应账号依次点击身份 → 我的预约 → 已有本人详情 → 返回；记录两种状态、设备、预约 ID、北京时间、URL 和 HTTP。管理员无入口及直接访问拒绝、异主／不存在同形响应分行记录。遇 403、503、账号误用、样本不安全或时间截止即停，不盲目重放、更不提交新预约。把事实填到 `$smoke\chrome-receipt.md`；无正式原因样本就引用隔离验证，不造历史。

操作完成关闭本次 Chrome，只在 A 用 Ctrl+C 停当前服务。终端 B 可完整复制后置检查命令：

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$smoke = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4\smoke-20261127-145741-081-70fac945'
& $tool -Phase Finish -RunDirectory $smoke
```

该阶段核对当前权限、相同应用源与该次候选前后的预约、设备、占用和历史。只有实际回执才用于最终验收。正式过程仍按课程第 25、26、27、33、34、36 页的现有团队依据，D-047、中央延期台账、原 Sprint 8/5、实验 A 与三人共同执行不变。此次未运行 113/15/NFR-001，未修改业务、授权 SQL、正式库或 Story 2.5，未标 done，未提交或推送。
