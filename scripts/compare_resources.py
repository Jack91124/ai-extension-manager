#!/usr/bin/env python3
"""compare_resources.py - diff two resource copies with hashes and optional unified diff.

Operands (repeatable per side):
  <path>                        a local file or directory
  resource:<id|name>            the current library payload
  resource:<id|name>@<label>    a stored version snapshot
  agent:<agent-id>:<resource>   the copy installed in one AI tool

Exit codes: 0 identical, 2 different, 1 error.
"""

from __future__ import annotations
import difflib
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core


def split_operand(operand: str):
    if operand.startswith("resource:"):
        body = operand[len("resource:"):]
        if "@" in body:
            name, label = body.rsplit("@", 1)
            return {"kind": "resource-version", "name": name, "label": label}
        return {"kind": "resource", "name": body}
    if operand.startswith("agent:"):
        parts = operand.split(":")
        if len(parts) < 3:
            return {"kind": "error", "error": "agent operand must be agent:<agent>:<resource>"}
        return {"kind": "agent", "agent": parts[1], "name": ":".join(parts[2:])}
    if operand.startswith("path:"):
        return {"kind": "path", "path": operand[len("path:"):]}
    return {"kind": "path", "path": operand}


def resolve_operand(home, operand: str, workspace, scope) -> dict:
    spec = split_operand(operand)
    if spec["kind"] == "error":
        return spec
    if spec["kind"] == "path":
        path = Path(spec["path"]).expanduser()
        if not path.is_absolute():
            path = (workspace or Path.cwd()) / path
        return {"label": operand, "path": path, "kind": "path"}
    record = home.find_resource(spec["name"])
    if record is None:
        return {"label": operand, "error": "resource not found: " + spec["name"]}
    if spec["kind"] == "resource-version":
        resource_dir = home.resource_dir(record["type"], record["slug"])
        payload = resource_dir / "versions" / spec["label"] / "payload"
        if not payload.exists():
            return {"label": operand, "error": "version not found: " + spec["label"],
                    "available": [entry["label"] for entry in record.get("versions") or []]}
        return {"label": operand + " (" + record["id"] + ")", "path": payload,
                "record": record, "version": spec["label"]}
    if spec["kind"] == "agent":
        agents = core.load_agent_configs(home)
        agent = agents.get(spec["agent"])
        if agent is None:
            return {"label": operand, "error": "unknown agent: " + spec["agent"]}
        target = core.target_for(record, agent, workspace, scope)
        if not target.get("ok"):
            return {"label": operand, "error": target.get("reason")}
        if record["type"] == "mcp":
            data = core.read_json(target["path"], {}) if target["path"].exists() else {}
            node = data
            for key in target.get("pointer") or ["mcpServers"]:
                node = node.get(key, {}) if isinstance(node, dict) else {}
            entry = node.get(target["server"]) if isinstance(node, dict) else None
            return {"label": operand, "mcp_entry": entry, "record": record,
                    "path": target["path"], "kind": "mcp"}
        return {"label": operand, "path": target["path"], "record": record, "kind": "target"}
    payload = core.payload_path(home, record)
    return {"label": operand + " (" + record["id"] + ")", "path": payload,
            "record": record, "version": record.get("version")}


def side_summary(home, side: dict) -> dict:
    if side.get("error"):
        return side
    if side.get("kind") == "mcp":
        entry = side.get("mcp_entry")
        return {"label": side["label"], "kind": "mcp", "path": str(side["path"]),
                "hash": core.short_hash(core.pj(entry)) if entry is not None else None,
                "present": entry is not None, "record": (side.get("record") or {}).get("id")}
    path: Path = side["path"]
    if not path.exists():
        return {"label": side["label"], "kind": "missing", "path": str(path), "present": False}
    manifest = core.tree_manifest(path)
    return {"label": side["label"], "kind": "dir" if path.is_dir() else "file",
            "path": str(path), "hash": core.manifest_hash(manifest),
            "files": len(manifest), "bytes": core.tree_stats(manifest)["bytes"],
            "manifest": manifest, "present": True,
            "record": (side.get("record") or {}).get("id"),
            "version": side.get("version")}


def unified_diff(old_path: Path, new_path: Path, max_lines: int) -> str:
    try:
        old_text = core.read_text(old_path, 512 * 1024).splitlines()
        new_text = core.read_text(new_path, 512 * 1024).splitlines()
    except OSError:
        return "(binary or unreadable)"
    diff = list(difflib.unified_diff(old_text, new_text, fromfile="old/" + old_path.name,
                                     tofile="new/" + new_path.name, lineterm="", n=2))
    if len(diff) > max_lines:
        diff = diff[:max_lines] + ["... diff truncated at " + str(max_lines) + " lines"]
    return "\n".join(diff)


