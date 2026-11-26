# Story 2.1 · 回交原独立 Code Review

BMAD 6.12.4 `bmad-code-review` `full`，沿用原独立评审会话、正式 AC-1～AC-11、D-039 及既有裁决。当前 Story 2.1 已完成集中整改开发自测，实施规格为 `in-review`、Sprint 状态为 `review`。本交接不是独立结果或最终验收。

- **复审范围**：以原独立评审的工作树快照和基线 `e196aba098771a31eb203be4270b460d5e0aab42` 为参照。重点仅 P01 的原生表单步进及真实纠错、P02 同角色异主与甲本人对照、P03 I7 同申请人实际等锁期新增候选；覆盖全部五个增量路径及未跟踪文件。旧阶段 stderr、历史原始日志、锁文件不属于业务差异。无需重放原补丁。
- **可用新证据**：团队普通 PowerShell 的 Django 91/91 零跳过、师生导航 1/1、Chrome 纠错 1/1、未授权 13/13（正对照另列）、真实交错 15/15；均来自 [真实运行](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/stages.txt)、[逐 AC 整改证据](story-2-1-remediation-evidence.md) 和 [原始记录核验摘要](story-2-1-remediation-run-audit.json)。不将这批开发证据冒充独立执行。
- **复用界线**：同路径历史开发实测的 NFR-001 20×10、故障 5/5、北京 18:00 B3/B4 已核验，没有在本轮新跑。请原独立会话按 D-039 完成针对性独立实跑及必要复验，核实调用版本与新增证据。入口 [verify-story-2-1-remediation.ps1](verify-story-2-1-remediation.ps1)，用 `-RecheckConcurrencyAndFaults` 可集中重跑真实完整竞争和故障，标准不降低。北京整点仅当相关证据失配或行为路径实质变化再重测。全部实际运行只用原环境及 `127.0.0.1:5433/test_lab_booking`。
- **保留**：P04～P18 条件性延期、D01 待核实及原三项驳回，不改正式验收标准、Sprint 8/5 或实验 A。正式库权限与迁移仍未获此轮授权。Story 2.2 仍 `backlog`，不自行改 done、commit 或 push。三位组员共同操作与审阅。


## D-040 后的最新复验入口

负责人在针对性独立评审选择 2 并批准 P02/P03 最小取证补强。前面的开发批次及核验仅作为历史证据，不满足新增的实际认证主体与数据库绑定断言。最新只执行 [D-040 单入口](story-2-1-targeted-independent-recheck/run-targeted-recheck.ps1)，见 [处置与回执要求](story-2-1-targeted-independent-recheck/d040-disposition-build-handoff.md)。不先运行旧入口。Story 2.1 当前 `in-progress`，此附注不是新的通过或正式环境验收。



## D-040 新独立回执核验完成

团队普通 Windows PowerShell 独立验证批次 20:52～20:53 实际通过，评审会话另对指针、原始日志、清理、版本及退出码重算核验。新增实际结果和历史复用分别登记，P01～P03 及 R02/R06/R07/R10 建议关闭。Story 2.1 已按条件恢复到 review，不标 done。 [复审收尾](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

