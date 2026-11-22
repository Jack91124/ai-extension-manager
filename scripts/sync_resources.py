#!/usr/bin/env python3
"""sync_resources.py - bidirectional synchronization engine.

Directions
  import      scan agent skill directories and pull new/changed skills into the library
  distribute  push library resources into one or more agents (skill copy/link, MCP merge, rules)
  both        import first, then distribute, per agent

Conflict policy (default skip):
  A  only the library changed        -> distribute updates the target after a backup
  B  only the target changed         -> import creates a new library version
  C  both changed                    -> conflict, nothing is overwritten (exit 2)
  D  target deleted                  -> distribute restores it
  E  target directory missing        -> reported, never created for an absent tool
  F  target copy without library     -> imported as a new resource (import direction)

The engine is idempotent: identical content is skipped without writes or backups.
A journal under staging/ makes interrupted runs resumable with --resume.
"""

from __future__ import annotations
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core
import import_resource as importer


def skills_in_dir(path: Path) -> list:
    found = []
    if not path.is_dir():
        return found
    for child in sorted(path.iterdir()):
        try:
            if child.is_dir() and (child / "SKILL.md").is_file():
                found.append(child)
        except OSError:
            continue
    return found


def journal_path(home, direction: str) -> Path:
    return home.staging / ("journal-" + direction + ".json")


def load_journal(home, direction: str, resume: bool) -> dict:
    path = journal_path(home, direction)
    if resume:
        data = core.read_json(path, None)
        if isinstance(data, dict):
            data.setdefault("steps_done", [])
            return data
    data = {"id": uuid.uuid4().hex[:8], "direction": direction, "started_at": core.utcnow(),
            "steps_done": [], "steps_failed": []}
    core.write_json_atomic(path, data)
    return data


def mark(journal: dict, home, key: str, ok: bool) -> None:
    if ok and key not in journal["steps_done"]:
        journal["steps_done"].append(key)
    elif not ok and key not in journal["steps_failed"]:
        journal["steps_failed"].append(key)
    core.write_json_atomic(journal_path(home, journal["direction"]), journal)


def import_ctx(args, extra: dict) -> dict:
    ctx = {
        "on_conflict": "new-version", "force": False, "allow_risk": False,
        "allow_secrets": False, "dry_run": args.dry_run, "type": "skill",
        "server": None, "ref": None, "depth": 3, "kinds": None,
        "workspace": core.workspace_path(args), "platform": "local-agent",
        "source_url": None, "source_path": None,
    }
    ctx.update(extra)
    return ctx


def run_import(home, agents, workspace, scope, journal, args, resume) -> list:
    results = []
    for agent in agents:
        detected = core.detect_agent(agent, workspace)
        if detected["status"] == "absent":
            results.append({"direction": "import", "agent": agent["id"], "action": "skipped",
                            "reason": "tool not installed"})
            continue
        for skill_dir in detected["skills"]:
            if skill_dir["scope"] != scope:
                continue
            if not skill_dir["exists"]:
                continue
            for path in skills_in_dir(Path(skill_dir["path"])):
                key = "import:" + agent["id"] + ":" + str(path).lower()
                if resume and key in journal["steps_done"]:
                    results.append({"direction": "import", "agent": agent["id"], "action": "skipped",
                                    "resource": path.name, "reason": "journal says this step already completed"})
                    continue
                result = import_one_skill(home, agent, path, skill_dir, args)
                result["direction"] = "import"
                results.append(result)
                if not args.dry_run:
                    mark(journal, home, key, result.get("action") not in ("error", "conflict"))
    return results


