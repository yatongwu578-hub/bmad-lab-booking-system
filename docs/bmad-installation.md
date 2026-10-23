# BMAD 安装与团队配置

项目：`bmad-lab-booking-system`；团队：3 人。课程基线见 [course-requirements.md](course-requirements.md)。本说明不代表 M1 门禁已通过。

## 当前安装依据

本地 `_bmad/_config/manifest.yaml` 记录 BMAD **6.12.4**，模块为内置 `core`、`bmm`，集成为 `codex`，`installShims: false`。安装时间记录为 `2026-10-23T01:20:16.350Z`；这是清单中的时间，不是本次重新安装的记录。

Codex 通过 `.agents/skills/<skill-name>/SKILL.md` 发现工作流。当前有 29 个技能目录，步骤、模板、脚本和参考资源随技能保存。`_bmad/` 保存配置、安装清单及运行支持脚本。兼容说明中的旧技能名称不意味着对应入口已安装；以实际技能目录和 `bmad-help` 为准。

## 共享与个人配置

| 路径 | Git 策略 | 用途 |
| --- | --- | --- |
| `.agents/skills/` | 提交 | 固定团队使用的工作流、模板和辅助脚本 |
| `_bmad/_config/`、`scripts/`、`core/`、`bmm/` | 提交 | 安装版本、目录和运行支持 |
| `_bmad/config.toml` | 提交，不直接修改 | 安装器管理的基础配置 |
| `_bmad/custom/config.toml` 及团队定制 | 提交 | 安装器保留的团队覆盖配置 |
| `_bmad/config.user.toml` | 忽略 | 个人安装答案 |
| `_bmad/custom/**/*.user.toml` | 忽略 | 个人覆盖配置 |
| `_bmad/render/` 生成内容 | 由原有子目录规则忽略 | 可再生成的技能快照 |
| `_bmad-output/` 的正式产物和过程证据 | 提交 | 规划、实施、评审和实验记录 |

本地 `_bmad/scripts/config_utils.py` 的 `load_central_config` 明确按以下顺序合并，后层覆盖前层：

1. `_bmad/config.toml`
2. `_bmad/config.user.toml`
3. `_bmad/custom/config.toml`
4. `_bmad/custom/config.user.toml`

团队覆盖使用已有字段：

```toml
[core]
project_name = "bmad-lab-booking-system"
communication_language = "Chinese"
document_output_language = "Chinese"
```

语言配置控制交流和文档默认语言；技能名称、配置字段、文件路径及代码标识符保留英文。个人最后一层仍可覆盖团队默认值；团队协作时应检查实际解析结果。不要将账号密码或 Token 放入共享配置，三个成员各自使用自己的账号。

## 复现安装

已有仓库使用者优先保留仓库中的安装快照，无需每次克隆都重装。需要重建时，在项目根目录执行固定版本的交互式安装命令：

```powershell
npx.cmd bmad-method@6.12.4 install
```

安装时选择当前项目目录、`bmm` 模块（`core` 为基础模块）、Codex 集成，交流和文档语言选择中文；完成后核对版本、模块、实际入口及团队覆盖配置，并检查安装差异。此命令固定安装器版本，交互选择仍是复现条件；本次没有重新运行安装器，也没有声称重装已验证。原始安装所用命令未保存在仓库中，不能据清单反推出原始会话。

