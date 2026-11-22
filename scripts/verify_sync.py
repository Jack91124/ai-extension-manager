#!/usr/bin/env python3
"""verify_sync.py - verify that installed copies still match the central library.

Checks every recorded target (or a selected resource/agent pair):
  ok          content hash matches the library
  drifted     files changed, added or removed in the target
  missing     target directory / config file / server entry is gone
  corrupted   link points somewhere unexpected or the file is unreadable
  unmanaged   a skill exists in a tool but not in the library (with --include-unmanaged)
Exit code: 0 all verified, 1 any problem, 2 only unmanaged findings (strict mode).
"""

from __future__ import annotations
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core


def agent_skills_by_name(agent: dict, workspace, scope: str) -> dict:
    detected = core.detect_agent(agent, workspace)
    found = {}
    for skill_dir in detected["skills"]:
        if skill_dir["scope"] != scope or not skill_dir["exists"]:
            continue
        path = Path(skill_dir["path"])
        if not path.is_dir():
            continue
        for child in path.iterdir():
            try:
                if child.is_dir() and (child / "SKILL.md").exists():
                    found[child.name] = str(child)
            except OSError:
                continue
    return found


def main(argv=None) -> int:
    parser = core.common_parser("Verify that agent copies match the central library")
    parser.add_argument("--resource", action="append", default=None, help="resource id or name (repeatable)")
    parser.add_argument("--agent", action="append", default=None, help="agent id (repeatable)")
    parser.add_argument("--all", action="store_true", help="verify every recorded target")
    parser.add_argument("--scope", default="user", choices=["user", "workspace"])
    parser.add_argument("--include-unmanaged", action="store_true",
                        help="also list skills present in a tool but not in the library")
    parser.add_argument("--strict", action="store_true", help="treat unmanaged resources as failures")
    args = parser.parse_args(argv)
    home = core.resolve_home(args)
    workspace = core.workspace_path(args)
    records = []
    if args.resource:
        for wanted in args.resource:
            record = home.find_resource(wanted)
            if record:
                records.append(record)
            else:
                results_error = {"ok": False, "error": "resource not found: " + wanted}
                core.output(results_error, args)
                return 1
    else:
        records = home.resources()
    agent_configs = core.load_agent_configs(home)
    checks = []
    for record in records:
        targets = record.get("targets") or {}
        if args.agent:
            agent_ids = args.agent
        elif args.all or not targets:
            agent_ids = list(targets.keys())
        else:
            agent_ids = list(targets.keys())
        for agent_id in agent_ids:
            agent = agent_configs.get(agent_id)
            if agent is None:
                checks.append({"resource": record["id"], "agent": agent_id,
                               "status": "unknown-agent"})
                continue
            if agent_id not in targets and not args.all:
                continue
            checks.append(core.verify_target(home, record, agent, workspace, args.scope))
    unmanaged = []
    if args.include_unmanaged:
        for agent_id, agent in agent_configs.items():
            if args.agent and agent_id not in args.agent:
                continue
            visible = agent_skills_by_name(agent, workspace, args.scope)
            for name, path in visible.items():
                if home.find_resource(name) is None:
                    unmanaged.append({"agent": agent_id, "skill": name, "path": path})
    summary = core.summarize_counts(checks, "status")
    problems = [check for check in checks if check["status"] not in ("ok", "unavailable")]
    result = {"ok": not problems and not (args.strict and unmanaged), "checks": checks,
              "summary": summary, "unmanaged": unmanaged,
              "problems": len(problems), "unmanaged_count": len(unmanaged)}
    lines = ["Verify sync (" + str(len(checks)) + " checks)"]
    for check in checks:
        line = "  " + str(check.get("agent")).ljust(8) + " " + str(check.get("resource")).ljust(34) + " " + str(check.get("status"))
        if check.get("detail"):
            line += "  " + str(check["detail"])
        if check.get("missing"):
            line += "  missing=" + str(check["missing"][:4])
        if check.get("changed"):
            line += "  changed=" + str(check["changed"][:4])
        lines.append(line)
    for item in unmanaged[:40]:
        lines.append("  " + item["agent"].ljust(8) + " unmanaged skill: " + item["skill"])
    lines.append("summary: " + core.pj(summary).replace("\n", " "))
    if unmanaged:
        lines.append("unmanaged resources: " + str(len(unmanaged)))
    core.output(result, args, lines)
    if problems:
        return 1
    if args.strict and unmanaged:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
