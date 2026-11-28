# 实验 A · 实施、度量和证据索引

**D1 截面（正式 done）：2026-11-28T21:10:43.0878369+08:00。C（共同观察截止）尚未到达，本表不代替期末报告。** X 是 Story 2.6（规划支持的 Build），Y 是 Story 2.7（直接实现）。两项取相同业务源码版本 10c193e289753592903549dcd483c65ff3886bb1，分别冻结、独立审查并验收，再按 2.6 → 2.7 集成。 [联合验收](../../_bmad-output/implementation-artifacts/story-2-6-2-7-final-acceptance.md) · [2.6 规格](../../_bmad-output/implementation-artifacts/spec-2-6-approve-pending-reservation.md) · [2.7 规格](../../_bmad-output/implementation-artifacts/spec-2-7-reject-pending-reservation.md) · [D-058～060](../../decision-log.md)

## 按 PPT 29 / 34 的五项记录

| 项目 | X · 2.6 | Y · 2.7 | 口径及证据 |
| --- | --- | --- | --- |
| 平均单 Story 实际对话次数 | 3/1＝3 | 3/1＝3 | 两组实际首次 done 已发生。原开发、独立 R1、针对性独立复核各一；同 ID 续接整改或 Step 05、内部子代理、准备和未开始对话的启动失败不另计。 |
| 首轮 code-review 通过率 | 0/1＝0% | 0/1＝0% | 两份 R1 有变更请求，后续通过不覆盖。 |
| 违反 project-context 规则次数（R1 主值） | 0 项已确认 | 2 项已确认 | Y 命中 PC-004（两处但规则去重）与 PC-005。未确认的假设和仅有测试缺口不计。 |
| 与 ADR 冲突的实现次数（截至 C） |  |  | 期末留空。R1 截面 X 0 / Y 2，Y 分别为授权后业务原因无效绕过时钟/合法失效，及终态先于采样短路。按独立根因去重。 |
| done 后需再修改的 Story 数（截至 C） |  |  | 期末留空。D1 前的改动不能算返工，文本合并触点不能自动算架构偏离。 |

| 组 | 原开发与同会话整改 | 独立 R1 | 针对性独立复核 |
| --- | --- | --- | --- |
| X | 01a22061-d073-7c71-b0eb-08392c7f62fb | 01a220cf-f8a2-7b42-983b-0338d46b6538 | 01a221f5-2eca-7521-80a2-29a42c4a9d5e |
| Y | 01a2204b-af50-7cb0-b880-846f4664cada | 01a2214d-c570-7582-b1ac-3f4d1317bdf6 | 01a221f5-fe11-7122-a630-de067150ed38 |

## 原始证据位置及散列

原件在项目可信本机实验归档 experiment-a-preparation-10c193e。以下仅公开可追溯摘要和 SHA-256。原生会话、凭据、Cookie、令牌、正式详情正文及可识别业务原件不放入公开 Git 历史。测试结果、PC/ADR 原判和不同版本的工具均保留。查询详细原件由负责人按归档名称与散列核对。

| 实际阶段与原件名称 | 标识或 SHA-256 |
| --- | --- |
| X S0 Git 冻结 | a400c77efe4141e2d6bd4638e59b172e0d29f2ac |
| Y S0 Git 冻结 | 502b5ec7390b1c0ae5e617172e4d4b6569038ba7 |
| X 同轮独立 R1 封存结论 r1-conclusion.md | 57B7E883CABAC9758CAA2B5FCF0625B1C1879AD5623363EDBC0460C0D1F38913 |
| Y 独立 R1 r1-original-review.md | C9FEB6BCB57098DB3CAC15A8A1D17A178542988A8503F39CBB5D332989BD5F56 |
| X 整改后复核归档清单 review-x/SHA256SUMS | 9560F65DD0CF356D3546144B174353F033B9E49112F96E3E4E940CE5F73EF8D7 |
| Y 整改后复核归档清单 review-y/SHA256SUMS | F3F06DC8C518054E113C1EDE73ABA6FB6679B128AEB9A3D018B965ED891F664F |
| D-059 候选人工验收 owner-acceptance-D059.md | 87207B1BD4FA76A45FDE9F48D8035BC9421B8B842FD7422E1CA004F5D8BF4A3C |
| X Step 05 原会话与本地状态回执 | 1A09E0388F80C81B4649A21BC574481B364A415C29A64363E7A12E0535B1CAFA |
| 集成源码 integrated-source-receipt.json | 36FBED07FAB4AC1630CCB30AF48032750B074D0BAC7DAE425545838ADA5B4606 |
| 全量和双序 PostgreSQL 组合实证 integration-unified-203159-verified.json | D5DB5398D33D8FECA43961F6A5375B6FD671A154A901383E725C21EC55D5E461 |
| 正式只读 formal-readonly-204808-verified.json | 8BA5275E891D4E5F1467DD14FF831FCC3D5E21DBC175F2821FF5729E729A5438 |
| 正式第一次失败 formal-detail-205458-audit.json | EB4DC753F23079B739C1A9855B08CEA419B81939F66F80700884F6A2CDF87957 |
| 原 / 修复后守卫启动脚本 | 6595E843A22C51924AFA3534B29C5C40612500436921D878839EA3F9B945F696 / 4AEF188527D66702BBAB0DABAC653EE36A20556ECB9F29F290F504CBD967138D |
| 正式成功 formal-26-27-detail-20261128-210544-286/formal-detail-receipt.json | 5BADFDC029FF40FCBFB4F8B80832BFDE2D7E5FD0FBDDE5808F7590BC7E5D9181 |
| 同一正式成功批 40 项证据清单 SHA256SUMS | FA80CAC7132BDEC8CB6D8507FE28851E127BF8D5858546650CDC2C9416CAD91F |
| Y 在 S0 后跨组信息暴露审计 | 06C1300093E1EAA120EEF11E82247BC9AE6894B85156E5D19E298A9D0EF83534 |

X 的 S0 后测试整改、P06 原始成功阶段与外层退出码未捕获的补证，以及 Y 的定向、PostgreSQL 和全量证据，均通过各自的复核 SHA256SUMS 追溯，未重新冻结。Y 的原开发会话在 S0 已封存之后、整改之前接触到 X 评审材料，不能称整改阶段依旧严格隔离；并无据此改判 S0 或另开的 R1，也不据此断言某处实现的因果来源。未为正式场景创建安全待审核样本，正向写入、表单及故障由隔离原件证明。

## 回顾与结题分析边界

- 截至 D1，Y−X 的故事会话差为 0，首过率差为 0 个百分点，R1 规则命中差为 +2。已确认差异涉及锁后时钟及 FR-018 业务拒绝边界，属于需求语义与架构／规约组合约束，不能从两个故事分离各自贡献。
- 12 个故事的机械情景外推是额外首过 0、额外故事会话 0；按 R1 规则次数差外推为 24 次规则命中，仅作情景展示，不当成真实收益。不能把规则或 ADR 项数直接折抵规划工时。规划投入、整改花费和未来的 C 后验量未齐，不预判净收益。
- 样本共两个故事，非随机、故事与路径绑定，审批和拒绝还有各自边界与残余难度差异。人员知情、实现／审查顺序、成熟源码隐含约束与 Y 的 S0 后偏差都可能影响解释。若规划可复用程度、功能复杂度或下游审查成本不同，结论可能反转。期末按同口径补 C、真实工时及返工，不预测缺失值。
