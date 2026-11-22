#!/usr/bin/env python3
"""scan_agents.py - detect the supported AI tools and their resource locations.

Contract:
  input : --home, --workspace, --agent <id> (repeatable), --json
  output: {ok, generated_at, agents:[...], summary:{...}}
  exit  : 0 normally (absent tools are data, not errors)
"""

from __future__ import annotations
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core


def main(argv=None) -> int:
    parser = core.common_parser("Detect supported AI tools, versions and resource directories")
    parser.add_argument("--agent", action="append", default=None,
                        help="limit to one agent id (repeatable): dsh, codex, claude, gemini, cursor, copilot")
    parser.add_argument("--require", default=None,
                        help="exit 1 unless this agent id is installed")
    args = parser.parse_args(argv)
    home = core.Home(args.home)  # read-only scan: no library creation
    workspace = core.workspace_path(args)
    requested = args.agent or None
    agents = core.resolve_agents(home, requested)
    if requested:
        known = {agent["id"] for agent in core.resolve_agents(home)}
        unknown = [agent_id for agent_id in requested if agent_id not in known]
        if unknown:
            result = {"ok": False, "error": "unknown agent id(s): " + ", ".join(unknown),
                      "known": sorted(known)}
            core.output(result, args)
            return 1
    detected = [core.detect_agent(agent, workspace) for agent in agents]
    summary = {
        "total": len(detected),
        "installed": sum(1 for item in detected if item["status"] == "installed"),
        "config_only": sum(1 for item in detected if item["status"] == "config-only"),
        "absent": sum(1 for item in detected if item["status"] == "absent"),
        "skills_visible": sum(sum(skill["skill_count"] for skill in item["skills"]) for item in detected),
    }
    result = {"ok": True, "generated_at": core.utcnow(), "home": str(home.root),
              "workspace": str(workspace) if workspace else None,
              "agents": detected, "summary": summary}
    lines = ["AI tool status (" + core.utcnow() + ")"]
    for item in detected:
        flag = {"installed": "[+]", "config-only": "[~]", "absent": "[ ]"}.get(item["status"], "[?]")
        version = " " + item["cli_version"] if item["cli_version"] else ""
        lines.append(flag + " " + item["label"] + " (" + item["id"] + ") " + item["status"] + version)
        for skill_dir in item["skills"]:
            mark = "ok" if skill_dir["exists"] else "--"
            scope = skill_dir["scope"]
            if scope == "workspace" and workspace is None:
                continue
            lines.append("    " + scope + " " + mark + " " + skill_dir["path"] +
                         "  skills=" + str(skill_dir["skill_count"]))
        for note in item["notes"][:2]:
            lines.append("    note: " + note)
    lines.append("summary: " + core.pj(summary).replace("\n", " "))
    core.output(result, args, lines)
    if args.require:
        target = next((item for item in detected if item["id"] == args.require), None)
        if not target or target["status"] == "absent":
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
