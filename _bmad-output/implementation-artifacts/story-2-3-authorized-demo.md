# Story 2.3 有限业务写入的正式验证执行单

**2026-11-27 负责人授权。** 本轮仅允许学生现有预约 #1 由本人列表触发 FR-018，以及教师经正常 2.1 表单最多新增一条可保留的演示预约；教师已有合适记录则复用。其他正式业务数据保持不变。不迁移、不 GRANT、不删除。有效 ACL 已在原批次两次确认，沿用其后置回执，不运行 Acl 或 Recover。Story 2.3 仍 `review`。 [先前只读阻塞](story-2-3-formal-sample-hold.md) · [独立复验](story-2-3-independent-recheck.md) · [决策 D-047](../../decision-log.md#d-047-2026-11-27-负责人处置-story-23-独立评审)

**本批已有部分实跑，不重放。** 实际结果见 `smoke-20261127-153153-150-bcfae1cb/chrome-receipt.md`。下列命令保留为原步骤追溯，不是对旧批次的重跑指令。

**后置已实际执行并失败。** `finish-20261127-160523-638-de559216` 保留原始错误及独立快照。教师计划新增 1 条，实际 0 条，请求日志无预约 POST。原验收拒绝正确；学生 #1 的失效、一次系统历史和重复读零写可独立复用。需要当前库状态时，使用取证单中的实际命令调用 [只读恢复](recover-story-2-3-readonly.py)，不重新调用 Finish、不重新授权。仅补教师及缺少的权限分支，原窗口和时段均不再用。Story 保持 `review`。

**16:17 已只读恢复。** `recovery-readonly-20261127-161757-129445-f93c0b3c` 确认授权范围内没有新数据变化，教师仍无预约，列级 ACL 精确。后续用 [教师独立补证入口](story23_teacher_followup.py) 的 `Serve`、`Chrome`、`Finish`，使用原 `.venv` 和固定 8003，绑定旧学生证据并禁止学生场景，不执行下方历史指令。教师 `/equipment/` 被旧验证入口白名单拦截，直接用新预检给的 `/equipment/1/reserve/`。新入口单独保留前置、实际日志及后置结果，机器通过后仅待真实页面验收与最终收口。

**最新恢复口径：不再提交预约。** 16:37 教师补证批次已发出一次预约 POST，守卫因时段不符在视图前返回 403，未放行写入，随后中止。只用 [零预约 POST 恢复入口](story23_teacher_readonly_resume.py)，不再运行上述教师补证入口的 Serve，也不删除原保护标记。恢复保留原学生证据与匿名 302，仅补缺失权限对照和可安全复用的教师本人记录。实际结果来源为新目录，状态仍为 `review`。

**16:51 零预约 POST 补证已实际完成机器核验。** `teacher-recovery-20261127-163714-f93c0b3c/post-8a49872cb2be` 的五项断言通过，正式前后预约／历史／设备／非会话账号散列一致，四列授权精确，W1 技术条件已满足。教师空列表 200、异主与不存在同形 404、管理员无入口且直访 403 均有实际证据，沿用原匿名 302 与学生 #1。教师没有可复用正式预约，本人详情及 201 不作现场通过记录。正式功能 AC 可引用既有独立隔离实测，不需重跑。现场缺口的处置和最终验收由团队据实确认，当前不启动新验证窗口、不标 `done`。

**D-048 最终验收已生效。** 上面均为历史执行记录，不再执行本文历史命令。负责人确认实际权限体验、接受教师本人详情现场未执行，以独立实测支持功能验收。W1 已关闭，Story 2.3 为 `done`。 [最终验收](story-2-3-final-acceptance.md) · [原始证据索引](story-2-3-formal-runtime-evidence/README.md)

## 工具行为与退出条件

- `-AuthorizedDemo` 只接受已有 ACL 根批次和受保护的原账号清单。自动按项目预置规则选每角色唯一用户名，实际数据库复核角色、启用、设备及全部相关本人和目标设备候选。检查 #1 归属；会触发其他待审变化则停。若 #1 已合法失效且有唯一正确系统历史，只复用，不再写。若教师已有安全可打开的预约，阻止新建。
- 教师无记录时使用既有演示设备，必须仍可用且设备待审范围无其他风险。依据正式冲突、北京时间同日和整点规则选一小时未来区间，开始至少距预检一小时。终端和锁定的 `sample-before.json` 都会给出**实际设备、路径、开始和结束**。Chrome 体验有 25 分钟窗口，额外防迟到边界。与团队协调该窗口不要通过旧服务改变样本。
- 8003 专用验证进程仍使用原 .venv、Python 3.13.17、runtime 模式和原 Django 视图。验证工具只在该进程安装局部门禁，先完成原 CSRF，再允许对应账号、路由、精确业务 SQL 绑定和一次教师提交。它不会直接代写、改产品源码或替正常业务逻辑成功。不会影响 8000/8001。学生列表两次成功及独立状态/历史回读一致之前，不开放教师提交。由一次性文件先记录放行意图；4xx/5xx、结果不明、其他候选、时间或权限漂移时保留证据，不能盲目点击重试。常规登录会话和 `last_login` 属技术活动，和业务变化分列。
- 后置由独立正式库只读连接查询原始业务数据，核验历史不可改、预约 #1 仅状态变更和一次正确系统历史、教师仅预定申请人/设备/时段的一个新增或零新增复用，逐行摘要核对其他已有预约、设备、历史和非登录账号字段。学生首次和再次列表的两次独立读回、教师真实 201 或复用、真实列表/详情/返回及管理员/归属对照须出现在 HTTP 回执。先前快照的 #1 已不算有效占用，所以验收为失效后无占用，不虚称一次可观测的 1→0。
- PowerShell 语法、三阶段模拟、原始 ORM 语句形态、其他记录/重复历史的负对照、教师复用及动态安全区间均离线核验。不是本轮正式实跑。原业务运行输入与独立复验 77 项保持相同。所有失败及恢复回执原样保留。