def compare_sides(left: dict, right: dict, max_lines: int, with_diff: bool) -> dict:
    result = {"identical": False, "differences": [], "diffs": []}
    if not left.get("present") or not right.get("present"):
        result["differences"].append("one side is missing")
        return result
    if left.get("kind") == "mcp" or right.get("kind") == "mcp":
        result["identical"] = left.get("hash") == right.get("hash")
        if not result["identical"]:
            result["diffs"].append({"file": "mcp entry", "diff": "left=" + core.pj(left) + "\nright=" + core.pj(right)})
        return result
    left_manifest = left.get("manifest") or {}
    right_manifest = right.get("manifest") or {}
    if left.get("hash") == right.get("hash"):
        result["identical"] = True
        return result
    missing, extra, changed = core.diff_manifests(left_manifest, right_manifest)
    result["differences"] = ([{"kind": "only-left", "path": rel} for rel in missing] +
                             [{"kind": "only-right", "path": rel} for rel in extra] +
                             [{"kind": "changed", "path": rel} for rel in changed])
    if with_diff:
        left_root = Path(left["path"])
        right_root = Path(right["path"])
        for rel in missing[:20]:
            result["diffs"].append({"file": rel, "kind": "only-left",
                                    "diff": unified_diff(left_root / rel, right_root / rel, max_lines)})
        for rel in extra[:20]:
            result["diffs"].append({"file": rel, "kind": "only-right",
                                    "diff": unified_diff(left_root / rel, right_root / rel, max_lines)})
        for rel in changed[:20]:
            left_file = left_root / rel if left_root.is_dir() else left_root
            right_file = right_root / rel if right_root.is_dir() else right_root
            if right_file.exists() and left_file.exists():
                result["diffs"].append({"file": rel, "kind": "changed",
                                        "diff": unified_diff(left_file, right_file, max_lines)})
    return result


def main(argv=None) -> int:
    parser = core.common_parser("Compare two resource copies (library, version, agent target or path)")
    parser.add_argument("--left", required=True, help="left operand")
    parser.add_argument("--right", required=True, help="right operand")
    parser.add_argument("--scope", default="user", choices=["user", "workspace"])
    parser.add_argument("--diff", action="store_true", help="include unified diffs")
    parser.add_argument("--max-diff-lines", type=int, default=200)
    parser.add_argument("--show-version", default=None, help="add the version of a resource: resource:<name>@<label>")
    args = parser.parse_args(argv)
    home = core.resolve_home(args)
    workspace = core.workspace_path(args)
    left_operand = args.left + ("@" + args.show_version if args.show_version and args.left.startswith("resource:") and "@" not in args.left else "")
    left_side = side_summary(home, resolve_operand(home, left_operand, workspace, args.scope))
    right_side = side_summary(home, resolve_operand(home, args.right, workspace, args.scope))
    errors = [side for side in (left_side, right_side) if side.get("error")]
    if errors:
        result = {"ok": False, "left": left_side, "right": right_side, "errors": errors}
        core.output(result, args)
        return 1
    missing = [side for side in (left_side, right_side) if not side.get("present")]
    if missing:
        result = {"ok": False, "left": left_side, "right": right_side,
                  "errors": [{"error": "operand not found on disk",
                              "label": side.get("label"), "path": side.get("path")} for side in missing]}
        core.output(result, args, ["Compare:", "  missing: " + ", ".join(str(side.get("label")) for side in missing)])
        return 1
    if args.diff and left_side.get("present") and right_side.get("present") and left_side.get("kind") != "mcp":
        # full-tree diff mode uses the raw paths
        comparison = compare_sides(left_side, right_side, args.max_diff_lines, True)
    else:
        comparison = compare_sides(left_side, right_side, args.max_diff_lines, False)
    left_side.pop("manifest", None)
    right_side.pop("manifest", None)
    result = {"ok": True, "left": left_side, "right": right_side,
              "identical": comparison["identical"],
              "differences": comparison["differences"], "diffs": comparison["diffs"]}
    lines = ["Compare:", "  left : " + (left_side.get("label") or "") + "  hash=" + str(left_side.get("hash")),
             "  right: " + (right_side.get("label") or "") + "  hash=" + str(right_side.get("hash"))]
    if comparison["identical"]:
        lines.append("identical: yes")
    else:
        lines.append("identical: no (" + str(len(comparison["differences"])) + " file differences)")
        for item in comparison["differences"][:40]:
            if isinstance(item, str):
                lines.append("  " + item)
            else:
                lines.append("  " + str(item.get("kind", "changed")).ljust(11) + " " + str(item.get("path")))
        for block in comparison["diffs"]:
            lines.append("")
            lines.append("--- " + block["file"] + " ---")
            lines.append(block["diff"])
    core.output(result, args, lines)
    return 0 if comparison["identical"] else 2


if __name__ == "__main__":
    sys.exit(main())
