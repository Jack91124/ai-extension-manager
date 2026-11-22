#!/usr/bin/env python3
"""aem - one command line for the AI Extension Manager.

The seven task scripts stay the implementation; this module is the stable,
memorable entry point (and the thing a package installs as 'aem').

Commands
  aem init                     create the central library
  aem doctor                   diagnose Python, paths, registry, locks, tools
  aem status                   one table: resource x agent sync state
  aem report                   single-file HTML dashboard of the library and its targets
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
  aem report [--out FILE]       write a single-file HTML dashboard (screenshot-friendly)
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
# report - a single-file HTML dashboard you can screenshot or commit
# ---------------------------------------------------------------------------

REPORT_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>aem report</title>
<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: #0a0e14; color: #d7e0ea;
  font: 15px/1.5 ui-sans-serif, -apple-system, "Segoe UI", system-ui, sans-serif; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 40px 24px 64px; }
header { display: flex; align-items: baseline; justify-content: space-between; gap: 16px;
  border-bottom: 1px solid #1d2733; padding-bottom: 18px; margin-bottom: 28px; }
.logo { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
.logo b { color: #5eead4; }
.meta { color: #7d8fa3; font-size: 13px; text-align: right; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; margin-bottom: 34px; }
.card { background: #101821; border: 1px solid #1d2733; border-radius: 12px; padding: 16px 18px; }
.card .n { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; }
.card .k { color: #7d8fa3; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }
.card.good .n { color: #5eead4; }
.card.warn .n { color: #fbbf24; }
.card.bad .n { color: #fb7185; }
h2 { font-size: 16px; letter-spacing: 0.04em; text-transform: uppercase; color: #9fb2c6;
  margin: 34px 0 12px; font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th { text-align: left; color: #7d8fa3; font-weight: 600; font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.06em; padding: 8px 10px; border-bottom: 1px solid #1d2733; }
td { padding: 9px 10px; border-bottom: 1px solid #131b25; vertical-align: top; }
tr:last-child td { border-bottom: none; }
.mono { font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; font-size: 12.5px; color: #93a4b8; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; }
.ok .dot { background: #34d399; } .drift .dot { background: #fbbf24; }
.miss .dot { background: #fb7185; } .muted .dot { background: #475569; }
.pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11.5px;
  border: 1px solid #243040; color: #a8bacd; }
.empty { color: #7d8fa3; padding: 14px 0; }
footer { margin-top: 44px; color: #55657a; font-size: 12.5px; border-top: 1px solid #1d2733; padding-top: 16px; }
code { font-family: ui-monospace, Consolas, monospace; color: #a5f3fc; }
</style></head><body><div class="wrap">
<header>
  <div class="logo"><b>aem</b> report</div>
  <div class="meta">[[HOME]]<br>generated [[GENERATED]] &middot; aem [[VERSION]]</div>
</header>
<div class="cards">[[CARDS]]</div>
<h2>Resources by type</h2>
[[TYPES]]
<h2>Tracked targets</h2>
[[TARGETS]]
<h2>Detected tools</h2>
[[AGENTS]]
<h2>Recent activity</h2>
[[EVENTS]]
<footer>Local-first: this file was generated from <code>metadata/registry.json</code>,
<code>metadata/agents.json</code> and <code>metadata/sync-history.json</code>. No network calls,
no telemetry. [[FOOTER_EXTRA]]</footer>
</div></body></html>
"""

REPORT_STATE = {
    "ok": ("in-sync", "ok"),
    "drifted": ("drifted", "drift"),
    "missing": ("missing", "miss"),
    "corrupted": ("corrupted", "miss"),
    "unavailable": ("unavailable", "muted"),
    "manual": ("manual", "muted"),
    "unknown-agent": ("unknown", "muted"),
}


def _esc(value) -> str:
    import html
    return html.escape(str(value if value is not None else ""), quote=True)


def _card(number, label, kind="") -> str:
    return ('<div class="card ' + kind + '"><div class="n">' + _esc(number) +
            '</div><div class="k">' + _esc(label) + "</div></div>")


