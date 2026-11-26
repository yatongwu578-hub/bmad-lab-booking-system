## Deferred from: code review of spec-2-1-submit-reservation (2026-11-26)

- **D01 终态本人结果读取与同请求内账号撤权竞态（Medium，未核实）。** 当前不加设备写锁的终态查询以已通过认证的主体及预约编号筛选，待审核有实证验证锁后权限重读。尚无旧主体在独立撤权已提交后仍读取新提交终态的实测。用只连隔离库的固定交错锁定认证完成、撤权提交及查询可见性，且不得给终态引入非必要设备锁。如果复现，按 PC-008／FR-002 重新裁决。见 [本轮裁决](story-2-1-independent-verification/review-checkpoint.md)。