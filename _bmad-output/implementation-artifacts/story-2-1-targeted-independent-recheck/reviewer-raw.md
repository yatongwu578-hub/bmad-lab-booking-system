# Story 2.1 · 四层复审回报（原始回报转录）

均基于同一个冻结五文件差异。以下保留原文的结论和定位。文件路径未改，Markdown 换行作格式整理。

## Blind Hunter

- Finding floor `N = min(floor(sqrt(48.765) + 1), 10) = 7` for the 48,765-byte diff.
- `verify_reservation_transactions.py:849–855` — The P02 owner control accepts any `200` containing `已失效`, then takes its only post-read snapshot after both requests. It could pass if the response showed the wrong reservation or the repeat changed unrelated state. Assert the rendered ID and fields and take a snapshot after each read.
- `verify_reservation_transactions.py:644–651` — The I7 fixed-candidate reread assertion searches every statement after the lock, including statements after the decision clock. It only checks SQL placeholders, so bound values for the wrong reservation, owner, or equipment would also match. Check the fixture IDs and require the reread to occur between the device lock and the decision sample.
- `verify_reservation_transactions.py:653–665` — I7 checks final statuses and selected applicant IDs, but it does not check that the device and untouched reservations retain their other fields. A read could rewrite a candidate’s times while leaving it pending and still pass. Compare all fields against the original rows and inserted fixtures, allowing only the target status change and its one history row.
- `_chrome_probe.py:97–115` — Browser evidence records only URL and status, and readiness accepts any prior matching response for that URL. The form GET and both submissions share one URL, so the receipt does not prove which request method and document produced each result. Pair the main-frame request method, response, and loaded document by navigation ID.
- `verify-story-2-1-remediation.ps1:150–156,205–223` — The default run can emit the same success marker while reusing historical fault and NFR results. The independent handoff calls for fresh runs of both. Give independent verification an explicit mode that requires fresh fault and NFR evidence and identifies that mode in the receipt.
- `verify-story-2-1-remediation.ps1:129–141` — Historical reuse authenticates the JSONL bytes and checks record counts, but it never verifies the archived run’s source manifests or baseline receipts. That proves the logs have not changed, not that they came from equivalent code and conditions. Tie reuse to the archived source and database receipts and record the equivalence checks.
- `verify-story-2-1-remediation.ps1:224–241` — A failure during the final database or source checks bypasses `failure.txt`. If a test already failed, an exception in `finally` can also mask the primary error at the console. Record cleanup and verification failures separately while retaining the original failure.
- `verify-story-2-1-remediation.ps1:146` — The new lock only serializes this script. The existing independent runner uses a different lock and the original verification runner does not take this one, even though they share the same isolated database. Use a lease scoped to the database target and shared by the entry points so overlapping runs cannot invalidate each other’s snapshots.

## Edge Case Hunter

| Location | Trigger condition | Guard snippet | Potential consequence |
| --- | --- | --- | --- |
| reservations/management/commands/verify_reservation_transactions.py:643-652 | The fixed-candidate reread is missing but the later expiry query uses the fixed predicates | Require the fixed result projection between the equipment lock and the decision clock, excluding expiry queries. | I7 can pass without proving the required lock-time reread. |
| reservations/management/commands/verify_reservation_transactions.py:838-846 | A denied request issues reservation or audit UPDATE/DELETE statements that are rolled back | Assert neither denied request traced INSERT, UPDATE, or DELETE against reservations or audit history. | The probe can certify no writes despite attempted writes during the denied request. |
| reservations/management/commands/_chrome_probe.py:151-154 | Chrome opens its DevTools port before the initial page target appears | Poll target discovery for the initial about:blank page until a bounded startup deadline. | An otherwise valid browser run aborts during startup. |
| reservations/management/commands/_chrome_probe.py:88-116 | The awaited command never replies while Chrome continues sending unrelated events | Enforce an absolute command deadline independently of socket inactivity and check it while consuming events. | The browser probe can hang past its polling timeout and delay fixture cleanup. |
| _bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:224-242 | A final baseline or source assertion throws during cleanup | Record cleanup failures separately and preserve any original stage exception before propagating either failure. | A cleanup failure can replace the original error or leave no failure.txt. |

## Verification Gap

### P02 can pass without a same-role foreign request

- **Changed surface:** The new P02 probe verifies that an active student cannot read another active student’s expired-but-still-pending reservation. `reservations/management/commands/verify_reservation_transactions.py:822`
- **Impacted consumer or site:** The reservation result route at `reservations/views.py:64` and the remediation gate that counts the peer request as the thirteenth denial at `_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:189`.
- **Existing test evidence:** The command checks the fixture users’ roles and IDs, the two 404 bodies, database fingerprints, and the absence of business work. Its `prepare()` helper records `role` from a caller-supplied argument, not from the authenticated request. The independent auditor likewise compares fixture IDs and supplied role labels without observing the request principal. The Django denial test uses a teacher for its foreign read. `reservations/management/commands/verify_reservation_transactions.py:292`, `reservations/management/commands/verify_reservation_transactions.py:823`, `_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/audit-targeted-run.py:140`, `reservations/tests.py:308`
- **Missing verification:** Assert from the request that produced the foreign 404 that the authenticated principal is the active peer student.
- **Demonstration:** A copy-forward mistake could pass the existing `teacher` opener to `peer_foreign` while leaving `role=Role.STUDENT` and the peer’s missing-record request intact. The teacher already returns the same 404 body without changing state. The command, the launcher, and the independent auditor would still count the case as same-role evidence.
- **Consequence:** The remediation could report thirteen verified denials without exercising the new student-to-student denial.
- **Disposition:** `patch` — capture only the authenticated fixture user ID and role in the server-side request trace, then assert both against the peer fixture in the P02 probe and raw-evidence audit.

### Other findings

- The fresh fault and concurrency rerun still requires the historical evidence it replaces. With `-RecheckConcurrencyAndFaults`, `Read-Historical` checks both old files before any fresh probes run and checks them again at cleanup. A missing or hash-mismatched historical fault or NFR file therefore blocks regeneration even though those files are omitted from the reuse summary. `_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:129`, `_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:150`, `_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:205`, `_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:236`

## Acceptance Auditor

- **P03 的 I7 未锁定固定候选重读与取时的先后顺序。** 违反 AC-10、PC-005 和 T-01/I7 的取证要求。`verify_reservation_transactions.py:643–651` 在 `FOR UPDATE` 之后的全部 SQL 中寻找固定候选重读，而 `check_order()` 在第 346–359 行只要求取时前有任意读取设备或预约状态的语句。若实现先读取其他状态、再取时、最后才重读固定候选，两项断言仍可通过。
- **P03 的 I7 未验证 GET 只返回原授权目标。** 违反 AC-10 和 P03 的响应范围取证要求。`verify_reservation_transactions.py:640–642` 只检查正文包含原目标编号和“已失效”，第 652–659 行检查的是数据库末态。若 GET 保留原目标，同时在响应中额外展示等锁期间新增的候选，探针仍可通过。
- **P02 未比较异主与不存在响应的 `Location`。** 违反 AC-10、PC-011 和 T-03 对同角色拒绝不泄露、与不存在响应一致的取证要求。`verify_reservation_transactions.py:268` 已记录 `Location`，但第 836–846 行只比较状态码和正文，也只在正文搜索受限值。若异主 404 通过 `Location` 暴露受限信息，现有断言不会失败。这是取证缺口，未发现实际泄露。

