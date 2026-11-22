#!/usr/bin/env python3
"""aem - one command line for the AI Extension Manager.

The seven task scripts stay the implementation; this module is the stable,
memorable entry point (and the thing a package installs as 'aem').

Commands
  aem init                     create the central library
  aem doctor                   diagnose Python, paths, registry, locks, tools
  aem status                   one table: resource x agent sync state
  aem scan | agents            detect AI tools and their resource directories
  aem detect | inspect         classify a path / URL / installed resources
  aem import | add             import skill / plugin / MCP / rules
  aem sync                     two-way sync (import, distribute, both)
  aem adopt                    import everything new from every tool (sync --direction import)
  aem distribute               push library resources to tools (sync --direction distribute)
  aem compare | diff           compare two copies
  aem verify                   verify installed copies against the library
  aem backup | restore | prune snapshots
  aem version                  print version

Exit codes: 0 success, 1 error or failed check, 2 conflict / difference.
"""

from __future__ import annotations
import argparse
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core

HELP = """aem - AI Extension Manager

Usage:
  aem init                      create the central library (~/.ai-extension-manager)
  aem doctor [--fix]            diagnose the local setup
  aem status [--agent ID]       show resource x agent sync state
  aem scan [--agent ID]         detect AI tools and directories
  aem detect --path PATH        classify a skill / plugin / MCP / rules
  aem import --source PATH      import a resource into the central library
  aem sync --direction both     two-way sync (import | distribute | both)
  aem adopt [--agent ID]        pull new/changed resources from tools into the library
  aem distribute [--agent ID]   push library resources to tools (backs up first)
  aem compare --left A --right B   compare two copies
  aem verify --all              verify installed copies
  aem backup backup --resource NAME
  aem backups                   list snapshots
  aem restore --resource NAME --version V
  aem prune --keep 10
  aem version

Global options accepted by every task command: --home PATH, --workspace PATH, --json.
Run "aem <command> --help" for the full option list.

Documentation: README.md and references/cli-reference.md
"""

# command -> (module, argument prefix).  A prefix lets one module expose
# several natural top-level commands (aem backups == backup_restore.py list).
# Options accepted both before and after a subcommand. Sub-parsers such as
# backup_restore only define them on the top-level parser, so move them first.
GLOBAL_FLAGS = ("--json",)
GLOBAL_VALUES = ("--home", "--workspace")


def reorder_globals(argv):
    front, rest, index = [], [], 0
    while index < len(argv):
        item = argv[index]
        if item in GLOBAL_FLAGS:
            front.append(item)
        elif item in GLOBAL_VALUES:
            front.append(item)
            if index + 1 < len(argv):
                front.append(argv[index + 1])
                index += 1
        else:
            rest.append(item)
        index += 1
    return front + rest


TASK_COMMANDS = {
    "scan": ("scan_agents", []),
    "agents": ("scan_agents", []),
    "detect": ("detect_resources", []),
    "inspect": ("detect_resources", []),
    "import": ("import_resource", []),
    "add": ("import_resource", []),
    "sync": ("sync_resources", []),
    "adopt": ("sync_resources", ["--direction", "import"]),
    "distribute": ("sync_resources", ["--direction", "distribute"]),
    "compare": ("compare_resources", []),
    "diff": ("compare_resources", []),
    "verify": ("verify_sync", []),
    "backup": ("backup_restore", ["backup"]),
    "backups": ("backup_restore", ["list"]),
    "list-backups": ("backup_restore", ["list"]),
    "restore": ("backup_restore", ["restore"]),
    "prune": ("backup_restore", ["prune"]),
}


def _writable(path: Path) -> bool:
    probe = path if path.exists() else path.parent
    try:
        if not probe.exists():
            return False
        return os.access(str(probe), os.W_OK)
    except OSError:
        return False


