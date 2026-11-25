# Ready-to-post launch copy

Copy these as-is. They are written to be posted from a personal account, not a brand account.
Attach the image named under each post; all of them already live in this repo.

Suggested order (one post per day, do not post everything the same hour):

1. **Day 1** — X thread (EN) + the Chinese post in one or two Chinese communities.
2. **Day 2** — open 3–5 awesome-list PRs (templates at the bottom).
3. **Day 3** — Reddit post, phrased as "I built, looking for feedback".
4. **Day 8** — Show HN, only after the first week produced a few stars.

Image assets:

- `docs/report.png` — the strongest single image (shows the whole library on one page).
- `docs/og.png` — 1200x630 card for link previews.
- `docs/demo.gif` — 10-second terminal demo, use only where GIFs autoplay.

---

## X / Twitter thread (English)

**1/**
Every AI coding tool now has its own skills folder.
Claude Code: ~/.claude/skills
Codex: ~/.codex/skills
Cursor, Copilot, Gemini, DSH — all different.
So the same skill gets copy-pasted six times, and the one you edited by hand is the one that gets overwritten.

**2/**
I built aem: one central library, two-way sync to all six tools.

It tracks a SHA-256 hash of every copy, so it knows whether the library, the tool copy, or both changed since the last sync.

**3/**
The part that matters: it refuses to clobber you.

Both sides changed -> `conflict [C]`, exit code 2, nothing written.
Every write is preceded by a per-target backup. Every run is `--dry-run`-able.

**4/**
It is not a wrapper around a CLI flag. The rules:

- copy is the default; symlink is opt-in and verified
- MCP secrets never leave the machine (they become ${ENV_VAR})
- third-party git mirrors are refused
- plugins are never copied between tools that do not share a plugin format

**5/**
Install (no dependencies, Python 3.9+):

```
npx skills add Jack91124/ai-extension-manager
# or
python -m pip install --user "git+https://github.com/Jack91124/ai-extension-manager.git"
```

28 scenario tests, CI on 3 OS, MIT.
Would love feedback from people who juggle more than one agent:
https://github.com/Jack91124/ai-extension-manager

---

## Reddit post (r/ClaudeAI, r/ChatGPTCoding, r/LocalLLaMA)

**Title:** I got tired of copy-pasting the same skill into 6 different AI coding tools, so I built a hash-tracked sync tool

**Body:**

If you use more than one agent CLI, you know the problem: the same `SKILL.md` lives in
`~/.claude/skills`, `~/.codex/skills`, `~/.cursor/...`, `~/.copilot/skills`, and a couple more.
Keeping them in sync is manual copying, and the copy you edited by hand is the one that gets silently overwritten.

I built **aem** (AI Extension Manager). One local library, two-way sync, SHA-256 state per copy:

- `aem import --source <path|github-url>` pulls a resource into the library
- `aem distribute --agent claude --agent codex --resource my-skill` pushes it out
- `aem verify --all` proves the copies still match
- `aem report` renders the whole library as one offline HTML page

The design decision I care about: **it never decides a winner by mtime**. It compares library hash, target hash and the last sync record, so "both sides changed" is a conflict that exits 2 and writes nothing — not a coin flip that eats your edits.

No dependencies, no daemon, no telemetry, MIT.
Repo: https://github.com/Jack91124/ai-extension-manager

I would especially like to hear from people whose tools are not in my list — which agent CLI do you use, and where does it keep skills? (Windows symlink behaviour is where I still expect bugs.)

---

## Show HN (use on day 8 at the earliest)

**Title:** Show HN: Sync agent skills across six AI coding tools without silent overwrites

**Text:**

Most "sync" scripts compare modification times, so the last writer wins and hand-edited copies disappear.
This one keeps three facts per copy — library hash, target hash, and the hash recorded at the last sync —
which turns the normal cases into safe operations and the genuinely ambiguous case into a conflict that
exits with code 2 and writes nothing.

- One content-addressed library under `~/.ai-extension-manager/library`
- `import` / `distribute` / `verify` / `compare` / `backup` / `restore` / `report` subcommands, plus JSON output
- Per-target backups before any write; `--dry-run` everywhere
- Paths for Claude Code, Codex, Gemini CLI, Cursor, VS Code Copilot and DSH, each marked local / docs / partial
- Python 3.9+, standard library only, MIT

It is early (v1.0, 28 scenario tests), and the DSH graphical plugin is still a spec, not a product.
The thing I want reviewed is the conflict model and the Windows link behaviour.

https://github.com/Jack91124/ai-extension-manager

---

## 中文社区帖（V2EX / 掘金 / 即刻，可各发一次）

**标题：** 同时用 Claude Code 和 Codex 的人，技能库是不是都在手动复制？

**正文：**

现在的 AI 编码工具几乎每家都有自己的一套 skills 目录：Claude Code 在 `~/.claude/skills`，Codex 在
`~/.codex/skills`，Cursor、Copilot、Gemini CLI、DSH 各不相同。同一个 SKILL.md 复制六份，改的时候忘了
改哪一份，下一次同步就被覆盖掉——这是我自己最烦的一件事。

所以我写了一个小工具 **aem**（AI Extension Manager）：一个本地中央库，向六个工具双向同步。

和"再写一个复制脚本"的区别在冲突判定：

- 每个副本记录三个值：中央库哈希、目标当前哈希、上次同步时的哈希
- 只有一侧变化 → 安全更新（先备份，再原子替换）
- 两侧都变化 → 输出 `conflict [C]`，退出码 2，**一个字节都不写**
- 目标被删、目录不存在、文件被手工改过，都单独标识，不会当成"没变化"

其余几条默认值：复制优先（链接可选且校验平台）、MCP 的密钥不出本机（写入中央库时替换成
`${ENV_VAR}`）、第三方 git 镜像直接拒绝、插件绝不跨工具复制（安装机制不同的东西不该合并）。

安装（零依赖，Python 3.9+）：

```
npx skills add Jack91124/ai-extension-manager
```

29 个端到端测试，Windows/macOS/Linux CI 全绿，MIT，v1.0.14。

仓库：https://github.com/Jack91124/ai-extension-manager
在线说明页（中英）：https://jack91124.github.io/ai-extension-manager/zh.html

想把 Windows 上的链接行为和冲突模型先交给你们骂一遍，尤其是同时用三个以上工具的人。

---

## awesome-list PR template

Find the list's "Skills" or "Tools" section and insert one line, keeping the list's alphabetical order:

```markdown
- [AI Extension Manager](https://github.com/Jack91124/ai-extension-manager) — One local library with
  SHA-256 state tracking and two-way sync for agent skills, rules and MCP configs across Claude Code,
  Codex, Gemini CLI, Cursor, VS Code Copilot and DSH; conflicts stop instead of overwriting.
```

PR title: `Add AI Extension Manager (cross-tool skill sync)`
PR body: one sentence on the problem, one on what is different (hash-based conflict detection, no silent
overwrites), the install line, and a note that the repo is MIT and test-covered. No marketing adjectives.

Candidate lists (verified active on 2026-11-26; still confirm each list accepts tool/manager PRs before opening):

- https://github.com/hesreallyhim/awesome-claude-code (58k stars, active)
- https://github.com/Punkpeye/awesome-mcp-servers (98k stars, active; only if the list covers managers, not servers)
- https://github.com/sickn33/agentic-awesome-skills (50k stars, active, has a Contributing section; explicitly covers Claude Code, Codex, Cursor, Gemini CLI)
- https://github.com/VoltAgent/awesome-agent-skills (37k stars, CONTRIBUTING.md welcomes contributions)
- https://github.com/github/awesome-copilot (41k stars, has CONTRIBUTING.md; best fit for the Copilot angle)
- https://github.com/e2b-dev/awesome-ai-agents (31k stars, but last push 2026-08-21 — lower priority)

## Rules for all posts

- Post from a personal account; say "I built this", never "we".
- One link per post. No UTM parameters, no affiliate links.
- Answer every reply for the first two hours; that is where the stars actually come from.
- Never claim the DSH plugin exists, and never call it a "manager for everything" — it manages skills,
  rules and MCP configs, and it says so.
