## Deferred from: code review of spec-2-1-submit-reservation.md (2026-11-26, targeted recheck)

- RD01（低）旧验证入口和整改入口缺少同一隔离库的跨脚本 lease。整改启动器的独占文件锁只保护本入口。多个入口若同时启动，隔离种子或基线可能互相污染，前后摘要应拒绝接纳。当前同一个 `127.0.0.1:5433/test_lab_booking` 不并跑不同入口，后续统一验证入口时完善共享 lease。只影响隔离测试取证，无正式库行为变更，不替代原 D01。 [独立裁决](story-2-1-targeted-independent-recheck/review-triage.md)