def _human(result: dict, lines: list, as_json: bool) -> None:
    if as_json:
        core.emit_json(result)
        return
    for line in lines:
        print(line)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def cmd_init(argv) -> int:
    parser = argparse.ArgumentParser(prog="aem init", description="Create the central resource library")
    parser.add_argument("--home", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    home = core.Home(args.home)
    existed = home.root.exists()
    registry_existed = home.registry_path.exists()
    home.ensure()
    result = {
        "ok": True,
        "home": str(home.root),
        "created": not existed,
        "initialized_registry": not registry_existed,
        "layout": {
            "library": str(home.library),
            "metadata": str(home.metadata),
            "backups": str(home.backups),
            "staging": str(home.staging),
            "conflicts": str(home.conflicts),
            "logs": str(home.logs),
        },
        "resources": len(home.resources()),
    }
    lines = [
        ("created " if not existed else "ready   ") + str(home.root),
        "library   " + str(home.library),
        "metadata  " + str(home.metadata),
        "backups   " + str(home.backups),
        "next: aem doctor; aem scan; aem import --source <path>",
    ]
    _human(result, lines, args.json)
    return 0


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

def _check(checks: list, ident: str, status: str, detail: str, fix: str | None = None) -> None:
    item = {"id": ident, "status": status, "detail": detail}
    if fix:
        item["fix"] = fix
    checks.append(item)


def cmd_doctor(argv) -> int:
    parser = argparse.ArgumentParser(prog="aem doctor", description="Diagnose the local AI Extension Manager setup")
    parser.add_argument("--home", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fix", action="store_true", help="create the library and remove a stale lock")
    args = parser.parse_args(argv)
    home = core.Home(args.home)
    checks: list = []

    py = platform.python_version()
    if sys.version_info >= (3, 9):
        _check(checks, "python", "ok", py + " (requires 3.9+)")
    else:
        _check(checks, "python", "fail", py + " is too old; install Python 3.9+")

    if not home.root.exists():
        _check(checks, "library", "warn", "not initialized: " + str(home.root),
               "run: aem init")
        if args.fix:
            home.ensure()
            _check(checks, "library", "ok", "created " + str(home.root))
    elif _writable(home.root):
        _check(checks, "library", "ok", str(home.root) + " is writable")
    else:
        _check(checks, "library", "fail", str(home.root) + " is not writable",
               "fix permissions or set AEM_HOME to a writable directory")

    if home.registry_path.exists():
        try:
            registry = json.loads(home.registry_path.read_text(encoding="utf-8"))
            resources = registry.get("resources")
            if not isinstance(resources, dict):
                raise ValueError("resources is not an object")
            _check(checks, "registry", "ok", str(len(resources)) + " resources")
            if registry.get("schema") != core.SCHEMA_VERSION:
                _check(checks, "schema", "warn",
                       "registry schema " + str(registry.get("schema")) +
                       " != " + str(core.SCHEMA_VERSION), "run: aem init (migration is not implemented yet)")
            else:
                _check(checks, "schema", "ok", "schema " + str(core.SCHEMA_VERSION))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            registry = {}
            _check(checks, "registry", "fail", "unreadable registry: " + str(exc),
                   "restore metadata/registry.json from a backup")
    else:
        registry = {}
        _check(checks, "registry", "warn", "no registry yet", "run: aem init")

    broken = []
    for record in (registry.get("resources") or {}).values():
        try:
            payload = core.payload_path(home, record)
        except Exception:
            payload = None
        if payload is None or not Path(payload).exists():
            broken.append(str(record.get("name") or record.get("id")))
    if broken:
        _check(checks, "payloads", "fail", str(len(broken)) + " resource payload(s) missing: " +
               ", ".join(broken[:5]), "run: aem verify --all and restore from backups")
    else:
        _check(checks, "payloads", "ok", "all payload directories present")

    lock = home.metadata / ".library.lock"
    if lock.exists():
        age = max(0, int(time.time() - lock.stat().st_mtime))
        if age > 3600:
            _check(checks, "lock", "warn", "stale lock is " + str(age) + "s old: " + str(lock),
                   "aem doctor --fix (only when no sync is running)")
            if args.fix:
                try:
                    lock.unlink()
                    _check(checks, "lock", "ok", "removed stale lock")
                except OSError as exc:
                    _check(checks, "lock", "fail", "cannot remove lock: " + str(exc))
        else:
            _check(checks, "lock", "ok", "active lock is " + str(age) + "s old")
    else:
        _check(checks, "lock", "ok", "no library lock")

    try:
        configs = core.resolve_agents(home)
        detected = [core.detect_agent(agent) for agent in configs]
        installed = [item for item in detected if item["status"] == "installed"]
        absent = [item["id"] for item in detected if item["status"] == "absent"]
        _check(checks, "agents", "ok" if installed else "warn",
               str(len(installed)) + "/" + str(len(detected)) + " tools installed; absent: " +
               (", ".join(absent) if absent else "none"))
    except Exception as exc:  # detection is best effort; never crash doctor
        _check(checks, "agents", "warn", "agent detection failed: " + str(exc))

    try:
        free = shutil.disk_usage(str(home.root if home.root.exists() else home.root.parent)).free
        status = "ok" if free > 100 * 1024 * 1024 else "warn"
        _check(checks, "disk", status, core.human_bytes(free) + " free")
    except OSError as exc:
        _check(checks, "disk", "warn", "cannot read free space: " + str(exc))

    backups = [entry for entry in home.backups.glob("*") if entry.is_dir()] if home.backups.exists() else []
    backup_bytes = 0
    for entry in backups:
        try:
            backup_bytes += core.tree_stats(core.tree_manifest(entry))["bytes"]
        except OSError:
            continue
    _check(checks, "backups", "ok", str(len(backups)) + " snapshots, " + core.human_bytes(backup_bytes))

    conflicts = [entry for entry in home.conflicts.glob("*") if entry.is_dir()] if home.conflicts.exists() else []
    _check(checks, "conflicts", "warn" if conflicts else "ok",
           str(len(conflicts)) + " unresolved conflict(s)")

    fails = [item for item in checks if item["status"] == "fail"]
    warns = [item for item in checks if item["status"] == "warn"]
    result = {"ok": not fails, "generated_at": core.utcnow(), "home": str(home.root),
              "checks": checks, "summary": {"ok": len(checks) - len(fails) - len(warns),
                                              "warn": len(warns), "fail": len(fails)}}
    lines = ["aem doctor - " + str(home.root), "python " + py]
    for item in checks:
        flag = {"ok": "[ok]  ", "warn": "[warn]", "fail": "[fail]"}.get(item["status"], "[?]   ")
        lines.append(flag + " " + item["id"].ljust(9) + " " + item["detail"])
        if item.get("fix") and item["status"] != "ok":
            lines.append("       fix: " + item["fix"])
    lines.append("result: " + ("healthy" if not fails else str(len(fails)) + " failure(s)"))
    _human(result, lines, args.json)
    return 0 if not fails else 1


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

STATUS_MAP = {
    "ok": "in-sync",
    "drifted": "changed",
    "missing": "missing",
    "corrupted": "corrupted",
    "unavailable": "unavailable",
    "manual": "manual",
    "unknown-agent": "unknown-agent",
}


def cmd_status(argv) -> int:
    parser = argparse.ArgumentParser(prog="aem status", description="Show resource x agent synchronization state")
    parser.add_argument("--home", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--scope", default="user", choices=["user", "workspace"])
    parser.add_argument("--agent", action="append", default=None, help="limit to an agent id (repeatable)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit 1 when any target is not in sync")
    args = parser.parse_args(argv)
    home = core.Home(args.home)
    workspace = core.workspace_path(args)
    rows = []
    if home.registry_path.exists():
        agent_configs = core.load_agent_configs(home)
        for record in sorted(home.resources(), key=lambda item: str(item.get("name") or "")):
            for agent_id, target in (record.get("targets") or {}).items():
                if args.agent and agent_id not in args.agent:
                    continue
                agent = agent_configs.get(agent_id)
                if agent is None:
                    rows.append({"resource": record.get("id"), "name": record.get("name"),
                                 "version": record.get("version"), "agent": agent_id,
                                 "status": "unknown-agent", "detail": "agent not in metadata/agents.json"})
                    continue
                check = core.verify_target(home, record, agent, workspace, args.scope)
                rows.append({
                    "resource": record.get("id"), "name": record.get("name"),
                    "version": record.get("version"), "agent": agent_id,
                    "status": STATUS_MAP.get(check.get("status"), check.get("status")),
                    "detail": check.get("detail"),
                    "path": check.get("path") or target.get("path"),
                })
    summary = core.summarize_counts(rows, "status")
    problems = [row for row in rows if row["status"] not in ("in-sync", "unavailable", "manual")]
    online = [row for row in rows if row["status"] == "in-sync"]
    result = {"ok": not problems, "generated_at": core.utcnow(), "home": str(home.root),
              "resources": len(home.resources()) if home.registry_path.exists() else 0,
              "rows": rows, "summary": summary, "problems": len(problems), "in_sync": len(online)}
    lines = ["aem status - " + str(home.root),
             "resources " + str(result["resources"]) + "   targets " + str(len(rows)) +
             "   in-sync " + str(len(online)) + "   problems " + str(len(problems))]
    if not rows:
        lines.append("nothing tracked yet: aem import --source <path>")
    else:
        lines.append("RESOURCE".ljust(30) + " VERSION".ljust(10) + " AGENT".ljust(9) + "STATUS")
        for row in rows:
            lines.append(str(row.get("name") or row["resource"]).ljust(30)[:30] +
                         " " + str(row.get("version") or "-").ljust(9) +
                         " " + row["agent"].ljust(8) + " " + row["status"] +
                         (("  " + str(row["detail"])) if row.get("detail") and row["status"] != "in-sync" else ""))
    _human(result, lines, args.json)
    return 0 if not (args.strict and problems) else 1


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

def cmd_version(argv) -> int:
    print("aem " + core.TOOL_VERSION + " (python " + platform.python_version() + ")")
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP)
        return 0
    command, rest = argv[0], argv[1:]
    if command in ("-v", "--version", "version"):
        return cmd_version(rest)
    if command == "init":
        return cmd_init(rest)
    if command == "doctor":
        return cmd_doctor(rest)
    if command == "status":
        return cmd_status(rest)
    if command in TASK_COMMANDS:
        module_name, prefix = TASK_COMMANDS[command]
        try:
            module = __import__(module_name)
        except ImportError as exc:
            print("aem: cannot load " + module_name + ": " + str(exc), file=sys.stderr)
            return 1
        try:
            code = module.main(reorder_globals(prefix + rest))
        except SystemExit as exc:  # argparse --help / usage errors
            code = exc.code
        return int(code or 0)
    print("aem: unknown command: " + command, file=sys.stderr)
    print("Run 'aem --help' for the command list.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
