# AI Extension Manager · AI 扩展资源管理助手

### 一个中央库，六个 AI 工具，双向同步，绝不静默覆盖你的修改。

`aem` 把 Agent Skill、规则文件（rules）和 MCP 配置统一存进本地中央资源库，再同步到
Claude Code、OpenAI Codex、Gemini CLI、Cursor、VS Code Copilot 和 DSH。
判断"谁变了"靠 SHA-256 内容哈希和每个目标的同步记录，而不是"最后修改时间更新就覆盖"。

**快速开始** · [为什么需要它](#为什么需要它) · [60 秒上手](#60-秒上手) ·
[冲突模型](#冲突模型) · [支持矩阵](#支持矩阵) · [安全策略](#安全策略) · [CLI](#cli-速查)

---

## 为什么需要它

每个 AI 工具都有自己的目录：`~/.claude/skills`、`~/.codex/skills`、`~/.gemini/skills`、
`~/.cursor/skills`、`~/.copilot/skills`、`~/.dsh/skills`。结果就是：同一个技能复制五份、
在其中三份里被改过；给一个工具装了，另外五个不知道；一个"同步脚本"把上周的本地修改静默删掉。

`aem` 以**中央资源库为唯一事实来源**，记录每个工具实际收到的是哪个哈希，因此能区分
"只有库变了 / 只有目标变了 / 两边都变了"，并在第三种情况下拒绝猜测。

它坚持**本地优先**：纯文件、纯 JSON，无服务端、无账号、无遥测。

## 60 秒上手

需要 **Python 3.9+**，无第三方依赖，支持 Windows / macOS / Linux。

```bash
git clone https://github.com/OWNER/ai-extension-manager.git
cd ai-extension-manager
python -m pip install .
aem init          # 创建 ~/.ai-extension-manager
aem doctor        # 检查 Python、路径、注册表、锁、已安装工具
aem scan          # 扫描六个工具及其技能目录
```

不安装也可以：所有命令等价于 `python scripts/aem.py <命令>`。

## 60 秒工作流

```bash
# 1. 从 GitHub 或本地目录导入
aem import --source https://github.com/owner/repo/tree/main/skills/my-skill

# 2. 分发到需要的工具（--agent 可重复）
aem sync --direction distribute --agent claude --agent codex --resource my-skill

# 3. 验证副本与库一致
aem verify --all
aem status
```

所有操作可回滚：`aem backups` 列出快照，`aem restore` 恢复旧版本，`aem compare` 输出
统一 diff。在某个工具里改了技能想拉回来？`aem sync --direction both` 会安全导入目标侧修改；
两边都改过时返回退出码 `2`，不写任何文件。

## 冲突模型

| 状态 | 发生了什么 | 默认动作 |
|---|---|---|
| **A** | 只有中央库变了 | 备份后更新目标 |
| **B** | 只有目标变了 | 保留目标，建议导入 |
| **C** | 两边都变了 | **冲突：不写文件，退出码 2** |
| **D** | 目标被删除 | 报告缺失，不静默重建 |
| **E** | 目标目录不存在 | 报告不可用，不猜路径 |
| untracked | 存在从未同步过的副本 | 内容相同则登记，不同则冲突 |

冲突证据保存在 `conflicts/`。解决方式必须显式选择：保留库版本、保留目标版本、另存为新版本、
手动合并、或恢复历史版本。默认绝不覆盖。

## 支持矩阵

| 工具 | Skill | Rules | MCP | Plugin | 验证程度 |
|---|---|---|---|---|---|
| **Claude Code** | 复制 / 链接 | `CLAUDE.md` | JSON 合并 | marketplace 命令 | 本机实测（2.1.318） |
| **OpenAI Codex** | 复制 / 链接 | `AGENTS.md` | 手动（TOML） | marketplace 命令 | 配置目录实测，无 CLI |
| **DSH** | 复制 / 链接 | `AGENTS.md` | 经插件 | `dsh plugin add` | 本机实测（0.2.0-rc.2） |
| **Gemini CLI** | 复制 / 链接 | `GEMINI.md` | JSON 合并 | `gemini extensions install` | 官方文档，未运行时验证 |
| **Cursor** | 复制 / 链接 | `.cursor/rules` | JSON 合并 | 仅市场 UI | 路径部分验证 |
| **VS Code / Copilot** | 复制 / 链接 | instructions | JSON 合并 | VS Code 扩展 | 文档 + 本机 VS Code |

插件代码**不会跨工具复制**：插件必须用目标工具自己的安装机制，`aem` 返回精确命令，
并拒绝把工具专属插件搬到别的工具。

## 安全策略

- 导入前扫描危险 Shell 模式、可疑脚本和密钥；高风险需 `--allow-risk`，凭据直接拒绝；
- 覆盖前自动备份；
- 不删除未经确认的资源；
- 拒绝把 `github.com` 重写到第三方镜像的 git 配置（`--allow-mirror` 才放行）；
- 密钥使用环境变量占位符，中央库只存哈希与元数据；
- 全部支持 `--dry-run`，试运行不留 journal。

完整策略见 [references/security-policy.md](references/security-policy.md)。

## CLI 速查

| 命令 | 作用 |
|---|---|
| `aem init` | 创建中央库目录结构 |
| `aem doctor` | 诊断 Python、路径、注册表、schema、锁、工具、磁盘 |
| `aem status` | 资源 × 工具同步状态总表，`--strict` 有漂移即失败 |
| `aem scan` | 扫描工具、版本与技能目录 |
| `aem detect --path P` | 判定 P 是 skill / plugin / MCP / rules |
| `aem import --source P` | 导入本地路径或 GitHub 地址 |
| `aem sync --direction import\|distribute\|both` | 双向同步与冲突检测 |
| `aem compare --left A --right B --diff` | 哈希清单 + 统一 diff |
| `aem verify --all` | 校验已安装副本 |
| `aem backup / backups / restore / prune` | 快照与回滚 |

所有命令都接受 `--home`、`--workspace`、`--json`。退出码：`0` 成功、`1` 错误、
`2` 冲突或差异。详见 [references/cli-reference.md](references/cli-reference.md)。

## 演示

```bash
python demo/run_demo.py
```

演示在临时沙箱里创建假中央库和六个假工具目录，完整走一遍：导入 → 分发到三个工具 → 校验哈希
→ 修改其中一个副本 → 显示漂移 → 修改上游 → 触发真实冲突并拒绝覆盖。不会碰你的真实配置。
完整输出见 [demo/demo-output.txt](demo/demo-output.txt)。

## 状态与限制

这是可运行的 **v1.0 CLI + Agent Skill**，不是完成品：

- ✅ 导入、分发、双向同步、冲突检测、备份、校验、比较、恢复；
- ✅ 六个适配器、安全扫描、JSON 输出契约；
- ✅ 22 个场景测试（全部使用一次性假目录）；
- 🚧 DSH Plugin 图形面板**只有规格，尚未实现**；
- 🚧 插件安装委托给各工具原生命令，尚未自动执行；
- ⚠️ Gemini CLI 与 Cursor 只对照官方文档/路径映射，未做运行时验证；
- ⚠️ Codex 的 MCP 写入是手动的（刻意不自动改 TOML）。

## 许可证

MIT，见 [LICENSE](LICENSE)。