def import_one_skill(home, agent, path: Path, skill_dir: dict, args) -> dict:
    validation = core.validate_skill_dir(path)
    name = validation.get("name") or path.name
    existing = home.find_resource(name)
    actual_hash = core.tree_hash(path)
    if existing is None:
        prepared = importer.prepare_skill(path, {"force": False, "allow_risk": False})
        if prepared.get("status") != "ready":
            return {"agent": agent["id"], "resource": name, "action": "rejected",
                    "reason": prepared.get("reason"), "path": str(path)}
        ctx = import_ctx(args, {"source_path": str(path), "source_url": None})
        outcome = importer.apply_import(home, prepared, ctx)
        if outcome.get("status") in ("imported", "updated"):
            record = home.get_resource(outcome.get("id") or "")
            if record is not None:
                record_target_from_import(home, record, agent, path, skill_dir)
        status = outcome.get("status")
        mapped = {"imported": "imported", "duplicate": "skip", "conflict": "conflict",
                  "needs-confirmation": "needs-confirmation", "secret-detected": "rejected",
                  "invalid": "rejected"}.get(status, status)
        return {"agent": agent["id"], "resource": name, "action": mapped,
                "reason": outcome.get("reason"), "id": outcome.get("id"),
                "safety": outcome.get("safety"), "scope": skill_dir["scope"]}
    if exists_identical(existing, actual_hash, path):
        record_target_from_import(home, existing, agent, path, skill_dir)
        return {"agent": agent["id"], "resource": name, "action": "skip",
                "reason": "target and library already identical", "id": existing["id"],
                "scope": skill_dir["scope"]}
    state = core.compute_target_state(existing, (existing.get("targets") or {}).get(agent["id"]),
                                      actual_hash, True)
    if state["state"] == "B":
        if args.dry_run:
            return {"agent": agent["id"], "resource": name, "action": "would-import",
                    "reason": "target changed since last sync", "id": existing["id"]}
        prepared = importer.prepare_skill(path, {"force": False, "allow_risk": False})
        if prepared.get("status") != "ready":
            return {"agent": agent["id"], "resource": name, "action": "rejected",
                    "reason": prepared.get("reason")}
        ctx = import_ctx(args, {"source_path": str(path), "on_conflict": "new-version"})
        outcome = importer.apply_import(home, prepared, ctx)
        record = home.get_resource(outcome.get("id") or "")
        if record is not None:
            record_target_from_import(home, record, agent, path, skill_dir)
        return {"agent": agent["id"], "resource": name, "action": "imported-update",
                "reason": "target changed only (state B)", "id": outcome.get("id"),
                "version": outcome.get("version"), "safety": outcome.get("safety")}
    if state["state"] == "A":
        return {"agent": agent["id"], "resource": name, "action": "skip",
                "reason": "library is ahead of this target; use --direction distribute",
                "id": existing["id"]}
    if state["state"] == "C" and args.on_conflict in ("keep-source", "new-version", "target"):
        prepared = importer.prepare_skill(path, {"force": False, "allow_risk": False})
        if prepared.get("status") != "ready":
            return {"agent": agent["id"], "resource": name, "action": "rejected",
                    "reason": prepared.get("reason")}
        ctx = import_ctx(args, {"source_path": str(path), "on_conflict": "new-version"})
        outcome = importer.apply_import(home, prepared, ctx)
        record = home.get_resource(outcome.get("id") or "")
        if record is not None:
            record_target_from_import(home, record, agent, path, skill_dir)
        return {"agent": agent["id"], "resource": name, "action": "imported-update",
                "reason": "state C resolved by keeping the target as a new library version",
                "state": state["state"], "id": outcome.get("id"), "version": outcome.get("version")}
    info = dict(state, target={"path": str(path), "hash": actual_hash})
    if args.dry_run:
        return {"agent": agent["id"], "resource": name, "action": "would-conflict",
                "state": state["state"], "reason": state["description"], "id": existing["id"]}
    core.record_conflict(home, existing, agent, info)
    return {"agent": agent["id"], "resource": name, "action": "conflict",
            "state": state["state"], "reason": state["description"], "id": existing["id"],
            "target": str(path)}


def exists_identical(existing, actual_hash, path: Path) -> bool:
    return existing.get("hash") == actual_hash


def record_target_from_import(home, record, agent, path: Path, skill_dir: dict) -> None:
    record.setdefault("targets", {})[agent["id"]] = {
        "agent": agent["id"], "scope": skill_dir["scope"], "path": str(path),
        "mode": "copy", "source_hash": record["hash"], "target_hash": record["hash"],
        "version": record.get("version"), "synced_at": core.utcnow(), "last_action": "adopt-on-import",
    }
    home.upsert_resource(record)


def select_resources(home, args) -> list:
    records = home.resources()
    if args.resource:
        selected = []
        for wanted in args.resource:
            record = home.find_resource(wanted)
            if record is None:
                continue
            selected.append(record)
        return selected
    return records


