#!/usr/bin/env python3
"""detect_resources.py - classify resources in a path, a tool, or a source URL.

Modes (at least one required):
  --path <p>        inspect a downloaded repository / folder / file
  --url <u>         classify a source URL before downloading
  --agent <id>      list resources a single AI tool can see
  --all-agents      list resources across every detected tool

Output: {ok, mode, candidates:[{type,name,confidence,evidence,path,...}], summary}
"""

from __future__ import annotations
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aem_core as core

ALLOWED_URL_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "codeberg.org")


def classify_url(url: str) -> dict:
    parsed = urlparse(url)
    result = {"url": url, "platform": parsed.hostname, "type": None,
              "confidence": "low", "requires_clone": True, "next_step": ""}
    if parsed.scheme not in ("https", "http"):
        result["error"] = "only http(s) URLs are accepted; use a local path for local repositories"
        return result
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_URL_HOSTS:
        result["error"] = "unsupported host " + host + "; supported: " + ", ".join(ALLOWED_URL_HOSTS)
        return result
    short_name = {"github.com": "github", "gitlab.com": "gitlab",
                  "bitbucket.org": "bitbucket", "codeberg.org": "codeberg"}[host]
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        result["error"] = "URL is not a repository URL (expected https://" + host + "/owner/repo)"
        return result
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    result.update({
        "platform": short_name,
        "host": host,
        "owner": owner,
        "repo": repo,
        "clone_url": "https://" + host + "/" + owner + "/" + repo + ".git",
        "web_url": "https://" + host + "/" + owner + "/" + repo,
        "type": "repository",
        "confidence": "high",
        "next_step": "import_resource.py --source " + url + "  (clones with git, then classifies SKILL.md / plugin manifests / MCP / rules)",
    })
    lowered = repo.lower()
    hints = []
    if "skill" in lowered:
        hints.append("name suggests a Skill collection")
    if "plugin" in lowered:
        hints.append("name suggests a Plugin")
    if "mcp" in lowered:
        hints.append("name suggests an MCP server")
    if hints:
        result["hints"] = hints
    return result


def skill_candidates_in_dir(path: Path) -> list:
    found = []
    if not path.is_dir():
        return found
    for child in sorted(path.iterdir()):
        try:
            if child.is_dir() and (child / "SKILL.md").is_file():
                found.append(core.classify_path(child))
        except OSError:
            continue
    return found


def scan_agent_resources(agent: dict, home, workspace, kinds) -> list:
    detected = core.detect_agent(agent, workspace)
    found = []
    if "skills" in kinds:
        for skill_dir in detected["skills"]:
            if not skill_dir["exists"]:
                continue
            if skill_dir["scope"] == "workspace" and workspace is None:
                continue
            for candidate in skill_candidates_in_dir(Path(skill_dir["path"])):
                candidate["source_agent"] = agent["id"]
                candidate["scope"] = skill_dir["scope"]
                found.append(candidate)
    if "plugins" in kinds:
        for item in core.plugin_inventory(agent):
            found.append({
                "path": item.get("path") or "", "type": "plugin", "confidence": "high",
                "name": item.get("name"), "version": item.get("version"),
                "enabled": item.get("enabled"), "installed": True,
                "evidence": ["installed plugin via " + str(item.get("source")) +
                             ((" marketplace=" + str(item.get("marketplace"))) if item.get("marketplace") else "")],
                "validation": {}, "issues": [], "source_agent": agent["id"],
            })
    if "mcp" in kinds:
        for config in (agent.get("mcp") or {}).get("configs") or []:
            if config.get("kind") != "json":
                continue
            raw = config["path"]
            config_path = core.resolve_agent_path(agent, raw, workspace,
                                                  config.get("scope") or "user")
            if config_path is None:
                continue
            data = core.read_json(config_path, None)
            if not isinstance(data, dict):
                continue
            pointer = config.get("pointer") or ["mcpServers"]
            node = data
            for key in pointer:
                node = node.get(key, {}) if isinstance(node, dict) else {}
            if isinstance(node, dict):
                for server_name in node:
                    found.append({
                        "path": str(config_path), "type": "mcp", "confidence": "high",
                        "name": server_name, "evidence": ["mcpServers entry in " + str(config_path)],
                        "validation": {}, "issues": [],
                        "source_agent": agent["id"], "server": server_name,
                    })
    if "rules" in kinds:
        for raw in (agent.get("rules") or {}).get("paths") or []:
            rule_path = core.resolve_agent_path(agent, raw, workspace,
                                                "workspace" if raw.startswith(".") else "user")
            if rule_path is None:
                continue
            if rule_path.exists():
                found.append({
                    "path": str(rule_path), "type": "rules", "confidence": "medium",
                    "name": rule_path.name, "evidence": ["known instruction location for " + agent["id"]],
                    "validation": {}, "issues": [], "source_agent": agent["id"],
                })
    return found