## 终端 A · 只读再核对，随后启动受控 8003

在普通 Windows PowerShell 复制本段。若报样本或权限漂移，不进行浏览器操作，不切换旧服务。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$parent = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4'
$manifest = Join-Path $env:LOCALAPPDATA 'LabBooking\Protected\accounts.json'
& $tool -Phase Serve -RunDirectory $parent -SmokeName 'smoke-20261127-153153-150-bcfae1cb' -AccountsManifest $manifest -AuthorizedDemo
```

打开后不要输入新的手工样本或以密码作为参数；仅在 Chrome 登录表单使用现有获准账号。脚本给出实际时间，未启动就不要进入下一步。

## 终端 B · 新 Chrome 配置和当场回执

A 启动后，另开普通 PowerShell 复制：

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$smoke = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4\smoke-20261127-153153-150-bcfae1cb'
& $tool -Phase Chrome -RunDirectory $smoke
```

固定 `http://127.0.0.1:8003`，不混用同主机其他端口。三套 Chrome 独立配置，各自 GET 当前登录表单，Network 可启用 Preserve log，只保存脱敏的单次请求反馈。

1. **学生先做。** 在学生窗口登录，身份页点击「我的预约」。从列表打开 #1 详情，记录「已失效」、设备当前状态和实际起止。点击「返回我的预约」构成第二次列表读取。验证工具读回唯一系统历史，保留两次证据，不从详情或其他入口触发首次失效。
2. **教师后做。** 登录并看身份页。若控制台显示 `reuse`，不打开提交表单，直接用现有预约。若显示 `once only`，从教师自己的新窗口打开终端 B 打印的正常表单地址，输入终端给出的两个**北京时间整点值**，核对设备，仅点击一次提交。记录实际 201，再通过成功页或身份页进入「我的预约」、打开本人详情、返回列表。若 POST 不是 201，停止，保留响应和日志，不重提交。
3. **权限对照。** 管理员窗口登录，确认身份页无入口，然后直访 `http://127.0.0.1:8003/reservations/` 得正常拒绝。在教师窗口分别 GET `http://127.0.0.1:8003/reservations/1/result/` 和 `http://127.0.0.1:8003/reservations/4611686018427387904/result/`，核对异主和缺失同形 404。
4. 请求证据从本次日志自动回填。只把已有的真实页面观察与团队结论引用到 `$smoke\chrome-receipt.md`，不重复录入设备、预约 ID、时间、URL 或状态码，不写密码、Cookie、CSRF 或未脱敏 HAR。正式拒绝／取消原因无获准样本则注明并引用隔离证据，不新造样本。

离线整理命令只读已有输入、仅更新 `chrome-receipt.md` 自动区。不会运行下面的 `Finish`，也不是正式验收结果。

```powershell
python -B '.\_bmad-output\implementation-artifacts\fill-story-2-3-chrome-receipt.py' $smoke
```

## 终端 B · 隔离回读和结束

完成后关闭本次 Chrome，在 A 按 Ctrl+C 只停这一组 8003。回到同一 B 复制：

```powershell
& $tool -Phase Finish -RunDirectory $smoke
```

新 Finish 目录会有 `sample-after.json` 或无法验证时的 `sample-after-unverified.json`、浏览器请求佐证及权限后置回执。成功标记 `STORY23_FORMAL_POSTCHECK_OK` 只代表独立差异核验，仍须结合实际页面观察和人工审阅。若中途失败或 503，只做这个独立读回并保存失败状态，不重放，不补造结果。按实际样本最终决定 W1 和验收意见，不自动标 done。

第 25、26、27、33、34、36 页继续走已记录的课程证据链。原 Sprint 8/5、实验 A、D-047 和中央延期台账保持。未跑 113/15/NFR-001，不改 PRD、Architecture 或业务代码，不提前开 2.5，不提交推送。
