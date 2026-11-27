# Story 2.5 · M01 整改开发实测及复审交回

2026-11-27（北京时间）｜BMAD 6.12.4 原 Build 会话核对。D-050 批准的唯一代码整改 M01（正式 AC-8）已完成开发专项，规格 `in-review`、Sprint `review`。交回原独立评审会话做针对性源码复审及一次集中独立复验，不代替独立结果或最终验收。 [D-050](../../decision-log.md#d-050-2026-11-27-负责人批准-story-25-独立评审处置) · [首次发现及裁决](story-2-5-review-triage.md) · [人工处置](story-2-5-review-disposition.md) · [正式 AC](../planning-artifacts/epics.md#story-25-管理员查询预约详情并按设备筛选)

## 真实执行与只读复算

项目组在普通 PowerShell 运行 `verify-story-2-5.ps1 -M01Only`，本会话只读核对。20:32:52～20:33:06，原 `.venv`、Python 3.13.17、Django 5.2.19、PostgreSQL 17.12，唯一目标 `127.0.0.1:5433/test_lab_booking`，`lab_booking_test`、Read Committed。**3/3 Django 专项、1/1 真实 HTTP/PostgreSQL 探针、零跳过、10 个阶段退出 0。** 原始 `batch-marker.txt` 唯一行为 `STORY25_M01_DEV_OK`，内层为 `STORY25_PROBE_OK cases=1`。没有把既有全量回归当成本批重跑。 [专项原始日志](story-2-5-run-20261127-203252-421-ad7cfd4fb78242f796769e9dff0f6331/targeted.stderr.txt) · [退出码](story-2-5-run-20261127-203252-421-ad7cfd4fb78242f796769e9dff0f6331/stages.txt) · [成功标记](story-2-5-run-20261127-203252-421-ad7cfd4fb78242f796769e9dff0f6331/batch-marker.txt) · [脱敏交叉核对](story-2-5-m01-development-evidence.json)

| 同一隔离预约 #1069 | 真实结果 |
| --- | --- |
| 空、空白、重复、33 字符及 NUL 的 `equipment` | 已认证管理员五次均收到 400；逐例零预约/设备/历史业务 SQL、零设备锁、零取时、零业务提交和历史尝试，快照仍为待审核，设备、有效占用及历史均相同。到期待审原本已无逻辑有效占用，不计作释放一次占用。 |
| 合法导航参数 | HTTP 200，保留设备筛选返回链接。固定目标设备锁后复核及重读，一次数据库 `t_decision`，只有一次状态 UPDATE 和一次历史 INSERT，事务提交后独立连接看到已失效及唯一系统历史 #515。历史原因和判定时刻与原证相符。 |
| 缺省参数再次读取 | HTTP 200，返回全量管理列表入口。零设备写锁、零取时、零 DML，业务快照不变，仍只有历史 #515。 |

87 个输入的前后散列清单相同，且在同步规格状态前与工作区逐项一致。三份外层隔离基线同散列，内层 `cleanup=true` 且内部前后快照与外层基线一致，五个受控表恢复为零行，采集的角色、表／迁移及 ACL 未变。不是完整 schema 或序列值指纹。运行时规格按原字节另存，便于在现规格进入 `in-review` 后重算散列。首次评审四视角、逐项裁决、人工处置、中央台账保留未改。 [原始 HTTP/SQL/快照](story-2-5-run-20261127-203252-421-ad7cfd4fb78242f796769e9dff0f6331/independent.jsonl) · [输入清单](story-2-5-run-20261127-203252-421-ad7cfd4fb78242f796769e9dff0f6331/before.sha256) · [运行时规格快照](story-2-5-m01-tested-spec.md)

## 原独立评审接续

核对最新版 `run-story-2-5-independent.ps1` 的语法和调用链。它以 `-Remediation` 执行原 5 个专项目标、125 项 Django 全量和 17 项 PostgreSQL 探针，`edge-input.m01` 纳入新专项而不改变探针分母。离线审计要求精确用例和阶段、成功标记、输入散列和清理，并逐条核对 M01 五个 400 及合法/重复控制的路径、SQL、持久化快照和系统历史，缺证不会输出最终 `STORY25_REVIEW_RUN_OK`。这次仅确认入口和实测开发证据，独立全量尚未执行。 [独立脚本与执行说明](story-2-5-remediation-handoff.md#整改后一次独立复验)

复审只重新判断 M01，已批准的其他裁决与延期保持不变，W01 正式发布门槛仍开放。原测试证据和 D-040 的 NFR-001 20×10 保留，不重复执行历史标准组。按课程基线落实 PPT 第 25、26、27、33、34、36 页的追溯、逐 Story 实施与独立评审、交付留证、实验 A 和人机决定记录，不冒充复核原 PPT 页。Sprint 8／5 不变、三人共同操作。不重复应用补丁、不访问正式库或执行 GRANT、不提前开发 Sprint 2、不标 `done`、不暂存、不提交或推送。 [课程要求](../../docs/course-requirements.md)