def render_report(data: dict) -> str:
    cards = "".join([
        _card(data["resources"], "resources", "good" if data["resources"] else ""),
        _card(data["targets"], "tracked targets"),
        _card(data["in_sync"], "in sync", "good" if data["in_sync"] else ""),
        _card(data["problems"], "need attention", "bad" if data["problems"] else "good"),
    ])
    if data["types"]:
        rows = "".join(
            "<tr><td>" + _esc(kind) + '</td><td class="mono">' + _esc(count) + "</td></tr>"
            for kind, count in sorted(data["types"].items()))
        types = '<table><tr><th>Type</th><th>Resources</th></tr>' + rows + "</table>"
    else:
        types = '<div class="empty">No resources yet. Run <code>aem import --source &lt;path&gt;</code>.</div>'
    if data["rows"]:
        rows = []
        for row in data["rows"]:
            label, cls = REPORT_STATE.get(row["status"], (row["status"], "muted"))
            rows.append('<tr><td><span class="' + cls + '"><span class="dot"></span>' + _esc(row["name"]) +
                        '</span></td><td class="mono">' + _esc(row.get("version") or "-") +
                        '</td><td class="mono">' + _esc(row["agent"]) + '</td><td class="' + cls + '">' +
                        _esc(label) + '</td><td class="mono">' + _esc(row.get("path") or "") + "</td></tr>")
        targets = ('<table><tr><th>Resource</th><th>Version</th><th>Agent</th><th>State</th><th>Path</th></tr>'
                   + "".join(rows) + "</table>")
    else:
        targets = '<div class="empty">Nothing distributed yet. Run <code>aem distribute --agent codex</code>.</div>'
    if data["agents"]:
        rows = []
        for agent in data["agents"]:
            rows.append("<tr><td>" + _esc(agent["label"]) + '</td><td><span class="pill">' +
                        _esc(agent["status"]) + '</span></td><td class="mono">' + _esc(agent["detail"]) +
                        "</td></tr>")
        agents = '<table><tr><th>Tool</th><th>Status</th><th>Detail</th></tr>' + "".join(rows) + "</table>"
    else:
        agents = '<div class="empty">No tool configuration found.</div>'
    if data["events"]:
        rows = "".join('<tr><td class="mono">' + _esc(event.get("at")) + "</td><td>" + _esc(event.get("action")) +
                       '</td><td class="mono">' + _esc(event.get("subject") or "") +
                       "</td></tr>" for event in data["events"])
        events = '<table><tr><th>When (UTC)</th><th>Action</th><th>Subject</th></tr>' + rows + "</table>"
    else:
        events = '<div class="empty">No sync events recorded yet.</div>'
    html_text = (REPORT_TEMPLATE
                 .replace("[[HOME]]", _esc(data["home"]))
                 .replace("[[GENERATED]]", _esc(data["generated_at"]))
                 .replace("[[VERSION]]", _esc(data["version"]))
                 .replace("[[CARDS]]", cards)
                 .replace("[[TYPES]]", types)
                 .replace("[[TARGETS]]", targets)
                 .replace("[[AGENTS]]", agents)
                 .replace("[[EVENTS]]", events)
                 .replace("[[FOOTER_EXTRA]]", _esc(data.get("footer_extra") or "")))
    return html_text


def cmd_report(argv) -> int:
    parser = argparse.ArgumentParser(prog="aem report",
                                     description="Write a single-file HTML dashboard of the library and its targets")
    parser.add_argument("--home", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--scope", default="user", choices=["user", "workspace"])
    parser.add_argument("--out", default=None, help="output file (default: aem-report.html in the current directory)")
    parser.add_argument("--open", action="store_true", help="open the report in the default browser")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    home = core.Home(args.home)
    workspace = core.workspace_path(args)
    resources = home.resources() if home.registry_path.exists() else []
    configs = core.load_agent_configs(home)
    rows = []
    for record in sorted(resources, key=lambda item: str(item.get("name") or "")):
        for agent_id in sorted((record.get("targets") or {})):
            agent = configs.get(agent_id)
            if agent is None:
                rows.append({"name": record.get("name"), "version": record.get("version"),
                             "agent": agent_id, "status": "unknown-agent", "path": ""})
                continue
            check = core.verify_target(home, record, agent, workspace, args.scope)
            rows.append({"name": record.get("name"), "version": record.get("version"), "agent": agent_id,
                         "status": check.get("status") or "unavailable",
                         "path": check.get("path") or ""})
    problems = [row for row in rows if row["status"] not in ("ok", "unavailable", "manual")]
    in_sync = [row for row in rows if row["status"] == "ok"]
    agents = []
    for agent_id, agent in configs.items():
        try:
            detected = core.detect_agent(agent)
        except Exception as exc:  # detection is best effort
            detected = {"status": "unknown", "detail": str(exc)}
        detail = detected.get("path") or detected.get("detail") or ""
        agents.append({"id": agent_id, "label": agent.get("label") or agent_id,
                       "status": detected.get("status") or "unknown", "detail": detail})
    agents.sort(key=lambda item: (item["status"] != "installed", item["label"]))
    events = []
    for event in reversed(home.history().get("events") or []):
        subject = (event.get("resource_id") or event.get("agent") or
                   event.get("resource") or event.get("name") or "")
        if event.get("resource_id") and event.get("agent"):
            subject += " → " + str(event.get("agent"))
        events.append({"at": event.get("at"), "action": event.get("action"), "subject": subject})
        if len(events) >= 12:
            break
    conflicts = len([entry for entry in home.conflicts.glob("*") if entry.is_dir()]) if home.conflicts.exists() else 0
    backups = len([entry for entry in home.backups.glob("*") if entry.is_dir()]) if home.backups.exists() else 0
    generated = core.utcnow()
    data = {
        "home": str(home.root),
        "generated_at": generated,
        "version": core.TOOL_VERSION,
        "resources": len(resources),
        "targets": len(rows),
        "in_sync": len(in_sync),
        "problems": len(problems),
        "conflicts": conflicts,
        "backups": backups,
        "types": core.summarize_counts([{"type": record.get("type")} for record in resources], "type"),
        "rows": rows,
        "agents": agents,
        "events": events,
        "footer_extra": str(conflicts) + " open conflict(s), " + str(backups) + " backup snapshot(s)",
    }
    out = Path(args.out).expanduser() if args.out else Path.cwd() / "aem-report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(data), encoding="utf-8")
    result = dict(data)
    result["ok"] = True
    result["out"] = str(out)
    result["bytes"] = out.stat().st_size
    lines = [
        "aem report - " + str(home.root),
        "resources " + str(data["resources"]) + "   targets " + str(data["targets"]) +
        "   in-sync " + str(data["in_sync"]) + "   need attention " + str(data["problems"]),
        "wrote " + str(out) + " (" + core.human_bytes(result["bytes"]) + ")",
        "open it with: start " + str(out) + "   (or --open)",
    ]
    if args.open:
        try:
            import webbrowser
            webbrowser.open(out.resolve().as_uri())
        except Exception:
            pass
    _human(result, lines, args.json)
    return 0


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
    if command == "report":
        return cmd_report(rest)
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