安装命令形式依据 [官方安装说明](https://docs.bmad-method.org/start/install-bmad/)。该网页同时包含 v7 内容；本项目固定使用 6.12.4，不采用其中的 v7 setup 流程。Windows 使用 `npx.cmd` 可避免调用受 PowerShell 脚本执行策略限制的 `npx.ps1`。

## 验证方法

本地解析器使用标准库 `tomllib`，需要 Python 3.11+；不能仅用默认 Python 的存在判断可运行。使用已安装的 Python 3.11+，或通过 uv 选择解释器：

```powershell
uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root . --key core.project_name --key core.communication_language --key core.document_output_language
```

uv 在缺少解释器时可能下载；本次不以下载或重新安装作为校验前提。预期三个值依次为 `bmad-lab-booking-system`、`Chinese`、`Chinese`。

Git 忽略规则可用以下只读命令验证，包含尚不存在的示例路径：

```powershell
git check-ignore -v --no-index _bmad/config.user.toml _bmad/custom/config.user.toml _bmad/custom/example.user.toml .venv/example .env .pytest_cache/example
git check-ignore -v --no-index .agents/skills/bmad-help/SKILL.md _bmad/config.toml _bmad/custom/config.toml _bmad-output/planning-artifacts/PRD.md decision-log.md retrospective.md
git ls-files --others --exclude-standard
git diff --check
```

第一条应列出忽略来源；第二条应无输出且退出码为 1，表示示例入口、团队配置和课程产物没有被忽略。检查 29 个技能目录各有非空 `SKILL.md`，并核对文件内 `name` 与目录一致。安装清单可能记录安装前源布局路径，不能直接把这些路径全部当成 Codex 落盘位置。

每个独立 BMAD 工作流使用新会话并先阅读课程要求。需要实际确认 Codex 技能加载时，在新会话调用 `bmad-help`；文件存在性检查不等同于完整工作流运行成功。

## 课程证据与提交边界

根目录忽略个人配置、Python 缓存、测试工具缓存、虚拟环境、`.env` 和私钥容器；保留已去敏的 `.env.example`。已有 `_bmad/custom/.gitignore`、`_bmad/render/.gitignore` 保留。不要整体忽略 `.agents/`、`_bmad/`、`_bmad-output/`，也不要笼统忽略所有日志，防止漏交实验原始证据。

简报、PRD、架构、ADR、Story、Sprint 状态及真实评审和实验记录持续提交到同一仓库。`decision-log.md`、`retrospective.md` 必须位于根目录。公开的会话证据应去除凭据和无关隐私，保留真实输入输出与人工判断，不能用缓存或自动生成日志代替人工审批证据。忽略规则不会自动识别嵌入普通文档中的密钥，提交前仍需检查实际差异。

本次只调整本地安装配置和说明，不运行业务测试、不代签人工审批，不执行 Git 暂存、提交或推送；实际校验结果见下节。

## 本次实际校验（2026-10-23）

- 使用本机已有 Python 3.12 运行 `resolve_config.py`，三个字段均为上述预期值。默认 `python` 为 3.10.14，未用于该解析器；没有下载解释器或重新安装 BMAD。
- 单独合并基础配置与团队覆盖（不加载个人配置），项目名及两项中文默认值校验通过，队友无需复制个人配置。
- 29 个技能目录均有可读取的 `SKILL.md`，其 `name` 字段与目录名称一致；未执行完整业务工作流或逐一运行辅助脚本。
- `git check-ignore` 确认个人配置、虚拟环境、环境文件、Python/测试缓存及渲染快照被忽略；技能入口、共享配置、PRD、Sprint 状态、根目录决策日志和复盘示例路径未被忽略。示例路径检查不表示相关产物已经创建。
- 对 238 个已跟踪或未忽略的 Git 候选文件扫描常见 OpenAI/GitHub/AWS 凭据及私钥头模式，无命中；候选文件不包含 `.user.toml`。这是模式检查，不代表可识别任意格式的秘密。
- 官方基础 TOML、两个模块 YAML 及两个原有子目录 `.gitignore` 的 SHA-256 与修改前一致；课程要求文档无 Git 差异。`git diff --check` 通过（该命令不覆盖未跟踪文件）。
- 本次新增根目录 `.gitignore`、本说明；修改团队覆盖 `_bmad/custom/config.toml`。未执行 `git add`、`git commit` 或 `git push`，尚无对应新提交证据。