def run_distribute(home, agents, workspace, scope, journal, args, resume) -> list:
    results = []
    records = select_resources(home, args)
    if args.resource and not records:
        return [{"direction": "distribute", "action": "error",
                 "reason": "no resource matched: " + ", ".join(args.resource)}]
    for record in records:
        if args.resource is None and record.get("status") not in ("active", None):
            continue
        for agent in agents:
            key = "distribute:" + record["id"] + ":" + agent["id"]
            if resume and key in journal["steps_done"]:
                results.append({"direction": "distribute", "agent": agent["id"],
                                "resource": record["id"], "action": "skipped",
                                "reason": "journal says this step already completed"})
                continue
            if args.resource is None:
                detected = core.detect_agent(agent, workspace)
                if detected["status"] == "absent":
                    continue
            outcome = core.install_payload(
                home, record, agent, workspace=workspace, scope=scope, mode=args.mode,
                on_conflict=args.on_conflict, dry_run=args.dry_run, force=args.force,
            )
            outcome.update({"direction": "distribute", "resource": record["id"],
                            "agent": agent["id"]})
            results.append(outcome)
            if not args.dry_run:
                mark(journal, home, key, outcome.get("action") not in ("error", "conflict"))
    return results


def main(argv=None) -> int:
    parser = core.common_parser("Bidirectional sync between the central library and AI tools")
    parser.add_argument("--direction", default="both", choices=["import", "distribute", "both"])
    parser.add_argument("--agent", action="append", default=None, help="agent id (repeatable)")
    parser.add_argument("--all-agents", action="store_true", help="all six supported agents (default)")
    parser.add_argument("--resource", action="append", default=None, help="resource id or name (repeatable)")
    parser.add_argument("--all", action="store_true", help="all library resources (default for distribute)")
    parser.add_argument("--scope", default="user", choices=["user", "workspace"])
    parser.add_argument("--mode", default="copy", choices=["copy", "link"])
    parser.add_argument("--on-conflict", default="skip",
                        choices=["skip", "library", "target", "overwrite", "keep-source", "new-version"],
                        help="skip (default) | library/overwrite (target is stale) | "
                             "target/keep-source/new-version (target is authoritative, import it)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="overwrite state B/C targets (dangerous)")
    parser.add_argument("--resume", action="store_true", help="resume an interrupted run via its journal")
    parser.add_argument("--keep-journal", action="store_true", help="do not delete the journal on success")
    args = parser.parse_args(argv)
    if args.mode == "link" and args.direction != "distribute":
        parser.error("--mode link only applies to --direction distribute")
    home = core.resolve_home(args)
    workspace = core.workspace_path(args)
    requested = args.agent
    agents = core.resolve_agents(home, requested)
    if requested:
        known = {agent["id"] for agent in core.resolve_agents(home)}
        unknown = [agent_id for agent_id in requested if agent_id not in known]
        if unknown:
            core.output({"ok": False, "error": "unknown agent id(s): " + ", ".join(unknown)}, args)
            return 1
    results = []
    with core.library_lock(home, "library"):
        if args.direction in ("import", "both"):
            journal = load_journal(home, "import", args.resume)
            results.extend(run_import(home, agents, workspace, args.scope, journal, args, args.resume))
            if not args.keep_journal:
                core.remove_tree(journal_path(home, "import"))
        if args.direction in ("distribute", "both"):
            journal = load_journal(home, "distribute", args.resume)
            results.extend(run_distribute(home, agents, workspace, args.scope, journal, args, args.resume))
            if not args.keep_journal:
                core.remove_tree(journal_path(home, "distribute"))
    summary = core.summarize_counts(results, "action")
    conflicts = [item for item in results if item.get("action") in ("conflict", "would-conflict")]
    errors = [item for item in results if item.get("action") in
              ("error", "rejected", "unavailable", "needs-confirmation")]
    manual = [item for item in results if item.get("action") == "manual"]
    result = {"ok": not errors and not conflicts, "direction": args.direction,
              "results": results, "summary": summary,
              "conflicts": len(conflicts), "errors": len(errors), "manual": len(manual)}
    lines = ["Sync " + args.direction + " (" + str(len(results)) + " steps)"]
    for item in results:
        agent = item.get("agent") or "?"
        resource = item.get("resource") or ""
        action = item.get("action") or "?"
        line = "  " + agent.ljust(8) + " " + resource.ljust(34) + " " + action
        if item.get("state"):
            line += " [" + str(item["state"]) + "]"
        if item.get("reason"):
            line += "  " + str(item["reason"])
        lines.append(line)
        if item.get("install"):
            lines.append("      manual: " + str(item["install"]))
    lines.append("summary: " + core.pj(summary).replace("\n", " "))
    if conflicts:
        lines.append("conflicts were left untouched; use compare_resources.py and resolve them explicitly")
    core.output(result, args, lines)
    if conflicts:
        return 2
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
