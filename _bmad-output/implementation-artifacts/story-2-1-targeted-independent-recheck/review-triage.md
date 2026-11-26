# Story 2.1 · 针对性复审逐条裁决

四个独立视角均已返回，原文转录件 [reviewer-raw.md](reviewer-raw.md)。首批为 Blind、Edge、Verification Gap，Acceptance 首次启动受四并发槽限制，前一层结束后同会话补启动。未用旧评审替代任何层。以下 18 条先逐条裁决，再按根因合并。Severity 衡量的是探针或脚本缺陷，未发现正式业务路径已有越权、错收尾或冲突结果。

| # | 视角 | 位置与主张 | 裁决 | 核实与去向 |
| --- | --- | --- | --- | --- |
| 01 | Blind | verify_reservation_transactions.py:849–855 本人正例只断 200/状态，首读和重读未分别拍快照 | low | 真实归档两次均展示目标 134，SQL 首次更新和插入、重复无 DML。但探针可漏检错误页面或首读／重读间的变化。R01。 |
| 02 | Blind | verify_reservation_transactions.py:644–651 I7 搜索锁后的所有 SQL，且无固定参数绑定验证 | medium | 宽松谓词可被时钟后到期查询满足，占位符不证明绑定相同 ID。现有 raw 的固定读在时钟前，服务生成 pk/本人/设备固定查询。R02。 |
| 03 | Blind | verify_reservation_transactions.py:653–665 I7 末态对设备及未收尾候选字段断言不足 | low | 实际快照的设备、终态记录、候选关键字段保留，原目标只变更状态。探针恒等检查仅覆跨时同侧快照，未断言这些不应变化的字段。R03。 |
| 04 | Blind | _chrome_probe.py:97–115 URL/status 未绑定方法和 document loader | low | 只采 URL/status 属实，然而真实日志恰有五个导航响应，400 专有错误 DOM、201 专有确认 DOM、普通提交按钮和事务快照相互佐证。同 URL 响应错配不太可能，加入全套 CDP 相关性成本高，驳回。 |
| 05 | Blind | verify-story-2-1-remediation.ps1:150–156,205–223 独立交接强制 NFR 和故障全部实跑 | false | 正式交接写的是可带可选开关，并未强制。用户明确批准同版本历史复用。独立入口单独标注新跑与复用。驳回。 |
| 06 | Blind | verify-story-2-1-remediation.ps1:129–141 历史读取只针对此 JSONL 校验散列、分母和清理 | medium | 当前启动器将工作树比对早期清单及 DB 比对约定摘要，但没有从所复用归档原始 source/baseline receipts 建立本组对应关系。独立 auditor 已补这一次的来源比对，旧启动器本身仍有缺口。R04。 |
| 07 | Blind | verify-story-2-1-remediation.ps1:224–241 最终检查抛错不进 failure.txt 或覆盖首错 | medium | finally 的异常确可越过前置 catch。可能缺失失败原因文件或控制台显示后置错误，非错误地报告通过。R05。 |
| 08 | Blind | verify-story-2-1-remediation.ps1:146 一脚本锁不能协调所有测试入口 | low | 原脚本不取新 lease，同靶数据库的赛事可重叠污染基线，比对会报失败。共享 lease 需另改多入口，旧入口协调问题已存在。继续限定不并跑。RD01 延期，独立于原 D01。 |
| 09 | Edge | verify_reservation_transactions.py:643–652 失效查询可冒充固定候选重读 | medium | 失效 SELECT 也符合固定 pk/申请人/设备谓词；通用 check_order 不要求该读投影及绑定。现有 raw 可直接看到锁后取时前真实重读。R02。 |
| 10 | Edge | verify_reservation_transactions.py:838–846 P02 无禁止被回滚 UPDATE/DELETE 断言 | medium | 捕获业务 SQL 却只以 INSERT 尝试计数；回滚 DML 与无写入会有相同终态。真实两条拒绝记录都是一条本人谓词 SELECT、零业务 DML。R06。 |
| 11 | Edge | _chrome_probe.py:151–154 DevTools 端口就绪但初始 page 尚未出现 | maybe-false | 单次 list 确无重试，涉及此 Chrome 启动顺序，未观察到空 target 启动。最坏当前只折损单次测试启动，不改变结果，保留复现条件但按低影响驳回。 |
| 12 | Edge | _chrome_probe.py:88–116 只有 socket inactivity 超时，持续事件可延长 CDP 调用 | maybe-false | 分析上持续无相关 ID 的事件能延时，真实隔离页面的有限 CDP 操作未观察到这种持续流，不认定当前存在挂死；若有含持续流的 Chrome 失败日志再判断。低影响嫌疑驳回。 |
| 13 | Edge | verify-story-2-1-remediation.ps1:224–242 最终清理错误覆盖首错 | medium | 与 #07 相同 finally 根因，原始阶段、摘要与退出码不足以在双错时分别定位。R05。 |
| 14 | Gap | verify_reservation_transactions.py:292,822–845 角色标签与 404 的实际鉴权主体未关联 | medium | 采纳预核验结果。真实冻结代码用独立 CookieJar 给活跃学生乙登录，恢复映射后仍用 peer opener，归档数值 738/735 不同；但探针把 requester_id 和 role 从夹具与调用者写入。换成 teacher opener 仍能计入 13。R07，P02 首要证据补强，非当前权限实现漏洞。 |
| 15 | Gap 其他 | verify-story-2-1-remediation.ps1:129,150,205,236 新跑故障/NFR 仍先依赖对应历史 JSONL | low | fresh 分支进入前和退出时都读旧三组；原文件损坏时无法用此开关再生同组。当前归档已完整可用。R08。 |
| 16 | Acceptance | verify_reservation_transactions.py:643–651 AC-10、PC-005、T-01 未锁定固定重读与 t_decision 的顺序 | medium | 采纳顺序因果，同根 #02/#09。独立离线核对了真实顺序，原断言不具备这项保护。R02。 |
| 17 | Acceptance | verify_reservation_transactions.py:640–642 AC-10 仅查原目标出现在响应 | low | 聚焦的数据层状态不替代 UI 最小投影断言。实际三个 200 均只渲染一个 dl 的四个字段，没有新增候选号；探针未独立冻结形状。R09。 |
| 18 | Acceptance | verify_reservation_transactions.py:268,836–846 AC-10、PC-011、T-03 未断言异主和不存在 404 的 Location | low | 两条真实 raw 的 Location 都是 null，未发现泄露。已记录但未断言，补一个明确的无 Location 检查。R10。 |

