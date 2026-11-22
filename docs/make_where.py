#!/usr/bin/env python3
"""Generate docs/where.html + docs/llms.txt from the agent registry in aem_core.

Nothing here is hand-maintained: paths, plugin mechanisms, MCP config files and
verification levels are read from scripts/aem_core.py, so the public page and the
scanner can never disagree.
"""

from __future__ import annotations
import html
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aem_core as core

E = lambda value: html.escape(str(value), quote=True)

VERIFY = {
    "local": ("ok", "verified locally"),
    "official+local": ("ok", "official docs + local"),
    "official+partial": ("partial", "official docs"),
    "partial": ("partial", "partial"),
    "none": ("partial", "unverified"),
}


def pills(agent):
    kind, text = VERIFY.get(agent.get("verification") or "none", VERIFY["none"])
    return "<span class=\"pill %s\">%s</span>" % (kind, E(text))


def paths_html(items, empty="—"):
    items = [item for item in items or [] if item]
    if not items:
        return empty
    return "<br>".join("<code>%s</code>" % E(item) for item in items)


def plugin_text(agent):
    plugin = agent.get("plugin") or {}
    supported = plugin.get("supported") or "unsupported"
    system = plugin.get("system") or ""
    if supported == "unsupported":
        return "no plugin mechanism"
    if supported == "unverified":
        return "%s (unverified CLI path)" % system
    return system.replace("-", " ")


def mcp_html(agent):
    configs = (agent.get("mcp") or {}).get("configs") or []
    if not configs:
        notes = (agent.get("mcp") or {}).get("notes") or "no standalone config file"
        return "<span class=\"dim\">%s</span>" % E(notes)
    seen, out = set(), []
    for item in configs:
        path = item.get("path")
        if not path or path in seen:
            continue
        seen.add(path)
        out.append("<code>%s</code>" % E(path))
    return "<br>".join(out)


def table_rows(agents):
    rows = []
    for agent in agents:
        skills = agent.get("skills") or {}
        rows.append(
            "<tr><td><b>%s</b><div class=\"dim\">%s</div></td>"
            "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (E(agent["label"]), E(agent["id"]),
               paths_html(skills.get("user")).replace("<code>", "<code style=\"font-size:13px\">"),
               paths_html(skills.get("workspace")),
               mcp_html(agent),
               paths_html((agent.get("rules") or {}).get("paths")),
               E(plugin_text(agent)),
               pills(agent)))
    return "\n".join(rows)


def cards(agents):
    out = []
    for agent in agents:
        skills = agent.get("skills") or {}
        plugin = agent.get("plugin") or {}
        rules = agent.get("rules") or {}
        lines = [
            "<div class=\"card\">",
            "  <h3>%s %s</h3>" % (E(agent["label"]), pills(agent)),
            "  <h4>Skills — personal</h4><p>%s</p>" % paths_html(skills.get("user")),
            "  <h4>Skills — project</h4><p>%s</p>" % paths_html(skills.get("workspace")),
            "  <h4>MCP config</h4><p>%s</p>" % mcp_html(agent),
            "  <h4>Rules / instructions</h4><p>%s</p>" % paths_html(rules.get("paths")),
            "  <h4>Plugins</h4><p>%s</p>" % e_plugin(plugin),
        ]
        if agent.get("docs"):
            lines.append("  <p class=\"dim\">Source: <a href=\"%s\">%s</a></p>" % (E(agent["docs"]), E(agent["docs"])))
        lines.append("</div>")
        out.append("\n".join(lines))
    return "\n".join(out)


def e_plugin(plugin):
    text = plugin_text({"plugin": plugin})
    install = (plugin.get("install") or "").strip()
    if install:
        return "%s<br><code>%s</code>" % (E(text), E(install))
    return E(text)


def render(agents, generated_at):
    template = (Path(__file__).resolve().parent / "where.template.html").read_text(encoding="utf-8")
    return (template
        .replace("%%ROWS%%", table_rows(agents))
        .replace("%%CARDS%%", cards(agents))
        .replace("%%GENERATED%%", E(generated_at))
        .replace("%%TOOLCOUNT%%", str(len(agents))))


def llms_txt(agents, generated_at):
    lines = [
        "# AI Extension Manager (aem)",
        "",
        "Local-first CLI + agent skill that keeps skills, MCP servers and rules in sync",
        "across Claude Code, Codex, Gemini CLI, Cursor, VS Code Copilot and DSH.",
        "Two-way sync with SHA-256 state tracking, per-target backups, and conflicts",
        "that exit non-zero instead of overwriting. MIT, zero runtime dependencies.",
        "",
        "## Install",
        "",
        "- Skill (any agent that supports Agent Skills): `npx skills add Jack91124/ai-extension-manager`",
        "- CLI: `pip install git+https://github.com/Jack91124/ai-extension-manager` (then `aem --help`)",
        "",
        "## Where each tool keeps skills (generated from scripts/aem_core.py, %s)" % generated_at,
        "",
        "| Tool | Personal skills | Project skills | MCP config | Rules |",
        "| --- | --- | --- | --- | --- |",
    ]
    for agent in agents:
        skills = agent.get("skills") or {}
        rules = agent.get("rules") or {}
        mcp = (agent.get("mcp") or {}).get("configs") or []
        lines.append("| %s | %s | %s | %s | %s |" % (
            agent["label"],
            "<br>".join(skills.get("user") or []),
            "<br>".join(skills.get("workspace") or []),
            "<br>".join(item.get("path", "") for item in mcp) or "via plugins",
            "<br>".join(rules.get("paths") or []),
        ))
    lines += [
        "",
        "## Pages",
        "",
        "- Home / demo: https://jack91124.github.io/ai-extension-manager/",
        "- Chinese home: https://jack91124.github.io/ai-extension-manager/zh.html",
        "- Where skills live: https://jack91124.github.io/ai-extension-manager/where.html",
        "- Source: https://github.com/Jack91124/ai-extension-manager",
        "- skills.sh listing: https://www.skills.sh/jack91124/ai-extension-manager",
        "",
        "## When to use it",
        "",
        "- A skill exists in one tool and you want it in the others without clobbering edits.",
        "- You edited a copy in another tool and want it back in the library without losing either side.",
        "- You want an honest inventory of where each tool stores skills, rules and MCP config.",
    ]
    return "\n".join(lines) + "\n"


def main():
    registry = core.default_agent_configs()
    order = ["claude", "codex", "gemini", "cursor", "copilot", "dsh"]
    agents = [registry[key] for key in order if key in registry]
    agents += [item for key, item in registry.items() if key not in order]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = Path(__file__).resolve().parent
    (out_dir / "where.html").write_text(render(agents, generated_at), encoding="utf-8")
    (out_dir / "llms.txt").write_text(llms_txt(agents, generated_at), encoding="utf-8")
    print("wrote", out_dir / "where.html", "and", out_dir / "llms.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())