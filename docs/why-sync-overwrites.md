# Your AI tools each have a skills folder. Last-write-wins will eat your work.

*A shorter version of this is what I post when announcing the project. The long version exists because
"just copy the files" keeps being the default advice, and it is wrong in a specific, predictable way.*

## The setup

Six tools, six folders, one skill you want everywhere:

```text
Claude Code      ~/.claude/skills/
OpenAI Codex     ~/.codex/skills/        (also ~/.agents/skills/)
Gemini CLI       ~/.gemini/skills/
Cursor           ~/.cursor/skills/
VS Code Copilot  ~/.copilot/skills/      (workspace: .github/skills/)
DSH              ~/.dsh/skills/
```

Every tool invented its own location, its own metadata and its own install story. So the same skill
gets copied six times. Then you fix a typo in the Claude copy. A week later a helper script "syncs"
the folders and picks the Codex copy because its mtime is newer. Your fix is gone, silently.

This is not a hypothetical failure mode. It is the default outcome of the only two strategies most
people use: copy in one direction, or symlink everything and hope.

## Why "newest file wins" is not a conflict policy

mtime is not evidence of intent. It changes when:

- a tool rewrites a file after reading it;
- you restore from a backup;
- a sync itself touches the destination;
- your filesystem normalises timestamps and the copy happens to look newer.

All four produce the same wrong conclusion: "the newest copy is the one the user wants." A conflict
system needs to answer a different question first: **what did each side know when they last agreed?**

## The three facts that make sync decidable

`aem` stores, for every resource and every target:

1. **the library's content hash** (SHA-256 over the file tree, not just one file);
2. **the hash this target was synced from** (`source_hash`);
3. **the hash the target received** (`target_hash`), plus `synced_at`.

With those three values you can classify every situation without guessing:

| State | What actually happened | Default action |
|---|---|---|
| **A** | only the library changed | update the target, after a backup |
| **B** | only the target changed | keep the target, offer to import it |
| **C** | both sides changed | **write nothing, exit code 2**, save the conflict evidence |
| **D** | the target was deleted | report it; do not silently recreate |
| **E** | the target directory does not exist | report unavailable; do not invent a path |
| untracked | a copy exists that was never synced | identical → adopt; different → conflict |

State C is the entire point. It is the case where every mtime-based script destroys something. A
tool that refuses to act is more useful than one that guesses.

```
$ aem sync --direction distribute --agent claude --resource my-skill
Sync distribute (1 step)
  claude   skill/my-skill                   conflict [C]  both sides changed
summary: {   "conflict": 1 }
conflicts were left untouched; use compare_resources.py and resolve them explicitly
```

Resolution is explicit, and every option is reversible:

```bash
aem compare --left resource:my-skill --right agent:claude:my-skill --diff   # see the actual diff
aem sync --direction distribute --agent claude --resource my-skill --on-conflict library
aem sync --direction import    --agent claude --resource my-skill --on-conflict new-version
aem restore --resource my-skill --version <label>
```

## "Why not just symlink the folder?"

Symlinks are a fine tool and `aem` supports them (`--mode link`, directory junctions on Windows),
but they are not a sync policy:

- Some tools rewrite files in place while loading them, which edits the source through the link.
- A link shares one physical copy, so per-tool edits become global edits with no record of who changed
  what — the exact problem this is trying to solve.
- Backups and rollback become ambiguous: what does "restore the Claude copy" mean when it is a link?
- Windows symlinks need developer mode or elevation; junctions work but only for directories on the
  same volume, and not every tool follows them.

Copy plus state tracking costs a few kilobytes and buys classification, diffs and rollback.

## What it deliberately does not do

Honesty is part of the design, so the README's support matrix says this out loud:

- **Plugins are not copied across tools.** Vendor plugins are installed by the vendor's own mechanism
  (`dsh plugin add`, `claude plugin`, `gemini extensions install`, the VS Code marketplace). `aem`
  returns the exact command and refuses cross-tool moves for tool-specific plugins.
- **Secrets are never synced.** MCP configs are merged, but credentials are refused or rewritten to
  `${ENV_VAR}` placeholders before anything is stored.
- **Not every adapter is runtime-verified.** Claude Code, Codex and DSH were exercised on the machine
  this was built on; Gemini CLI and Cursor paths come from vendor docs and are marked *partial*.
  CI tests the CLI against fake homes, not the tools themselves.

## Try it in 60 seconds

```bash
npx skills add Jack91124/ai-extension-manager     # or: pip install --user "git+...@v1.0.12"
aem scan                     # where are the six tools on this machine?
aem adopt                    # pull new/changed skills from every tool into one library
aem distribute --agent claude --agent codex --resource my-skill
aem verify --all             # prove every copy still matches the library
```

No account, no server, no telemetry, no dependencies. Python 3.9+. MIT.

Repository: <https://github.com/Jack91124/ai-extension-manager>

---

## 中文摘要

六个 AI 编程工具各自一套 Skill 目录，同一个技能被复制六份，然后在不同地方被改。常见的「同步
脚本」按修改时间判断谁新，于是你在 Claude 里修的那处改动，会在下一次同步时被 Codex 的旧副本
静默覆盖——这是必然结果，不是意外。

`aem` 的思路是记录三件事：中央库的内容哈希、每个目标「从哪个哈希同步过来」、以及同步时间。
由此可以把情况分成 A（只有库变，备份后更新目标）、B（只有工具变，反向导入）、C（两边都变，
**报冲突、退出码 2、一个字都不写**）、D（目标被删除）、E（目标目录不存在），而不是猜谁更新。

冲突不会自动解决：`aem compare` 给出逐文件 diff，然后你显式选择保留库、保留目标、或把目标
存为新版本；所有分发前都有备份，`aem restore` 可回滚任意历史版本。

它也不假装全能：插件不由它跨工具复制（交给各工具自己的安装机制），密钥不同步（MCP 配置里的
凭据会被拒绝或替换成 `${ENV_VAR}`），Gemini CLI 与 Cursor 的路径来自官方文档、标注为
partial，尚未在真机运行时验证。

安装：`npx skills add Jack91124/ai-extension-manager` 或 pip 从 git 安装；零依赖，Python 3.9+。
