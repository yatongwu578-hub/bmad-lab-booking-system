# Story 2.3 隔离开发验证原始回执

批次 `story-2-3-run-20261127-111101-492-41d9eb74`，2026-11-27 11:11:01–11:12:32（北京时间）。用户报告在普通 Windows PowerShell 运行仓库的 [verify-story-2-3.ps1](../verify-story-2-3.ps1)。本归档不依赖外部目录。

- 25 个原始文件逐字节复制并复算 SHA-256。JSONL 中的 HTML 来自测试夹具，3 处 CSRF 值已由原探针遮盖。候选归档扫描未命中凭据、Cookie 或本机绝对路径。8 个非必要的 `*.command.txt` 未归档，避免带入本机运行路径；使用归档阶段名与仓库脚本还原执行顺序。没有伪造控制台回显。
- `spec-at-run.md` 是状态同步之前的规格原件，匹配 `before.sha256` 中对应原路径的条目。评审时该路径已按工作流更新为 `in-review`，须使用这个副本复算当时指纹。
- [archive.sha256](archive.sha256) 覆盖 25 个原始文件和这个规格快照，不包含自身或本说明。 [开发核对报告](../story-2-3-dev-evidence.md) · [评审交接](../story-2-3-code-review-handoff.md)
