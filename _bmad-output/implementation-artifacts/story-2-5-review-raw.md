# Story 2.5 · BMAD Step 2 四视角回执

负责人在独立评审会话明确批准范围并进入 Step 2。四个视角同一宿主能力、独立上下文，各自读取统一差异，未运行应用或数据库。宿主最大 4 个活跃线程（含主持人），第四路初次并发请求被拒，空位释放后启动，4 路均实际返回，失败层 0。下列是各视角返回意见的编号摘录，非人工意见、非主持人裁决。详见逐项裁决记录。

冻结差异 SHA-256 `87C03C38A327CAAEAEA8D6421041514FECC793B10DA8491B9B52C36BA6586155`，96,055 bytes。Blind Hunter 的下限为 min(floor(sqrt(96.055)+1),10)=10，实际返回 11 项。其过程中已自行撤回的超长 URL 数字导致 500 不是最终发现，独立复核确认 Django 路由捕获转换 ValueError。

| 原始 ID | 视角 | 发现摘要及位置 |
| --- | --- | --- |
| 01 | blind-hunter | `views.py:197–222` 提交后时间格式化，数据库可存但北京时间溢出的时间会在事务提交后显示失败。 |
| 02 | blind-hunter | `audit/services.py:54–59` 按 ID 选择原因，而历史按实际记录时间排序。 |
| 03 | blind-hunter | `audit/services.py:54–59`、`admin_detail.html:25` 摘要不标来源动作，可能把既往批准原因看作无原因的取消理由。 |
| 04 | blind-hunter | `reservations/services.py:249–273` 全量物化和大 IN，增长时持锁和内存都扩大。 |
| 05 | blind-hunter | 验证器第 58–71 行要求未跟踪的规格和检查点，只有代码差异的干净检出不能运行。 |
| 06 | blind-hunter | 验证器第 117–130 行只打开已存在的旧租约，其他入口可能并跑。 |
| 07 | blind-hunter | 探针第 84–128 行不锁定原因及历史 SQL 的 ID 绑定。 |
| 08 | blind-hunter | 探针第 448–490 行有迟发详情历史故障，没有迟发列表原因 SELECT 故障组合。 |
| 09 | blind-hunter | 探针第 130–190 行与实现共享 `_beijing_text` 和时区对象作部分期望。 |
| 10 | blind-hunter | 探针第 130–490 行只在断言后登记逐例记录，故障批次可能漏掉失败调用的原始响应和 SQL。 |
| 11 | blind-hunter | 探针第 43–59 行的 schema 比较是名字、拥有者、ACL 和迁移，不包括定义或序列位置。 |
| 12 | edge-case-hunter | `audit/services.py:54–59` PostgreSQL C 类空白匹配可能和 Python Unicode strip 不同。 |
| 13 | edge-case-hunter | `audit/services.py:54–59` 更高 ID 但录入时间更早时，摘要与时间线可能不同。 |
| 14 | edge-case-hunter | `reservations/services.py:229–232` 最终角色复核之后外部撤权，可能在该请求已获授权后完成。 |
| 15 | edge-case-hunter | `reservations/services.py:250–254` 无本地 lock_timeout，阻塞事务可延长多设备持锁。 |
| 16 | edge-case-hunter | 验证器第 126–129 行在旧租约文件尚未存在时不能协调未来旧入口。 |
| 17 | verification-gap | `admin_detail.html:15` 的详情摘要 `dl` 不是独立断言，删除它时现有历史／正文匹配仍可能通过。 |
| 18 | verification-gap | `views.py:203` 详情有 GET 限制，但只有列表 POST 负例，删除详情装饰器不会被现测检出。 |
| 19 | verification-gap | `views.py:177,202` 有 no-cache 装饰器，但管理员路径未断言实际缓存头。 |
| 20 | verification-gap | `audit/services.py:77` 有时间相等时的 ID 排序，现有夹具时间不同或一预约一条历史，无法锁定次排序。 |
| 21 | acceptance-auditor | `views.py:196–199`、`admin_list.html:23–28` 未显示固定范围／判定参考，不提示并发新增下次出现。引用 AC-4／PC-005。 |
| 22 | acceptance-auditor | `views.py:210–212` 无效设备参数在详情只被清除返回条件，仍按预约执行 FR-018。测试第 158–159 行明确期待回退。引用 AC-8／冻结矩阵。 |
| 23 | acceptance-auditor | `services.py:256,273,277` 未来批准→取消与详情交错时，Read Committed 多语句可能显示旧摘要配新历史；当前 Sprint 尚无该写入口。 |

独立原始评审与开发证据分开。两者均不是新 PostgreSQL 独立运行回执。
