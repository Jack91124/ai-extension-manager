# Launch kit · 发布材料

Everything needed to announce AI Extension Manager on developer channels. Copy, paste, adapt.
发布时按渠道取用；所有数字和命令都在 v1.0.13 上验证过。

- Live site: https://jack91124.github.io/ai-extension-manager/ （中文 /zh.html）
- Repository: https://github.com/Jack91124/ai-extension-manager
- Mirror (China): https://gitee.com/ping-pong-squid-king/ai-extension-manager
- Skill listing: https://www.skills.sh/jack91124/ai-extension-manager
- Install: `python -m pip install --user "git+https://github.com/Jack91124/ai-extension-manager.git@v1.0.13"`
  (or download the v1.0.13 wheel), or `npx skills add Jack91124/ai-extension-manager`
- Hero image: [demo.gif](demo.gif) (animated, 109 KB), static [hero.png](hero.png), or the
  1200x630 social card [og.png](og.png) (rendered by [make_og.py](make_og.py))
- Long-form article (post as a blog/HN/V2EX body): [why-sync-overwrites.md](why-sync-overwrites.md)
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
- **26 end-to-end scenarios** — real CLI runs against throwaway fake tool homes; CI on 3 OS × 2 Pythons.
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

28 scenario tests, CI on 3 OS. No deps. MIT.

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
26 个端到端场景测试，Windows/macOS/Linux CI 全绿，MIT。

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

Python 3.9+, no dependencies, local-first. 28 scenario tests, CI on 3 OS.
Happy to answer questions about the per-tool path verification — some of it is
documented by vendors, some is marked "partial" in the support matrix on purpose.
```

## 5. Channel checklist · 渠道清单

| Channel | Asset | Status |
|---|---|---|
| GitHub README + topics + Release + Pages | README.md / README.zh-CN.md / v1.0.13 wheel / live site | done |
| skills.sh listing | root SKILL.md is discoverable by `npx skills add` | indexed; badge installed in READMEs |
| Gitee mirror | code + tag v1.0.13 | code done; Gitee Release needs a fresh token |
| X / Twitter | copy above + og.png (1200x630) | ready to post |
| 小红书 / 即刻 / V2EX | 中文文案 above + demo.gif or og.png | ready to post |
| Hacker News / r/ClaudeAI | Show HN copy above | ready to post |
| awesome-* lists / MCP directories | one-line + link | ready for PR (targets below) |

## 6. Launch-day checklist · 发布当天

1. Post hero image + copy on one primary channel; link the GitHub repo (not Gitee) first.
2. Pin an issue: "Which tool should get a first-class adapter next?" — collects demand.
3. Reply to every comment within the first 3 hours; log objections in `docs/feedback.md`.
4. Track: stars, `npx skills add` installs (skills.sh), issues by tool, clone traffic.
5. Do **not** claim verified support for Gemini/Cursor runtimes: the support matrix marks them
   `partial`. Say "documented, not runtime-verified on this machine" when asked.

## 7. Cold-start plan (zero audience) · 零受众冷启动

The repo is indexed but nobody sees it yet (0 views). Order matters: credibility first, reach second.

| Day | Action | Where | Asset |
|---|---|---|---|
| 1 | Add repo social preview image (Settings → Social preview → upload `docs/og.png`), confirm description/topics | GitHub web UI (no API) | og.png |
| 1 | Post the short Chinese post in one community where you already participate | 即刻 / V2EX / 小红书 | 中文文案 + demo.gif |
| 2 | Submit 2 awesome-list PRs (below) — reviewers care that the tool is documented and tested | GitHub PR | one-liner + link |
| 3 | Post the English X thread, pin it on your profile | X | X copy + og.png |
| 4–7 | Answer every reply within 3h; convert objections into README FAQ entries; ship a patch release if a bug is reported | GitHub | commit + release |
| 8–14 | Show HN only after the README survives 2 rounds of feedback (Show HN is one-shot per project) | news.ycombinator.com | Show HN copy |

**awesome-list targets (open a PR each; one line + link):**

| List | Repo | Entry fits |
|---|---|---|
| awesome-claude-code | `hesreallyhim/awesome-claude-code` | Tools / skills section |
| awesome-ai-agents | `e2b-dev/awesome-ai-agents` | Developer tooling |
| awesome-mcp-servers | `punkpeye/awesome-mcp-servers` | not a server — skip unless it syncs MCP configs |
| awesome-devtools | `mrcodedev/awesome-devtools` | CLI utilities |
| skills.sh "packs" / directories | `vercel-labs/skills` discussions | skill pack listing |

Rules that keep PRs alive: read CONTRIBUTING, keep the line in the list's existing format, no marketing
adjectives, one PR at a time, and reply to review comments the same day.

## 8. Social preview · 仓库社交预览图

Copy-paste post drafts (X thread, Reddit, Show HN, 中文社区, awesome-list PR template) live in
[`posts.md`](posts.md). Nothing there is posted automatically — you paste, you post.

GitHub has no API for this. Settings → General → Social preview → **Upload an image** → `docs/og.png`
(1200x630, 697 KB). This is what shows up when the link is pasted into X, Slack, Discord or Reddit —
without it the preview is a generic grey box, and link cards get measurably fewer clicks.

## 9. What not to say · 避免过度承诺

- Don't call it a plugin manager: vendor plugins are installed via vendor mechanisms only.
- Don't promise automatic migration of tool-specific plugins or credentials.
- Don't claim macOS/Linux runtime testing of each AI tool — CI tests the CLI, not the tools.
