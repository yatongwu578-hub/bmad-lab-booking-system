# Story 1.4 D-035 正式库授权与 Chrome 本机执行

2026-11-26。负责人已关闭 R1、R2、R7、Q-3，并另行批准限定的正式业务库授权及运行验证。Q-1、Q-2 及其它原延期不变，W1 等真实运行证据，不代签关闭。Story 1.4 保持 `review`，此时没有最终验收。 [D-035](../../decision-log.md#d-035-2026-11-26-负责人关闭-story-14-四项发现并批准正式库验证) · [独立复验](story-1-4-targeted-independent-recheck.md#2026-11-26-独立复验结果)

**后续结果，11:46。** 团队已按下述命令完成运行，W1 已取证，正式验收待负责人。下面的恢复命令作为历史保留，不再执行。勿重复 GRANT 或提交同一演示设备的编辑。 [已核对的原始日志与结果](story-1-4-runtime-evidence.md)

## 实际状态与环境

- 初次准备时以已验证的指定解释器和独立临时目录调用 BMAD 6.12.4 正式渲染，指向原不可变 Build 快照；Code Review 完成钩子为空。此次仅是 D-035 运行工具纠错，不重复实施、评审或重放补丁。
- 团队在普通 PowerShell 首次实际执行，日志记录 Python 3.13.17、Node 24.22.1，授权批次在 `django_migrations.app` 与 PL/pgSQL 局部变量 `app` 歧义处以 psql 退出码 3 中止。当时尚未执行 `GRANT`，`ON_ERROR_STOP=1` 和 `--single-transaction` 使该批次回滚。运行验证记录为 `NOT RUN`，无新服务或浏览器证据。保留[原始错误](story-1-4-runtime-run-20261126-105606-102/acl-raw.txt)、[首次汇总](story-1-4-runtime-run-20261126-105606-102/run-summary.txt)及[原输入散列](story-1-4-runtime-run-20261126-105606-102/inputs.sha256)，不覆盖。
- 授权 SQL 仅将迁移表字段限定为 `dm.app` 和 `dm.name`，未改任何安全断言或授权内容。完整授权和应用角色快照未发现其它同类歧义，后者与既有验证入口均未改动。当前沙箱对密码文件元数据仍返回 `Access is denied`，未连接正式库，不能代报当前有效权限。沿用既有隔离证据，未重跑 68 项 Django、10 项探针或 Q-3。
- 工具核对通过：撤销这一处字段限定后，源码 SHA-256 精确匹配首次清单；修复版 SHA-256 为 `77D3E93F9D5C78E155350C8873ABE7CC64975505AFA1A3E34B16BAB243AB5D35`。原始失败目录的三份文件及既有运行入口、快照、Chrome 工具散列未变。PowerShell 语法解析通过，用替身进程离线模拟了两个有效状态及四种停止情形（非零退出、缺 COMMIT、缺标记、重复标记），六例均符合预期。这些不是 PostgreSQL 或 Chrome 的实测结果。

## 2026-11-26 11:20 执行结果与恢复

- 团队普通 PowerShell 在同一次工作中先取得 [11:20 授权前只读快照](story-1-4-runtime-acl-check-20261126-112028-049/acl-raw.txt)，为 `NOT_GRANTED`、退出 0，继承角色为空。随后 [授权原始日志](story-1-4-runtime-run-20261126-112028-249/acl-raw.txt) 有两个阶段的权限矩阵、`D035_ACL_ASSERTIONS_PASSED` 和退出 0。[运行角色独立只读回读](story-1-4-runtime-run-20261126-112028-249/runtime-acl-readback.txt) 也是退出 0。确认已提交，四列以外无新增权限。这个结论对应 11:20 的证据，不代替恢复当刻的核验。
- [Chrome 停止日志](story-1-4-runtime-run-20261126-112028-249/chrome-db-raw.txt)仅有独立 before 快照及原 Node 退出 1。原脚本第 52 行的等值检查在 Chrome 临时目录、启动及任何 HTTP 操作之前。仅类别冲突，旧记录和原计划均为「课程演示」。改用「课程设备 · Story 1.4」，其他三个旧计划值保持不变，依据快照四列都确有变化。恢复时会在浏览器启动前核验原演示数据，拒绝基线变化或任一允许字段相同；正常编辑提交前再读回一次。保留原脚本输入散列及全部原日志。
- [运行汇总](story-1-4-runtime-run-20261126-112028-249/run-summary.txt)记录 8001 的项目启动 PID 39000、监听 PID 5364。Codex 只读看到相同两个 PID、启动时间、项目原虚拟环境及其基础解释器路径；CIM 命令行元数据在沙箱中被拒，未连接正式库、未访问服务、未终止进程。恢复脚本在普通 PowerShell 核对记录、解释器、命令、进程父子关系以及 Git 基线和 53 项独立认证源文件的散列及时间，再决定复用。若 8001 已空闲才启动新服务，若占用者无法证明身份则停止。8000 不处理。
- PowerShell AST、Chrome JavaScript 语法及 53 项原文件散列均通过。以历史快照离线回放核对了四字段变化、拒绝重复值、拒绝基线漂移及指定设备边界。使用真实 PID／时间／路径及模拟 CIM 元数据检查了复用判断、他进程和错命令拒绝。这些不是新的正式库或 Chrome 实测。

## 普通 PowerShell 恢复命令

先用[只读 ACL 核验](check-story-1-4-runtime-acl.ps1)验证当前有效及继承权限，只有 `GRANTED` 才继续。其他结果、部分授权、额外权限及非零退出均停止，不回退到授权命令。使用既有受保护文件，路径不同时可给两条命令传相同的绝对 `-Passfile`，并给运行命令传绝对 `-AccountsJson`，不要交回文件本身。团队在同一轮操作，期间不要另开权限脚本或修改同一演示设备。

```powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-Location -LiteralPath 'F:\softwork\SE-Management\bmad-lab-booking-system'
    $artifacts = '.\_bmad-output\implementation-artifacts'
    $operator = Read-Host '实际操作者姓名'
    $acl = & (Join-Path $artifacts 'check-story-1-4-runtime-acl.ps1') -ExecutedBy $operator
    if ($acl -cne 'GRANTED') { throw '四列有效 UPDATE 未确认。停止，不重新授权。' }
    & (Join-Path $artifacts 'verify-story-1-4-runtime.ps1') -ExecutedBy $operator -RuntimeOnly -ResumeInterruptedRun
}
```

1. [执行入口](verify-story-1-4-runtime.ps1)核对原 Python 3.13.17、Git 基线、53 个已独立复验文件、受保护输入及原运行证据散列。原 [单事务 ACL 批次](story-1-4-runtime-grant.sql)不变并已成功，不在恢复时执行。恢复不修改数据库 ACL 或迁移。
2. [只读回读](story-1-4-runtime-snapshot.sql)由实际应用角色在新只读事务核验有效 ACL、Read Committed 及指定设备。验证 8001 的项目服务身份后优先复用，原日志继续追加，不覆盖。无监听时仅新启 `127.0.0.1:8001 --noreload` 的运行实例。
3. [Chrome 流程](story-1-4-runtime-chrome.mjs)复用已验证 DevTools 协议，独立 Chrome 配置。匿名、学生、教师只对获批演示档案验证 GET／POST 被拒且无设备变化。管理员从原设备详情点击编辑，先验证编号／状态不作为可编辑字段，分别附加一个伪造字段并核对完整请求被拒。每个拒绝都用独立运行角色重新查询确认。然后只提交一次经批准的正常四字段更新，复核同一详情、原主键／编号／状态、其它设备摘要和表记录总数。正常编辑拟写入课程演示标识值，记录前后，不自动恢复或重提。未批准的删除、状态转换、并发、故障注入及额外设备写入都不执行。
4. 保存 ACL 原始输出及退出码、运行角色只读快照、真实 Chrome 与每例数据库回读、启动输出、实际操作者及输入散列。所有账号从原受保护文件读取，不输出凭据、会话标识或 CSRF。若失败，原样保留打印出的 `story-1-4-runtime-run-*` 目录。不要重跑已知／未知是否提交的授权或设备更新。仅在只读确认恰好四列有效 UPDATE、没有额外权限、设备尚未被改动且 8001 可用时，才使用 `-RuntimeOnly` 跳过授权，不终止不明进程。

经验证的服务留在 [登录页](http://127.0.0.1:8001/login/)。成功时 Chrome 最终 JSON 以实际独立读回的主键打印 `detail_url` 和 `edit_url`，编辑入口是管理员设备详情上的「编辑设备基础信息」。目前证据只确认 8001 曾成功启动且仍监听，不宣称正式编辑验证已通过。

## 目录回交与课程追溯

请回交只读检查和续跑脚本实际打印的证据目录名称。保留 `run-summary.txt`、只读 `acl-raw.txt`、`runtime-acl-readback.txt`、`chrome-db-raw.txt`、`inputs.sha256` 及成功时的 `inputs.after.sha256`。复用时留 `service-identity.txt`，新启动时留两份启动日志，失败时保留已有各件。`-RuntimeOnly` 不生成新的写授权日志。届时核对权限矩阵、Chrome 四类身份、各拒绝和正常编辑后的独立读回、监听 PID 及地址。

保留第 26 页 FR／ADR／AC 与运行验证追溯、第 27 页真实 `review` 状态和问题关闭、第 33 页权限与运行原始证据、第 34 页实验 A 不变、第 36 页 D-035 人工决定。三位组员共同操作及审阅，不另派个人任务。没有修改正式需求、架构或业务代码，Story 2.1 仍为 `backlog`，未暂存、提交或推送。
