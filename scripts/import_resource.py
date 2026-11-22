#!/usr/bin/env python3
"""import_resource.py - download / import a resource into the central library.

Examples:
  import_resource.py --source ./my-skill
  import_resource.py --source https://github.com/owner/repo --on-conflict keep-source
  import_resource.py --source ./.claude/skills/foo --dry-run

The command never overwrites an existing library resource by default: a
different payload is staged under staging/conflicts/ and reported with exit
code 2. Pass --on-conflict to choose an explicit resolution.
"""

from __future__ import annotations
import re
import shutil
import subprocess
from urllib.parse import urlparse
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core


def platform_of(source: str) -> str:
    if source.startswith("http"):
        return "github" if "github.com" in source else "git"
    return "local"


OFFICIAL_GIT_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "codeberg.org")


def check_git_rewrites() -> list:
    """Detect url.<base>.insteadOf rules that redirect official hosts elsewhere.

    A global rewrite such as url.https://ghproxy.net/https://github.com/.insteadOf
    silently sends a "github.com" clone to a third-party mirror. That is a supply
    chain risk, so the importer refuses to clone until the user passes
    --allow-mirror (or removes the rule).
    """
    try:
        result = subprocess.run(["git", "config", "--global", "--get-regexp", "^url\\."],
                                capture_output=True, text=True, timeout=10,
                                encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return []
    rewrites = []
    for line in (result.stdout or "").splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        key, replaces = parts[0], parts[1].strip()
        match = re.match(r"url\.(.+?)\.insteadof", key, re.I)
        if not match:
            continue
        actual_base = match.group(1)
        official_host = urlparse(replaces).hostname or ""
        mirror_host = urlparse(actual_base).hostname or ""
        if official_host in OFFICIAL_GIT_HOSTS and mirror_host and mirror_host not in OFFICIAL_GIT_HOSTS:
            rewrites.append({"rule": key, "replaces": replaces, "actual_base": actual_base,
                             "official_host": official_host, "mirror_host": mirror_host})
    return rewrites


def clone_source(source: str, staging: Path, ref=None) -> dict:
    if not source.startswith("https://"):
        return {"ok": False, "error": "only https:// repository URLs are cloned automatically; use a local path otherwise"}
    destination = staging / ("clone-" + uuid.uuid4().hex[:8])
    command = ["git", "clone", "--depth", "1"]
    if ref:
        command += ["--branch", ref]
    command += [source, str(destination)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300,
                                encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": "git clone failed: " + str(exc)}
    if result.returncode != 0:
        return {"ok": False, "error": "git clone failed: " + (result.stderr or "").strip()[:500]}
    shutil.rmtree(destination / ".git", ignore_errors=True)
    return {"ok": True, "path": destination, "command": " ".join(command)}


def prepare_skill(path: Path, ctx: dict) -> dict:
    validation = core.validate_skill_dir(path)
    if not validation["valid"] and not ctx["force"]:
        return {"status": "invalid", "reason": "; ".join(validation["errors"]), "validation": validation}
    name = validation.get("name") or path.name
    return {"status": "ready", "type": "skill", "name": name, "payload_src": path,
            "validation": validation, "supported_agents": [], "extra": {}}


def prepare_plugin(path: Path, ctx: dict) -> dict:
    evidence = core.looks_like_plugin(path)
    supported = sorted({item.split(":")[0] for item in evidence
                        if item.split(":")[0] in ("claude", "cursor", "codex", "vscode", "dsh", "gemini", "kimi")})
    name = core.plugin_display_name(path)
    return {"status": "ready", "type": "plugin", "name": name, "payload_src": path,
            "validation": {"evidence": evidence}, "supported_agents": supported,
            "extra": {"plugin": {"evidence": evidence, "cross_tool": len(supported) > 1}}}


def prepare_mcp(path: Path, ctx: dict) -> dict:
    data = core.read_json(path, None)
    if not isinstance(data, dict):
        return {"status": "invalid", "reason": "MCP config is not a JSON object: " + str(path)}
    pointer = None
    for key in ("mcpServers", "mcp_servers", "servers"):
        if isinstance(data.get(key), dict):
            pointer = key
            break
    if pointer is None:
        return {"status": "invalid", "reason": "no mcpServers object found in " + str(path)}
    servers = data[pointer]
    wanted = ctx.get("server")
    if wanted:
        if wanted not in servers:
            return {"status": "invalid", "reason": "server not found: " + wanted,
                    "available": sorted(servers.keys())}
        selected = {wanted: servers[wanted]}
    else:
        selected = servers
    prepared = []
    for server_name, config in selected.items():
        if not isinstance(config, dict):
            continue
        clean, placeholders = core.redact_mapping(config)
        prepared.append({"status": "ready", "type": "mcp", "name": server_name,
                         "server": server_name, "config": clean, "placeholders": placeholders,
                         "source_path": str(path),
                         "validation": {"pointer": pointer},
                         "extra": {"mcp": {"server": server_name, "config": clean,
                                           "placeholders": placeholders}}})
    if not prepared:
        return {"status": "invalid", "reason": "no usable MCP server entries"}
    return {"status": "ready-multi", "items": prepared}


def prepare_rules(path: Path, ctx: dict) -> dict:
    if path.is_dir():
        files = [item for item in sorted(path.iterdir()) if item.is_file()]
        if not files:
            return {"status": "invalid", "reason": "rules directory is empty"}
        path = files[0]
    if not path.is_file():
        return {"status": "invalid", "reason": "rules source must be a file"}
    text = core.read_text(path, 256 * 1024)
    meta = core.parse_frontmatter(text)
    return {"status": "ready", "type": "rules", "name": path.stem, "payload_src": path,
            "validation": {"frontmatter": meta, "suffix": path.suffix},
            "supported_agents": [], "extra": {"content_sha": core.sha256_file(path)}}


PREPARERS = {"skill": prepare_skill, "plugin": prepare_plugin, "mcp": prepare_mcp, "rules": prepare_rules}


def relative_to_root(root: Path, path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


def describe_candidate(root: Path, candidate: dict) -> dict:
    return {
        "name": candidate.get("name") or Path(candidate["path"]).name,
        "type": candidate.get("type"),
        "path": relative_to_root(root, candidate["path"]),
        "confidence": candidate.get("confidence"),
    }


def select_candidates(root: Path, candidates: list, ctx: dict):
    """Reduce discovered candidates to the ones the user asked for.

    A repository or folder that bundles several skills must not import all of
    them by accident: the default is to stop with exit code 2 and list the
    choices. --pick <path> imports exactly one, --all imports every match.
    """
    pick = ctx.get("pick")
    if pick:
        target = Path(pick).expanduser()
        if not target.is_absolute():
            target = Path(root) / target
        target = target.resolve()
        if not target.exists():
            return None, {
                "status": "pick-not-found", "pick": pick, "root": str(root),
                "reason": "no such path inside the source: " + str(pick),
                "available": [describe_candidate(root, item) for item in candidates],
            }
        info = core.classify_path(target)
        if info["type"] not in PREPARERS and not target.is_dir():
            return None, {
                "status": "pick-not-found", "pick": pick, "root": str(root),
                "reason": "picked path is not a skill / plugin / MCP config / rules file (" +
                          str(info["type"]) + ")",
                "available": [describe_candidate(root, item) for item in candidates],
            }
        return [info], None
    if ctx.get("all") or len(candidates) <= 1:
        return candidates, None
    return None, {
        "status": "multiple-candidates", "root": str(root), "count": len(candidates),
        "candidates": [describe_candidate(root, item) for item in candidates],
        "reason": "found %d resources in this source; choose one with --pick <path> " % len(candidates) +
                  "or import every match with --all",
    }


def stage_payload(home, prepared: dict, ctx: dict) -> Path:
    """Materialise the payload that will live under library/<kind>/<slug>/payload."""
    staging_root = home.staging / ("import-" + uuid.uuid4().hex[:8])
    payload = staging_root / "payload"
    kind = prepared["type"]
    if kind in ("skill", "plugin"):
        core.copy_tree(prepared["payload_src"], payload)
    elif kind == "mcp":
        payload.mkdir(parents=True, exist_ok=True)
        core.write_json_atomic(payload / "server.json",
                               {"name": prepared["server"], "config": prepared["config"]})
    elif kind == "rules":
        payload.mkdir(parents=True, exist_ok=True)
        core.copy_tree(prepared["payload_src"], payload / "content.md")
    return payload


def apply_import(home, prepared: dict, ctx: dict) -> dict:
    kind = prepared["type"]
    name = prepared["name"]
    slug = core.slugify(name)
    payload = stage_payload(home, prepared, ctx)
    manifest = core.tree_manifest(payload)
    new_hash = core.manifest_hash(manifest)
    registry = home.registry["resources"]
    existing = None
    for record in registry.values():
        if record["type"] == kind and str(record["name"]).lower() == name.lower():
            existing = record
            break
    safety = core.scan_safety(payload)
    if safety["secrets"] and not ctx.get("allow_secrets"):
        core.remove_tree(payload.parent)
        return {"status": "secret-detected", "name": name, "type": kind,
                "secrets": safety["secrets"],
                "reason": "potential credential found in payload; remove it or redact before importing",
                "safety": safety}
    if safety["requires_confirmation"] and not ctx["allow_risk"]:
        core.remove_tree(payload.parent)
        return {"status": "needs-confirmation", "name": name, "type": kind, "safety": safety,
                "reason": "security scanner found risky patterns; review and re-run with --allow-risk"}
    if existing is None:
        resource_id = core.make_resource_id(kind, name, registry)
        record = core.build_record(kind, name, payload, {
            "url": ctx.get("source_url"), "platform": ctx.get("platform"),
            "kind": "local-path", "path": ctx.get("source_path"),
        }, slug=resource_id.split("/", 1)[1], safety=safety,
            validation=prepared.get("validation") or {})
        record["id"] = resource_id
        record["supported_agents"] = prepared.get("supported_agents") or []
        if kind == "plugin":
            record["package"] = name
        record["extra"] = prepared.get("extra") or {}
        record.update(prepared.get("extra") or {})
        if prepared.get("placeholders"):
            record["mcp"] = dict(record.get("mcp") or {})
            record["mcp"]["placeholders"] = prepared["placeholders"]
        if kind == "rules":
            record["content"] = {"file": "content.md", "sha256": prepared["extra"]["content_sha"]}
        if ctx["dry_run"]:
            core.remove_tree(payload.parent)
            return {"status": "would-import", "name": name, "type": kind, "id": resource_id,
                    "hash": new_hash, "files": len(manifest), "safety": safety_summary(safety)}
        destination = home.resource_dir(kind, record["slug"])
        if destination.exists():
            core.remove_tree(payload.parent)
            return {"status": "error", "reason": "destination already exists: " + str(destination)}
        destination.mkdir(parents=True, exist_ok=True)
        core.copy_tree(payload, destination / "payload")
        record["hash"] = new_hash
        record["manifest"] = manifest
        record["files"] = len(manifest)
        record["bytes"] = core.tree_stats(manifest)["bytes"]
        home.upsert_resource(record)
        core.write_resource_files(home, record)
        home.log_event("import", resource_id=record["id"], hash=new_hash, source=ctx.get("source_path"))
        core.remove_tree(payload.parent)
        return {"status": "imported", "name": name, "type": kind, "id": record["id"],
                "version": record["version"], "hash": new_hash, "files": len(manifest),
                "path": str(destination / "payload"), "safety": safety_summary(safety)}
    # -- existing resource ---------------------------------------------------
    if existing.get("hash") == new_hash:
        core.remove_tree(payload.parent)
        if kind == "mcp" and existing.get("mcp"):
            existing["mcp"]["config"] = prepared["config"]
            home.upsert_resource(existing)
        return {"status": "duplicate", "name": name, "type": kind, "id": existing["id"],
                "version": existing.get("version"), "hash": new_hash}
    resolution = ctx["on_conflict"]
    if resolution == "skip":
        conflict_dir = home.conflicts / (core.slugify(name) + "-" + new_hash[:8])
        conflict_dir.mkdir(parents=True, exist_ok=True)
        core.copy_tree(payload, conflict_dir / "payload")
        core.write_json_atomic(conflict_dir / "conflict.json", {
            "resource_id": existing["id"], "name": name, "type": kind,
            "existing_hash": existing.get("hash"), "incoming_hash": new_hash,
            "existing_version": existing.get("version"),
            "source": ctx.get("source_path"), "detected_at": core.utcnow(),
            "options": ["keep-library", "keep-source", "new-version"],
        })
        core.remove_tree(payload.parent)
        home.log_event("import-conflict", resource_id=existing["id"], incoming_hash=new_hash)
        return {"status": "conflict", "name": name, "type": kind, "id": existing["id"],
                "existing_version": existing.get("version"), "incoming_hash": new_hash,
                "conflict_path": str(conflict_dir)}
    if resolution == "keep-library":
        core.remove_tree(payload.parent)
        return {"status": "kept-library", "name": name, "type": kind, "id": existing["id"]}
    if ctx["dry_run"]:
        core.remove_tree(payload.parent)
        return {"status": "would-update", "name": name, "type": kind, "id": existing["id"],
                "old_hash": existing.get("hash"), "new_hash": new_hash,
                "resolution": resolution}
    resource_dir = home.resource_dir(kind, existing["slug"])
    snapshot = core.save_version_snapshot(home, existing, "before " + resolution)
    backup = core.backup_target(home, "library", existing, resource_dir / "payload", "pre-import")
    core.remove_tree(resource_dir / "payload")
    core.copy_tree(payload, resource_dir / "payload")
    existing.update({
        "hash": new_hash, "manifest": manifest, "files": len(manifest),
        "bytes": core.tree_stats(manifest)["bytes"], "updated_at": core.utcnow(),
        "version": core.version_label(), "source": {
            "url": ctx.get("source_url"), "platform": ctx.get("platform"),
            "kind": "local-path", "path": ctx.get("source_path")},
        "safety": safety, "validation": prepared.get("validation") or {},
        "status": "active",
    })
    if kind == "mcp":
        existing["mcp"] = {"server": prepared["server"], "config": prepared["config"],
                           "placeholders": prepared.get("placeholders") or []}
    if kind == "plugin":
        existing["package"] = name
        existing["supported_agents"] = prepared.get("supported_agents") or []
    if kind == "rules":
        existing["content"] = {"file": "content.md", "sha256": prepared["extra"]["content_sha"]}
    existing["versions"] = existing.get("versions") or []
    home.upsert_resource(existing)
    core.write_resource_files(home, existing)
    core.remove_tree(payload.parent)
    home.log_event("import-update", resource_id=existing["id"], old_hash=backup.get("target_hash"),
                   new_hash=new_hash, resolution=resolution, snapshot=snapshot)
    return {"status": "updated", "name": name, "type": kind, "id": existing["id"],
            "version": existing["version"], "hash": new_hash, "snapshot": snapshot,
            "backup": backup.get("backup_id"), "safety": safety_summary(safety)}


def safety_summary(safety: dict) -> dict:
    return {"risk": safety.get("risk"), "counts": safety.get("counts"),
            "binaries": safety.get("binaries"), "secrets": len(safety.get("secrets") or [])}


def import_source(home, source: str, ctx: dict) -> list:
    source_path = Path(source).expanduser()
    if source.startswith("http"):
        rewrites = check_git_rewrites()
        if rewrites and not ctx.get("allow_mirror"):
            return [{"status": "git-rewrite-detected", "source": source,
                     "reason": "git url.<base>.insteadOf rules redirect official hosts to a mirror; "
                               "review them and pass --allow-mirror only if the mirror is trusted",
                     "rewrites": rewrites}]
        cloned = clone_source(source, home.staging, ctx.get("ref"))
        if not cloned["ok"]:
            return [{"status": "error", "reason": cloned["error"], "source": source}]
        root = cloned["path"]
        ctx["platform"] = platform_of(source)
        ctx["source_url"] = source
    else:
        if not source_path.is_absolute():
            base = ctx.get("workspace") or Path.cwd()
            source_path = (Path(base) / source_path).resolve()
        if not source_path.exists():
            return [{"status": "error", "reason": "source does not exist: " + str(source_path)}]
        root = source_path
    ctx["source_path"] = str(root)
    forced = ctx.get("type") or "auto"
    if forced != "auto":
        candidates = []
        if root.is_file() and forced in ("mcp", "rules"):
            candidates = [{"path": str(root), "type": forced, "confidence": "high",
                           "name": root.stem, "evidence": ["explicit --type " + forced],
                           "validation": {}, "issues": []}]
        else:
            info = core.classify_path(root)
            if info["type"] == forced:
                candidates = [info]
            else:
                candidates = [item for item in core.discover_candidates(root, ctx.get("depth", 3))
                              if item["type"] == forced]
        if not candidates:
            return [{"status": "error", "reason": "no resource of type " + forced + " found in " + str(root)}]
    else:
        candidates = core.discover_candidates(root, ctx.get("depth", 3))
        if not candidates:
            info = core.classify_path(root)
            if info["type"] in ("skill", "plugin", "mcp", "rules"):
                candidates = [info]
        allowed = ctx.get("kinds")
        if allowed:
            candidates = [candidate for candidate in candidates if candidate["type"] in allowed]
    ctx["_clone_dir"] = str(root) if source.startswith("http") else None
    selected, problem = select_candidates(root, candidates, ctx)
    if problem:
        if ctx.get("_clone_dir"):
            core.remove_tree(Path(ctx["_clone_dir"]))
        return [problem]
    candidates = selected
    results = []
    for candidate in candidates:
        kind = candidate["type"]
        if kind not in PREPARERS:
            results.append({"status": "skipped", "reason": "unsupported resource type " + str(kind),
                            "path": candidate["path"]})
            continue
        prepared = PREPARERS[kind](Path(candidate["path"]), ctx)
        if prepared["status"] == "ready-multi":
            for item in prepared["items"]:
                results.append(apply_import(home, item, ctx))
            continue
        if prepared["status"] != "ready":
            prepared.setdefault("path", candidate["path"])
            results.append(prepared)
            continue
        results.append(apply_import(home, prepared, ctx))
    if ctx.get("_clone_dir"):
        core.remove_tree(Path(ctx["_clone_dir"]))
    return results


def main(argv=None) -> int:
    parser = core.common_parser("Import a skill / plugin / MCP server / rules file into the central library")
    parser.add_argument("--source", required=True, help="local path or https repository URL")
    parser.add_argument("--type", default="auto", choices=["auto", "skill", "plugin", "mcp", "rules"])
    parser.add_argument("--kinds", default=None, help="comma separated kinds to import from a repository")
    parser.add_argument("--pick", default=None,
                        help="import exactly this resource from the source (path relative to it)")
    parser.add_argument("--all", action="store_true",
                        help="import every resource found in the source (default: refuse when ambiguous)")
    parser.add_argument("--server", default=None, help="MCP server name to import (default: all)")
    parser.add_argument("--ref", default=None, help="git branch/tag for URL sources")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--on-conflict", default="skip",
                        choices=["skip", "keep-library", "keep-source", "new-version"])
    parser.add_argument("--force", action="store_true", help="import even if SKILL.md validation fails")
    parser.add_argument("--allow-risk", action="store_true", help="import despite security findings")
    parser.add_argument("--allow-secrets", action="store_true", help="import even if the secret scanner fired")
    parser.add_argument("--allow-mirror", action="store_true",
                        help="allow git insteadOf rewrites that redirect official hosts to a mirror")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    home = core.resolve_home(args)
    kinds = {kind.strip() for kind in args.kinds.split(",") if kind.strip()} if args.kinds else None
    ctx = {
        "on_conflict": args.on_conflict, "force": args.force, "allow_risk": args.allow_risk,
        "allow_secrets": args.allow_secrets, "allow_mirror": args.allow_mirror,
        "dry_run": args.dry_run, "type": args.type,
        "server": args.server, "ref": args.ref, "depth": args.depth, "kinds": kinds,
        "pick": args.pick, "all": args.all,
        "workspace": core.workspace_path(args),
    }
    with core.library_lock(home, "library"):
        results = import_source(home, args.source, ctx)
    summary = core.summarize_counts(results, "status")
    conflicts = [item for item in results if item.get("status") == "conflict"]
    errors = [item for item in results if item.get("status") in
              ("error", "invalid", "secret-detected", "needs-confirmation",
               "git-rewrite-detected", "pick-not-found")]
    ambiguous = [item for item in results if item.get("status") == "multiple-candidates"]
    result = {"ok": not errors and not ambiguous, "source": args.source, "results": results,
              "summary": summary, "conflicts": len(conflicts), "errors": len(errors)}
    lines = ["Import " + args.source]
    for item in results:
        status = item.get("status", "?")
        lines.append("- " + status + ": " + str(item.get("name") or item.get("path") or ""))
        for key in ("id", "version", "hash", "reason", "conflict_path", "snapshot", "backup"):
            if item.get(key):
                lines.append("    " + key + ": " + str(item[key]))
        if item.get("safety"):
            lines.append("    safety: risk=" + str(item["safety"].get("risk")) +
                         " high=" + str((item["safety"].get("counts") or {}).get("high")))
        for candidate in item.get("candidates") or []:
            lines.append("    " + str(candidate["type"]) + " " + str(candidate["path"]) + "  " + str(candidate["name"]))
        for candidate in (item.get("available") or []) if item.get("status") == "pick-not-found" else []:
            lines.append("    " + str(candidate["type"]) + " " + str(candidate["path"]) + "  " + str(candidate["name"]))
        for finding in (item.get("safety") or {}).get("findings", [])[:3]:
            lines.append("      ! " + finding["severity"] + ": " + finding["rule"] + " in " + finding["file"] + ":" + str(finding["line"]))
    lines.append("summary: " + core.pj(summary).replace("\n", " "))
    core.output(result, args, lines)
    if conflicts or ambiguous:
        return 2
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
