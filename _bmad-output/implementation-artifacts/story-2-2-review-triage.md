# Story 2.2 · 四视角逐条裁决

全部四视角返回。Blind Hunter 的 108.577 kB 输入按 `min(floor(sqrt(108.577)+1),10)=10` 设置候选下限，返回 12 项。Edge Case Hunter 4 项，Verification Gap 3 项，Acceptance Auditor 5 项及其余正式行为摘要。先逐项核实和裁决，再按根因合并。以下不是团队人工处置或代码修改。

| ID | 视角及位置 | 裁决 | 可复查依据及归并 |
| --- | --- | --- | --- |
| 1 | Blind · views.py:86／services.py:236 | low | `never_cache` 不识别预取，已认证 GET 可能触发只能在到期后执行的收尾。D-043 批准该 GET；未发现匿名授权绕过或提前释放。排除扩大当前 GET 协议。 |
| 2 | Blind · forms.py:12 | low | Django 表单取同名参数末值，并非原生控件会生成的请求。有效末项本身通过严格日期验证。正式 AC 未禁重复参数，不新增公开输入规则。 |
| 3 | Blind · services.py:63 | false | 当前 Role 枚举严格仅三种，不存在当前第四角色静默获权的结果。增加业务角色时另审。 |
| 4 | Blind · occupancy.html:25 | false | FR-006 和 Story 2.1 的 `valid_window` 拒绝非整点及非零秒／微秒，有效写入不能形成所述亚秒区间或间隙。测试旁路夹具不是正式数据。 |
| 5 | Blind · services.py:220 | low | 初次授权后撤权恰逢不存在设备，可早返 404，已有设备锁后可 403。没有返回任何受保护时段和无写，早期不存在处理符合 AC-6。本轮不扩大为强一致撤权机制，也不据此关闭 2.1 D01。 |
| 6 | Blind · services.py:234 | low | 纯投影确在提交前持锁，模板在提交后。未见超过正式 NFR 或正确性缺陷，拆分服务结构不列本轮整改。 |
| 7 | Blind · views.py:103 | low | 待核查无诊断关联号属已知运维可用性改进，正文不误报、不重试。本故事不扩展诊断协议，既有 P14 不动。 |
| 8 | Blind · verify_equipment_occupancy.py:75 | medium | P1。实际开发日志两次 `object_type` 绑定均为 `reservation`；探针第二条送出的值是 `invalid`。真实 23514 及前后业务快照仍支持 AC-8。 |
| 9 | Blind · verify_equipment_occupancy.py:569 | low | P2。写 `cleanup=true` 在实际验证之前，失败会退出非零且没有最终成功标记。原批清理已另算通过，不否定这批结果。 |
| 10 | Blind · verify-story-2-2.ps1:109 | low | D1。旧锁不存在时跳过，无法覆盖另一旧入口稍后新建的竞态。原已登记 RD01，同一隔离库继续不并跑。 |
| 11 | Blind · verify-story-2-2.ps1:42 | low | P3。旧包装先枚举一次，两次用同一列表；新增文件可能漏掉。外层独立入口已补鲜活路径清单对比，不追改运行器或旧清单。 |
| 12 | Blind · test_occupancy.py:173 | low | P4。测试确认 action 与 label，另构造 HTTP 查询，没有让实际控件导航并冻结输入名。当前源中 method、action、name 与后端一致。 |
| 13 | Edge · views.py:92 | low | 与 2 同根因。重复参数忽略前项是真实行为，但更改重复参数处理不是本 AC 的必要修补。 |
| 14 | Edge · services.py:224 | low | 既有设备锁协议没有此路由专用等待上限。正式 AC 要求等待并重读，无单请求等待 SLA；不在本 Story 新增超时分支。 |
| 15 | Edge · occupancy.html:25 | false | 与 4 一样，亚秒记录非正式提交可达状态。 |
| 16 | Edge · verify-story-2-2.ps1:109 | low | 与 10 同根因，D1。原批序贯且基线无漂移。 |
| 17 | Gap · test_occupancy.py:173 | low | P4。变更输入名仍可能过现有断言，属证据覆盖，不是当前控制坏了。 |
| 18 | Gap · services.py:199 | low | P5。历史单类及有效单类各验证，但没有同一日混合夹具冻结恰好的补集。现版把两类一起排序，未见错误展示。 |
| 19 | Gap · occupancy.html:39／47 | low | P6。未冻结历史／未占用段落的实际 HTML 行，当前模板确实有两处循环，不能把 context 验证当全部 HTML 回归。 |
| 20 | Acceptance · views.py:92 | low | 与 2／13 同根因。末值有效不等于放行相同规则下的唯一非法日期，不判 AC-6 失败。 |
| 21 | Acceptance · views.py:86 | low | 与 1 同根因。Django 对 GET 不用 CSRF token，风险限定为合法会话触发到期收尾，无跨站读取、任意写或提前到期证据。不得扩大为安全防护已全覆盖。 |
| 22 | Acceptance · verify_equipment_occupancy.py:75 | medium | P1，与 8 同根因。实际语句绑定和注入前绑定应分开记录。探针自测和独立审计都不得把注入前值冒称执行值。 |
| 23 | Acceptance · test_occupancy.py:173 | low | P4，与 12／17 同根因。开发资料本身未声称 Chrome 点击；正式运行用真实导航补证。 |
| 24 | Acceptance · services.py:234 | low | 与 6 同根因。事务原子性不受纯数据计算影响，无本次必改事项。 |

## 路由

- P1 Medium，修正故障日志实际绑定与原绑定标注，不改变故障和业务逻辑。独立交接入口已把原批的限制显式标注，真实回滚证据仍然完整。
- P2 Low，将清理成功的原始记录写到核对后，不以单一 cleanup 标记验收。
- P3 Low，每份快照重枚举输入集。外层为这轮鲜活证据增加文件集合核验，原包装长期改进仍留待办。
- P4 Low，锁定真实日期表单导航。正式 Chrome 烟测是本轮交接的产品导航补证，自动化覆盖不阻塞产品验收。
- P5／P6 Low，补混合日精确补集和历史／未占用的模板行测试。不是现有算法或模板缺陷。
- D1 Low，复用 RD01，统一验证入口时处理共享租约。不要把保留事项写成已修复。
- 13 项 rejected，保留各自的事实及不处置理由。没有需要更改正式 FR、AC、ADR、实验 A 或 Sprint 的人工需求决定。当前所有 Patch 保留待办，不应用代码补丁。

负责人后续在 D-044 选择 2，批准 P1～P6 的非阻塞延期，不改变上表原始裁决，也未实施补丁。D1 未关闭，13 条不采纳依据保持。中央台账沙箱写入拒绝，保留原 RD01。以 [D-044 七条合并稿](story-2-2-d044-deferred-pending.md) 和 [Step 4 处置记录](story-2-2-review-disposition.md) 为准，不另行合并旧 D1 单条草稿。

[AC 与证据复核](story-2-2-independent-review.md) · [规格待办](spec-2-2-query-equipment-occupancy.md#review-findings)
