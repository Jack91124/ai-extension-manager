# Launch kit · 发布材料

Everything needed to announce AI Extension Manager on developer channels. Copy, paste, adapt.
发布时按渠道取用；所有数字和命令都在 v1.0.3 上验证过。

- Repository: https://github.com/Jack91124/ai-extension-manager
- Mirror (China): https://gitee.com/ping-pong-squid-king/ai-extension-manager
- Skill listing: https://www.skills.sh/jack91124/ai-extension-manager
- Install: `python -m pip install --user "git+https://github.com/Jack91124/ai-extension-manager.git@v1.0.3"`
  (or download the v1.0.3 wheel), or `npx skills add Jack91124/ai-extension-manager`
- Hero image: [hero.png](hero.png)
- Release: <https://github.com/Jack91124/ai-extension-manager/releases/latest>

---

## 1. Positioning · 定位

**One library. Six AI tools. Two-way sync that never silently overwrites your work.**

Not another "download skills from GitHub" helper — a local, hash-based sync engine for the skill
folders every AI coding tool invented separately.

不是又一个「从 GitHub 下载 Skill」的助手，而是给六个 AI 工具各自为政的 Skill 目录做**带版本记录的
双向同步**：中央库是事实来源，每个目标都记录「从哪个哈希同步过来」，所以能区分只有库变、只有工具变、
还是两边都变；两边都变时直接报冲突（exit 2），绝不静默覆盖。

## 2. Titles · 标题候选

1. **One library, six AI tools: two-way skill sync without the silent overwrites**
2. **Your AI tools each have a skills folder. This keeps them honest.**
3. **Git-like conflict detection for Claude Code, Codex, Gemini, Cursor, Copilot and DSH skills**
4. 中文：**六个 AI 工具的 Skill 目录，终于有一个不会静默覆盖的同步器**
5. 中文：**把 Claude Code / Codex / Gemini / Cursor / Copilot / DSH 的扩展放进一个库**

## 3. One-liner + bullets · 一句话与要点

> `aem` keeps Agent Skills, rules and MCP definitions in one local library and syncs them to six
> AI tools — with SHA-256 state tracking, per-target backups, and conflicts that stop instead of
> overwriting.

- **Six adapters, one command** — DSH, Codex, Claude Code, Gemini CLI, Cursor, VS Code Copilot.
- **A/B/C/D/E conflict model** — hashes + last-sync records, not "newest file wins".
- **Reversible by default** — every distribute backs up first; `aem restore` brings any version back.
- **Local-first** — plain files and JSON, zero dependencies, no telemetry, Python 3.9+.
- **24 end-to-end scenarios** — real CLI runs against throwaway fake tool homes; CI on 3 OS × 2 Pythons.
- **Tested safety rails** — blocks high-risk scripts and secrets, refuses git mirror rewrites.

## 4. Social copy · 社交文案

### X / Twitter (English)

```text
Every AI coding tool invented its own skills folder.

Claude Code: ~/.claude/skills
Codex: ~/.codex/skills
Gemini: ~/.gemini/skills
Cursor, Copilot, DSH: three more

So you copy the same skill 6 times, edit it in 3 places, and a sync script deletes last week's fix.

I built aem: one local library, six adapters, SHA-256 state tracking.

- only library changed -> update targets (backup first)
- only target changed -> import it back
- both changed -> exit 2, write nothing

24 scenario tests, CI on 3 OS. No deps. MIT.

https://github.com/Jack91124/ai-extension-manager

#AgentSkills #ClaudeCode #Codex #MCP #DevTools
```

### 小红书 / 即刻 / V2EX（中文）

```text
六个 AI 编程工具，六套 Skill 目录，同一个技能复制六份——然后在三个地方分别被改过。

我写了个 aem：一个中央库，六个适配器，双向同步。

关键不是"复制文件"，而是"知道自己复制的是哪个哈希"：
· 只有库变了 → 备份后更新目标
· 只有工具变了 → 反向导入
· 两边都变了 → 直接报冲突，退出码 2，一个字都不写

本地优先，纯文件 + JSON，零依赖，Python 3.9+。
24 个端到端场景测试，Windows/macOS/Linux CI 全绿，MIT。

GitHub: https://github.com/Jack91124/ai-extension-manager
Gitee（国内）: https://gitee.com/ping-pong-squid-king/ai-extension-manager

#AI编程 #ClaudeCode #Codex #效率工具 #开源
```

### Hacker News / Reddit

```text
Show HN: aem – two-way sync for AI agent skills across six tools

I kept hitting the same failure mode: the same skill copied into ~/.claude/skills,
~/.codex/skills, ~/.cursor/skills..., then edited in two of them, then a "sync" script
picks one and silently deletes the other change.

aem stores one library plus, for every target, the hash it was synced from. That record
distinguishes: only library changed, only target changed, both changed. The last case
writes nothing and exits 2. Every distribute backs up the target first; compare gives
per-file unified diffs; restore brings any snapshot back.

Scope is deliberately boring: skills, rules, MCP server definitions. Plugins are
detected but installed through each vendor's own mechanism, never copied across tools.

Python 3.9+, no dependencies, local-first. 24 scenario tests, CI on 3 OS.
Happy to answer questions about the per-tool path verification — some of it is
documented by vendors, some is marked "partial" in the support matrix on purpose.
```

## 5. Channel checklist · 渠道清单

| Channel | Asset | Status |
|---|---|---|
| GitHub README + topics + Release | README.md / README.zh-CN.md / v1.0.1 assets | done |
| skills.sh listing | root SKILL.md is discoverable by `npx skills add` | indexed, badge pending install count |
| Gitee mirror | code + tag v1.0.1 | done; Release needs a fresh token |
| X / Twitter | copy above + hero.png | ready to post |
| 小红书 / 即刻 / V2EX | 中文文案 above + hero.png | ready to post |
| Hacker News / r/ClaudeAI | Show HN copy above | ready to post |
| awesome-* lists / MCP directories | one-line + link | needs manual PR |

## 6. Launch-day checklist · 发布当天

1. Post hero image + copy on one primary channel; link the GitHub repo (not Gitee) first.
2. Pin an issue: "Which tool should get a first-class adapter next?" — collects demand.
3. Reply to every comment within the first 3 hours; log objections in `docs/feedback.md`.
4. Track: stars, `npx skills add` installs (skills.sh), issues by tool, clone traffic.
5. Do **not** claim verified support for Gemini/Cursor runtimes: the support matrix marks them
   `partial`. Say "documented, not runtime-verified on this machine" when asked.

## 7. What not to say · 避免过度承诺

- Don't call it a plugin manager: vendor plugins are installed via vendor mechanisms only.
- Don't promise automatic migration of tool-specific plugins or credentials.
- Don't claim macOS/Linux runtime testing of each AI tool — CI tests the CLI, not the tools.
