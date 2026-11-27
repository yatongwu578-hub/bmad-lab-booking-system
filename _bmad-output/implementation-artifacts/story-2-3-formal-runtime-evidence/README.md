# Story 2.3 正式运行原始证据索引

本目录仅归档本 Story 必需的脱敏、可追溯原始文件。保留原字节与 [归档 SHA-256](archive.sha256)，不改原始回执。保留脱敏账号编号，不纳入凭据、账号清单、Cookie、CSRF 值、浏览器配置、未脱敏 HAR、旧 Story 的运行日志或锁。相对目录名用于仓库索引，原工具回执保留采集时的名字和散列。未集齐的历史现场操作不补造。

| 实际阶段 | 原始文件 |
| --- | --- |
| 原授权、异常及两次精确读回 | [授权执行和故障](../story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/stages.txt) · [已提交](../story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/grant-outcome.txt) · [授权后读回](../story-2-3-formal-20261127-120858-648-0dcaa5b4-serve-original/recover-20261127145353762-app.stdout.txt) |
| 原样本不安全，未启动 | [阶段](../smoke-20261127-145741-081-70fac945-formal-hold-original/stages.txt) · [前置失败](../smoke-20261127-145741-081-70fac945-formal-hold-original/sample-before-catalog.stderr.txt) |
| 学生 #1 正式按需失效与重复读取 | [Chrome 监听](original-smoke/chrome/listener.txt) · [前置快照](original-smoke/sample-before.json) · [实际 HTTP 与独立回读](original-smoke/browser-http.jsonl) · [运行输入](original-smoke/runtime-source.sha256) |
| 原 Finish 失败以及独立只读恢复 | [阶段](original-smoke/finish-failed/stages.txt) · [真实错误](original-smoke/finish-failed/demo-after-catalog.stderr.txt) · [未通过的后置快照](original-smoke/finish-failed/sample-after-unverified.json) · [16:17 独立恢复](recovery-readonly/current-db.json) |
| 教师首次预约 POST 被门禁拒绝，未写入，未重放 | [前置计划](teacher-rejected/before.json) · [真实请求及匿名 302](teacher-rejected/browser-http.jsonl) · [拒绝和中止的响应体指纹](teacher-readonly/source-review.json) |
| 后续零预约 POST，权限对照通过 | [原始 HTTP](teacher-readonly/browser-http.jsonl) · [前置数据库](teacher-readonly/preflight-cd1d08891ee5/current-db.json) · [后置数据库](teacher-readonly/post-8a49872cb2be/current-db.json) · [后置 ACL](teacher-readonly/post-8a49872cb2be/app-acl.stdout.txt) · [五项机器断言](teacher-readonly/post-8a49872cb2be/result.json) · [自动取证单](teacher-readonly/post-8a49872cb2be/chrome-receipt.md) |

教师无可复用正式预约，本人详情与 201 未在正式 Chrome 验证。实际人工体验及对该限制的决定见 [最终验收](../story-2-3-final-acceptance.md) 和 [D-048](../../../decision-log.md#d-048-2026-11-27-负责人最终验收-story-23)。
