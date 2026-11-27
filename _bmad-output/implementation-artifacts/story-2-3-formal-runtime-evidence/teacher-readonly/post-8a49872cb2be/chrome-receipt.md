# Story 2.3 · 零预约 POST 恢复取证

原学生及匿名证据沿用。教师原 403 不重放。Story 保持 review。

- 教师模式 `read_only_empty`。教师本人链路 `None`，未自动认定最终验收。
- [当前数据库](current-db.json) · [ACL](acl.json) · [断言结果](result.json)
- `all_business_rows_unchanged` — 通过
- `no_student_or_booking_post` — 通过
- `teacher_same_404` — 通过
- `admin_no_entry_and_real_403` — 通过
- `anonymous_302_from_original_real_log` — 通过

| 北京时间 | 角色/ID | 请求 | HTTP | 写入 |
| --- | --- | --- | --- | --- |
| 2026-11-27T16:49:31.720212+08:00 | None/None | `GET http://127.0.0.1:8003/login/` | 200 | [] |
| 2026-11-27T16:49:31.817489+08:00 | None/None | `GET http://127.0.0.1:8003/favicon.ico` | 404 | [] |
| 2026-11-27T16:49:31.874703+08:00 | None/None | `GET http://127.0.0.1:8003/login/` | 200 | [] |
| 2026-11-27T16:49:32.061685+08:00 | None/None | `GET http://127.0.0.1:8003/favicon.ico` | 404 | [] |
| 2026-11-27T16:49:45.367049+08:00 | None/None | `GET http://127.0.0.1:8003/login/` | 200 | [] |
| 2026-11-27T16:49:56.073839+08:00 | teacher/3 | `POST http://127.0.0.1:8003/login/` | 302 | ['session', 'session', 'last-login'] |
| 2026-11-27T16:49:56.129863+08:00 | teacher/3 | `GET http://127.0.0.1:8003/identity/` | 200 | [] |
| 2026-11-27T16:50:12.564863+08:00 | teacher/3 | `GET http://127.0.0.1:8003/reservations/1/result/` | 404 | [] |
| 2026-11-27T16:50:18.808823+08:00 | teacher/3 | `GET http://127.0.0.1:8003/reservations/4611686018427387904/result/` | 404 | [] |
| 2026-11-27T16:50:25.498912+08:00 | teacher/3 | `GET http://127.0.0.1:8003/reservations/` | 200 | [] |
| 2026-11-27T16:50:26.808365+08:00 | teacher/3 | `GET http://127.0.0.1:8003/identity/` | 200 | [] |
| 2026-11-27T16:50:34.607051+08:00 | teacher/3 | `GET http://127.0.0.1:8003/login/` | 200 | [] |
| 2026-11-27T16:50:51.378168+08:00 | admin/1 | `POST http://127.0.0.1:8003/login/` | 302 | ['session', 'last-login'] |
| 2026-11-27T16:50:51.436969+08:00 | admin/1 | `GET http://127.0.0.1:8003/identity/` | 200 | [] |
| 2026-11-27T16:50:55.023769+08:00 | admin/1 | `GET http://127.0.0.1:8003/identity/` | 200 | [] |
| 2026-11-27T16:50:58.702432+08:00 | admin/1 | `GET http://127.0.0.1:8003/reservations/` | 403 | [] |
