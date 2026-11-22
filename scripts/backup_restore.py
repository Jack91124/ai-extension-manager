#!/usr/bin/env python3
"""backup_restore.py - versioned backups and restores for the central library.

Subcommands:
  backup  --resource <id|name> [--agent <id>]     snapshot a library resource or agent copy
  list    [--resource <id|name>]                  list snapshots newest first
  restore --backup-id <id> [--to library|agent]   restore a snapshot (undoable)
          --resource <id|name> --version <label>  restore a stored library version
  prune   --keep <n>                              delete old snapshots, keep newest n

Global options (--home/--workspace/--json) go before the subcommand.
"""

from __future__ import annotations
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core


def find_backup(home, backup_id: str):
    path = home.backups / backup_id
    return path, core.read_json(path / "manifest.json", None)


def list_backups(home, resource=None) -> list:
    items = []
    if not home.backups.exists():
        return items
    for entry in sorted(home.backups.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        manifest = core.read_json(entry / "manifest.json", None)
        if not isinstance(manifest, dict):
            continue
        if resource:
            resource_id = str(manifest.get("resource_id") or "")
            if resource not in (resource_id, resource_id.split("/")[-1]):
                continue
        items.append(manifest)
    return items


def cmd_backup(home, args) -> int:
    record = home.find_resource(args.resource)
    if record is None:
        core.output({"ok": False, "error": "resource not found: " + args.resource}, args)
        return 1
    if args.agent:
        agent = core.load_agent_configs(home).get(args.agent)
        if agent is None:
            core.output({"ok": False, "error": "unknown agent: " + args.agent}, args)
            return 1
        target = core.target_for(record, agent, core.workspace_path(args), args.scope)
        if not target.get("ok") or not target["path"].exists():
            core.output({"ok": False, "error": "target not found: " + str(target.get("reason") or target.get("path"))}, args)
            return 1
        entry = core.backup_target(home, args.agent, record, target["path"], "manual")
    else:
        payload = core.payload_path(home, record)
        if not payload.exists():
            core.output({"ok": False, "error": "library payload missing: " + str(payload)}, args)
            return 1
        entry = core.backup_target(home, "library", record, payload, "manual")
    core.output({"ok": True, "backup": entry}, args,
                ["backup created: " + entry["backup_id"], "  resource: " + record["id"],
                 "  path: " + str(home.backups / entry["backup_id"])])
    return 0


def cmd_list(home, args) -> int:
    items = list_backups(home, args.resource)
    lines = ["Backups: " + str(len(items))]
    for item in items:
        lines.append("  " + item["backup_id"] + "  " + str(item.get("resource_id")) +
                     "  agent=" + str(item.get("agent")) + "  reason=" + str(item.get("reason")))
    core.output({"ok": True, "backups": items, "count": len(items)}, args, lines)
    return 0


def restore_library(home, record, source: Path, label: str, args) -> dict:
    payload = core.payload_path(home, record)
    manifest = core.tree_manifest(source)
    if args.dry_run:
        return {"ok": True, "dry_run": True, "would_restore": label,
                "hash": core.manifest_hash(manifest)}
    if payload.exists():
        core.save_version_snapshot(home, record, "before restore " + label)
        core.backup_target(home, "library", record, payload, "pre-restore")
    core.remove_tree(payload)
    core.copy_tree(source, payload)
    record.update({
        "hash": core.manifest_hash(manifest), "manifest": manifest,
        "files": len(manifest), "bytes": core.tree_stats(manifest)["bytes"],
        "updated_at": core.utcnow(), "version": core.version_label(), "status": "active",
        "notes": (record.get("notes") or []) + ["restored from " + label],
    })
    home.upsert_resource(record)
    core.write_resource_files(home, record)
    home.log_event("restore", resource_id=record["id"], source=label, hash=record["hash"])
    return {"ok": True, "restored": label, "resource": record["id"], "hash": record["hash"],
            "version": record["version"], "path": str(payload)}


def restore_agent(home, record, agent, source: Path, label: str, args) -> dict:
    target = core.target_for(record, agent, core.workspace_path(args), args.scope)
    if not target.get("ok"):
        return {"ok": False, "error": target.get("reason")}
    destination = target["path"]
    if args.dry_run:
        return {"ok": True, "dry_run": True, "would_restore": label, "path": str(destination)}
    if destination.exists():
        core.backup_target(home, agent["id"], record, destination, "pre-restore")
        core.remove_tree(destination)
    core.copy_tree(source, destination)
    record.setdefault("targets", {})[agent["id"]] = {
        "agent": agent["id"], "scope": target.get("scope"), "path": str(destination),
        "mode": "copy", "source_hash": record["hash"],
        "target_hash": core.tree_hash(destination), "version": record.get("version"),
        "synced_at": core.utcnow(), "last_action": "restore",
    }
    home.upsert_resource(record)
    home.log_event("restore-agent", resource_id=record["id"], agent=agent["id"], source=label)
    return {"ok": True, "restored": label, "resource": record["id"], "agent": agent["id"],
            "path": str(destination)}


def cmd_restore(home, args) -> int:
    record = None
    if args.version:
        record = home.find_resource(args.resource or "")
        if record is None:
            core.output({"ok": False, "error": "resource not found: " + str(args.resource)}, args)
            return 1
        resource_dir = home.resource_dir(record["type"], record["slug"])
        source = resource_dir / "versions" / args.version / "payload"
        if not source.exists():
            core.output({"ok": False, "error": "version not found: " + args.version,
                         "available": [entry["label"] for entry in record.get("versions") or []]}, args)
            return 1
        label = "version:" + args.version
    else:
        if not args.backup_id:
            core.output({"ok": False, "error": "pass --backup-id or --resource plus --version"}, args)
            return 1
        path, manifest = find_backup(home, args.backup_id)
        if not manifest:
            core.output({"ok": False, "error": "backup not found: " + args.backup_id}, args)
            return 1
        source = path / "payload"
        if not source.exists():
            core.output({"ok": False, "error": "backup payload missing: " + str(source)}, args)
            return 1
        record = home.get_resource(manifest.get("resource_id"))
        if record is None:
            core.output({"ok": False, "error": "resource no longer in library: " + str(manifest.get("resource_id"))}, args)
            return 1
        label = "backup:" + args.backup_id
    if args.to == "agent":
        if not args.agent:
            core.output({"ok": False, "error": "--to agent requires --agent"}, args)
            return 1
        agent = core.load_agent_configs(home).get(args.agent)
        if agent is None:
            core.output({"ok": False, "error": "unknown agent: " + args.agent}, args)
            return 1
        result = restore_agent(home, record, agent, source, label, args)
    else:
        result = restore_library(home, record, source, label, args)
    core.output(result, args, [core.pj(result)])
    return 0 if result.get("ok") else 1


def cmd_prune(home, args) -> int:
    items = list_backups(home, args.resource)
    if args.resource:
        items = [item for item in items if item.get("resource_id") == args.resource]
    removed = []
    for item in items[args.keep:]:
        target = home.backups / item["backup_id"]
        if not args.dry_run:
            core.remove_tree(target)
        removed.append(item["backup_id"])
    result = {"ok": True, "removed": removed, "kept": len(items) - len(removed)}
    core.output(result, args, ["pruned " + str(len(removed)) + " backups, kept " + str(result["kept"])])
    return 0


def main(argv=None) -> int:
    parser = core.common_parser("Backup, list, restore and prune library / agent snapshots")
    sub = parser.add_subparsers(dest="command", required=True)
    backup = sub.add_parser("backup", help="snapshot a resource")
    backup.add_argument("--resource", required=True)
    backup.add_argument("--agent", default=None)
    backup.add_argument("--scope", default="user", choices=["user", "workspace"])
    listing = sub.add_parser("list", help="list snapshots")
    listing.add_argument("--resource", default=None)
    restore = sub.add_parser("restore", help="restore a snapshot or version")
    restore.add_argument("--backup-id", default=None)
    restore.add_argument("--resource", default=None)
    restore.add_argument("--version", default=None)
    restore.add_argument("--to", default="library", choices=["library", "agent"])
    restore.add_argument("--agent", default=None)
    restore.add_argument("--scope", default="user", choices=["user", "workspace"])
    restore.add_argument("--dry-run", action="store_true")
    prune = sub.add_parser("prune", help="delete old snapshots")
    prune.add_argument("--keep", type=int, default=10)
    prune.add_argument("--resource", default=None)
    prune.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    home = core.resolve_home(args)
    with core.library_lock(home, "library"):
        if args.command == "backup":
            return cmd_backup(home, args)
        if args.command == "list":
            return cmd_list(home, args)
        if args.command == "restore":
            return cmd_restore(home, args)
        if args.command == "prune":
            return cmd_prune(home, args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