## 分组与处置提案

- R01（低）本人正例各步校验目标和数据快照（#01）。
- R02（中）I7 验证固定候选完整投影及绑定参数，位置在行锁和唯一取时之间（#02、#09、#16）。
- R03（低）I7 按预期字段验证原目标仅状态改变、设备及其他候选不变（#03）。
- R04（中）使原启动器的复用证据可独立验证对应历史版本及前后摘要（#06）。本轮复用已由独立审计补证，不重复压测。
- R05（中）分别保存主要验证与最后校验／清理失败（#07、#13）。
- R06（中）P02 拒绝侧断言跟踪的预约／审计业务 SQL 无任何 DML（#10）。
- R07（中）P02 仅记录请求实际鉴权主体的测试夹具 ID、角色、启用状态，并及于 404 与对照，不留凭据（#14）。
- R08（低）fresh 可选路径只依赖仍实际复用的历史组（#15）。
- R09（低）I7 响应仅一个目标的最小投影，不包含并发新增候选（#17）。
- R10（低）P02 明确断言两条 404 没有 Location（#18）。
- RD01（低，延期）共享隔离测试库的历史多入口 lease 协调，后续维护统一验证入口时处理。当前不要并跑不同脚本（#08）。
- 驳回 #04、#05、#11、#12。每条理由见表。

0 项需作设计裁决，10 项 Patch（5 中、5 低），1 项 Defer，4 项 Rejected。没有 High。R01～R10 是本次新增建议，不替代原 P04～P18、D01 或首轮驳回。记录开放证据项不等于授权修复、批准生产发布或认可正式验收。