def attach_library_state(home, candidates: list, check_hash: bool) -> None:
    for candidate in candidates:
        record = home.find_resource(candidate.get("name") or "")
        if not record:
            candidate["library_match"] = None
            continue
        match = {"id": record["id"], "version": record.get("version"), "hash": record.get("hash")}
        if check_hash and Path(candidate["path"]).is_dir() and candidate["type"] == "skill":
            try:
                match["same_content"] = core.tree_hash(Path(candidate["path"])) == record.get("hash")
            except OSError:
                pass
        candidate["library_match"] = match


def main(argv=None) -> int:
    parser = core.common_parser("Classify AI resources (skill / plugin / MCP / rules) from a path, tool or URL")
    parser.add_argument("--path", action="append", default=None, help="file or directory to inspect (repeatable)")
    parser.add_argument("--url", action="append", default=None, help="source URL to classify (repeatable)")
    parser.add_argument("--agent", action="append", default=None, help="scan a single agent id (repeatable)")
    parser.add_argument("--all-agents", action="store_true", help="scan every detected agent")
    parser.add_argument("--kinds", default="skills,plugins,mcp,rules,other",
                        help="comma separated resource kinds to report (default: all)")
    parser.add_argument("--depth", type=int, default=3, help="max directory depth for --path discovery")
    parser.add_argument("--safety", action="store_true", help="run the security scanner on each candidate")
    parser.add_argument("--check-hash", action="store_true", help="compare candidate content with library copy")
    args = parser.parse_args(argv)
    home = core.Home(args.home)  # read-only discovery: no library creation
    workspace = core.workspace_path(args)
    kinds = {kind.strip() for kind in args.kinds.split(",") if kind.strip()}
    candidates = []
    mode = []
    if args.url:
        mode.append("url")
        for url in args.url:
            candidates.append({"kind": "source", **classify_url(url)})
    if args.path:
        mode.append("path")
        for raw in args.path:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = (workspace or Path.cwd()) / path
            if path.is_file():
                candidates.append(core.classify_path(path))
            else:
                candidates.extend(core.discover_candidates(path, args.depth))
    if args.all_agents or args.agent:
        mode.append("agents")
        agents = core.resolve_agents(home, args.agent)
        if args.agent:
            known = {agent["id"] for agent in core.resolve_agents(home)}
            unknown = [agent_id for agent_id in args.agent if agent_id not in known]
            if unknown:
                core.output({"ok": False, "error": "unknown agent id(s): " + ", ".join(unknown)}, args)
                return 1
        for agent in agents:
            candidates.extend(scan_agent_resources(agent, home, workspace, kinds))
    if not mode:
        parser.error("nothing to do: pass --path, --url, --agent or --all-agents")
    kind_map = {"skills": "skill", "plugins": "plugin", "mcp": "mcp", "rules": "rules", "other": "other"}
    wanted = {kind_map.get(kind, kind) for kind in kinds}
    filtered = [candidate for candidate in candidates
                if candidate.get("type") in wanted or candidate.get("kind") == "source"]
    for candidate in filtered:
        if args.safety and candidate.get("type") in ("skill", "plugin", "rules", "mcp"):
            candidate["safety"] = core.scan_safety(Path(candidate["path"]))
    attach_library_state(home, filtered, args.check_hash)
    summary = core.summarize_counts(filtered, "type")
    result = {"ok": True, "mode": mode, "generated_at": core.utcnow(),
              "candidates": filtered, "summary": summary}
    lines = ["Resource candidates (" + str(len(filtered)) + "):"]
    for candidate in filtered:
        extra = ""
        if candidate.get("library_match"):
            extra = "  [library: " + candidate["library_match"]["id"] + " " + str(candidate["library_match"].get("version")) + "]"
        if candidate.get("kind") == "source":
            lines.append("- SOURCE " + str(candidate.get("url")))
            if candidate.get("error"):
                lines.append("    error: " + candidate["error"])
            else:
                lines.append("    " + candidate["platform"] + "/" + candidate["owner"] + "/" + candidate["repo"] +
                             " (type unknown until cloned)")
                lines.append("    next: " + candidate["next_step"])
            continue
        validation = candidate.get("validation") or {}
        validity = ""
        if candidate.get("type") == "skill":
            validity = " valid=" + str(validation.get("valid"))
        lines.append("- " + candidate["type"].upper() + " " + candidate.get("name") +
                     " [" + candidate.get("confidence") + "]" + validity + extra)
        lines.append("    " + candidate["path"])
        for evidence in (candidate.get("evidence") or [])[:3]:
            lines.append("    evidence: " + evidence)
        for issue in (candidate.get("issues") or [])[:3]:
            lines.append("    issue: " + issue)
        if candidate.get("safety"):
            lines.append("    safety: risk=" + candidate["safety"]["risk"] +
                         " high=" + str(candidate["safety"]["counts"]["high"]))
    lines.append("summary: " + core.pj(summary).replace("\n", " "))
    result["summary_text"] = lines
    core.output(result, args, lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
