#!/usr/bin/env python3
"""aem_core - shared library for the AI Extension Manager skill.

Standard-library only so every script runs on a bare Python 3.9+ install.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
TOOL_VERSION = "1.0.14"
VCS_DIRS = {".git", ".svn", ".hg", ".bzr", "__pycache__", ".mypy_cache", ".pytest_cache"}
SYSTEM_JUNK = {".DS_Store", "Thumbs.db", "desktop.ini"}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def pj(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False)


def emit_json(payload: dict, stream=None) -> None:
    (stream or sys.stdout).write(pj(payload) + "\n")


def read_json(path: Path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json_atomic(path: Path, payload) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex[:8])
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(pj(payload) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def read_text(path: Path, limit: int | None = None) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read() if limit is None else handle.read(limit)
    except OSError:
        return ""


def expand_path(value: str, base: Path | None = None) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(raw)
    if not path.is_absolute() and base is not None:
        path = Path(base) / path
    return path


def safe_join(root: Path, relative: str) -> Path:
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path escapes root: " + relative)
    return candidate


def is_within(child: Path, parent: Path) -> bool:
    try:
        child = Path(child).resolve()
        parent = Path(parent).resolve()
        return child == parent or parent in child.parents
    except OSError:
        return False


def human_bytes(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return str(int(value)) + "B" if unit == "B" else format(value, ".1f") + unit
        value /= 1024.0
    return str(num) + "B"


def short_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", name.strip().lower()).strip("-._")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:80] or "resource"


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def iter_payload_files(root: Path):
    root = Path(root)
    if not root.exists():
        return
    if root.is_file():
        yield root
        return
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in VCS_DIRS and not d.startswith(".aem-tmp"))
        for name in sorted(filenames):
            if name in SYSTEM_JUNK or name.startswith(".aem-tmp"):
                continue
            yield Path(current) / name


def tree_manifest(root: Path) -> dict:
    root = Path(root)
    manifest = {}
    for file_path in iter_payload_files(root):
        rel = file_path.name if root.is_file() else file_path.relative_to(root).as_posix()
        try:
            manifest[rel] = {"sha256": sha256_file(file_path), "size": file_path.stat().st_size}
        except OSError:
            manifest[rel] = {"sha256": "unreadable", "size": 0}
    return dict(sorted(manifest.items()))


def manifest_hash(manifest: dict) -> str:
    joined = "\n".join(rel + "=" + info["sha256"] for rel, info in sorted(manifest.items()))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def tree_hash(root: Path) -> str:
    return manifest_hash(tree_manifest(root))


def tree_stats(manifest: dict) -> dict:
    return {"files": len(manifest), "bytes": sum(int(info.get("size") or 0) for info in manifest.values())}


def copy_tree(src: Path, dst: Path) -> None:
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*VCS_DIRS, *SYSTEM_JUNK, ".aem-tmp*"), dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)


def remove_tree(path: Path) -> None:
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        try:
            path.unlink()
        except OSError:
            path.chmod(0o666)
            path.unlink()
        return

    def _onerror(func, target, exc_info):
        try:
            os.chmod(target, 0o700)
            func(target)
        except OSError:
            pass

    shutil.rmtree(path, onerror=_onerror)


def atomic_replace_dir(staging: Path, destination: Path, backup_dir: Path | None = None) -> None:
    staging = Path(staging)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        if backup_dir is not None:
            backup_dir.mkdir(parents=True, exist_ok=True)
            copy_tree(destination, Path(backup_dir) / destination.name)
        remove_tree(destination)
    os.replace(staging, destination)


def link_tree(src: Path, dst: Path) -> str:
    src = Path(src).resolve()
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        raise FileExistsError(str(dst))
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            return "junction"
        try:
            os.symlink(src, dst, target_is_directory=True)
            return "symlink"
        except OSError as exc:
            raise OSError("link not supported on this system: " + str(exc)) from exc
    os.symlink(src, dst, target_is_directory=True)
    return "symlink"


def is_link(path: Path) -> bool:
    path = Path(path)
    if path.is_symlink():
        return True
    if os.name == "nt" and path.exists():
        try:
            attrs = os.lstat(path).st_file_attributes
            return bool(attrs & 0x400)
        except (AttributeError, OSError):
            return False
    return False

class Home:
    """Central resource library rooted at a user-chosen directory."""

    def __init__(self, path=None):
        self.root = Path(path or os.environ.get("AEM_HOME") or (Path.home() / ".ai-extension-manager")).expanduser()
        self.library = self.root / "library"
        self.metadata = self.root / "metadata"
        self.backups = self.root / "backups"
        self.staging = self.root / "staging"
        self.conflicts = self.root / "conflicts"
        self.logs = self.root / "logs"
        self.registry_path = self.metadata / "registry.json"
        self.agents_path = self.metadata / "agents.json"
        self.history_path = self.metadata / "sync-history.json"

    def ensure(self):
        for folder in (self.library, self.metadata, self.backups, self.staging, self.conflicts, self.logs):
            folder.mkdir(parents=True, exist_ok=True)
        for kind in RESOURCE_TYPES:
            (self.library / kind).mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            write_json_atomic(self.registry_path, {"schema": SCHEMA_VERSION, "resources": {}})
        if not self.agents_path.exists():
            write_json_atomic(self.agents_path, {"schema": SCHEMA_VERSION, "agents": default_agent_configs()})
        if not self.history_path.exists():
            write_json_atomic(self.history_path, {"schema": SCHEMA_VERSION, "events": []})
        return self

    def library_dir(self, kind: str) -> Path:
        return self.library / kind

    def resource_dir(self, kind: str, slug: str) -> Path:
        folder = TYPE_TO_KIND.get(kind, kind)
        return self.library / folder / slug

    @property
    def registry(self) -> dict:
        data = read_json(self.registry_path, None)
        if not isinstance(data, dict):
            data = {"schema": SCHEMA_VERSION, "resources": {}}
        data.setdefault("resources", {})
        return data

    def save_registry(self, data: dict) -> None:
        write_json_atomic(self.registry_path, data)

    def resources(self) -> list:
        return list(self.registry["resources"].values())

    def get_resource(self, rid: str):
        return self.registry["resources"].get(rid)

    def find_resource(self, name_or_id: str):
        registry = self.registry["resources"]
        if name_or_id in registry:
            return registry[name_or_id]
        lowered = name_or_id.lower()
        for record in registry.values():
            if str(record.get("name", "")).lower() == lowered or str(record.get("slug", "")).lower() == lowered:
                return record
        return None

    def upsert_resource(self, record: dict) -> dict:
        data = self.registry
        data["resources"][record["id"]] = record
        self.save_registry(data)
        return record

    def delete_resource(self, rid: str, keep_payload: bool = False) -> bool:
        record = self.get_resource(rid)
        if record is None:
            return False
        data = self.registry
        data["resources"].pop(rid, None)
        self.save_registry(data)
        if not keep_payload:
            remove_tree(self.resource_dir(record["type"], record["slug"]))
        return True

    def history(self) -> dict:
        data = read_json(self.history_path, None)
        if not isinstance(data, dict):
            data = {"schema": SCHEMA_VERSION, "events": []}
        data.setdefault("events", [])
        return data

    def log_event(self, action: str, **details) -> dict:
        event = {"at": utcnow(), "action": action, "tool_version": TOOL_VERSION}
        event.update(details)
        data = self.history()
        data["events"].append(event)
        data["events"] = data["events"][-2000:]
        write_json_atomic(self.history_path, data)
        with open(self.logs / "operations.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event


@contextlib.contextmanager
def library_lock(home: Home, name: str = "library", timeout: float = 20.0):
    home.ensure()
    lock_path = home.metadata / ("." + name + ".lock")
    deadline = time.time() + timeout
    handle = None
    while True:
        try:
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(handle, (str(os.getpid()) + " " + utcnow()).encode())
            break
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except OSError:
                age = 0
            if age > 300:
                with contextlib.suppress(OSError):
                    lock_path.unlink()
                continue
            if time.time() >= deadline:
                raise TimeoutError("another operation holds " + str(lock_path) + "; retry later")
            time.sleep(0.1)
    try:
        yield lock_path
    finally:
        if handle is not None:
            os.close(handle)
        with contextlib.suppress(OSError):
            lock_path.unlink()

def default_agent_configs() -> dict:
    def agent(**kwargs):
        base = {
            "id": "", "label": "", "labels": {}, "cli": [],
            "home_env": None, "home_default": "", "markers": [],
            "skills": {"user": [], "workspace": [], "format": "agent-skills"},
            "plugin": {"supported": "unsupported", "system": "", "manifests": [], "install": "", "cache": []},
            "mcp": {"supported": "no", "configs": [], "notes": ""},
            "rules": {"supported": False, "paths": [], "format": ""},
            "supports": {"global": True, "workspace": True, "autodiscovery": True,
                         "symlink": "unverified", "restart_required": False},
            "docs": "", "verification": "none", "notes": [],
        }
        base.update(kwargs)
        return base

    return {
        "dsh": agent(
            id="dsh", label="DSH", labels={"zh": "DeepSeek Harness"},
            cli=["dsh"], home_env="DSH_HOME", home_default="~/.dsh", markers=["~/.dsh"],
            skills={"user": ["~/.dsh/skills", "~/.agents/skills"],
                    "workspace": [".dsh/skills", ".agents/skills"], "format": "agent-skills"},
            plugin={"supported": "yes", "system": "dsh-bundle", "manifests": ["package.json:dsh"],
                    "install": "dsh plugin --profile {profile} add {package}",
                    "cache": ["~/.dsh/profiles/{profile}/node_modules"], "profile": "desktop"},
            mcp={"supported": "unverified", "configs": [],
                 "notes": "No standalone MCP config file was found on this machine; MCP usually arrives through installed plugins."},
            rules={"supported": True, "paths": ["~/.dsh/AGENTS.md", "~/.agents/AGENTS.md"], "format": "agents-md"},
            docs="https://github.com/MichengAI/dsh-skills-manager#readme", verification="local",
            notes=["DSH loads ~/.dsh/skills and ~/.agents/skills (confirmed by the installed skills manager).",
                   "Plugins are npm packages mounted via dsh plugin --profile <name> add <pkg>; a plugin declares dsh.bundle.patch and/or dsh.client in package.json."],
        ),
        "codex": agent(
            id="codex", label="OpenAI Codex", labels={"zh": "OpenAI Codex"},
            cli=["codex"], home_env="CODEX_HOME", home_default="~/.codex", markers=["~/.codex", "~/.agents"],
            skills={"user": ["~/.codex/skills", "~/.agents/skills"],
                    "workspace": [".agents/skills", ".codex/skills"], "format": "agent-skills"},
            plugin={"supported": "yes", "system": "codex-marketplace",
                    "manifests": ["plugin.json", ".codex-plugin/plugin.json"],
                    "install": "Configure [marketplaces.<id>] and [plugins.\"<name>@<id>\"] in ~/.codex/config.toml, or use the Codex app marketplace UI.",
                    "cache": ["~/.codex/plugins/cache/{marketplace}/{plugin}/{version}"]},
            mcp={"supported": "read+manual",
                 "configs": [{"kind": "toml", "path": "~/.codex/config.toml", "pointer": ["mcp_servers"], "scope": "user"}],
                 "notes": "Codex stores MCP servers in config.toml [mcp_servers.*]; automated writes are not implemented (TOML rewrite risk), use the Codex CLI/app."},
            rules={"supported": True, "paths": ["~/.codex/AGENTS.md", "AGENTS.md"], "format": "agents-md"},
            docs="https://developers.openai.com/codex/", verification="local",
            notes=["~/.codex/skills is populated on this machine; vendor docs also list ~/.agents/skills as the native Codex skill location.",
                   "~/.codex/config.toml contains [mcp_servers.*], [marketplaces.*] and plugin entries; plugin code is cached under ~/.codex/plugins/cache.",
                   "codex CLI was not on PATH here; config-directory detection still reports config-only."],
        ),
        "claude": agent(
            id="claude", label="Claude Code", labels={"zh": "Claude Code"},
            cli=["claude"], home_env="CLAUDE_CONFIG_DIR", home_default="~/.claude", markers=["~/.claude"],
            skills={"user": ["~/.claude/skills"], "workspace": [".claude/skills"], "format": "agent-skills"},
            plugin={"supported": "yes", "system": "claude-marketplace",
                    "manifests": [".claude-plugin/plugin.json"],
                    "install": "claude plugin install <plugin>@<marketplace> (add marketplaces with claude plugin marketplace add <repo>)",
                    "cache": ["~/.claude/plugins/cache/{marketplace}/{plugin}/{version}"]},
            mcp={"supported": "yes", "configs": [
                {"kind": "json", "path": "~/.claude.json", "pointer": ["mcpServers"], "scope": "user"},
                {"kind": "json", "path": ".mcp.json", "pointer": ["mcpServers"], "scope": "workspace"}],
                "notes": "CLI also supports claude mcp add and --mcp-config."},
            rules={"supported": True, "paths": ["~/.claude/CLAUDE.md", "CLAUDE.md"], "format": "claude-md"},
            docs="https://code.claude.com/docs/en/skills", verification="local",
            notes=["CLI 2.1.318 on PATH; claude plugin --help confirmed marketplace-qualified plugin ids.",
                   "~/.claude/plugins/installed_plugins.json + known_marketplaces.json confirmed; plugin caches carry .claude-plugin/plugin.json."],
        ),
        "gemini": agent(
            id="gemini", label="Gemini CLI", labels={"zh": "Gemini CLI"},
            cli=["gemini"], home_env="GEMINI_HOME", home_default="~/.gemini", markers=["~/.gemini"],
            skills={"user": ["~/.gemini/skills", "~/.agents/skills"],
                    "workspace": [".gemini/skills", ".agents/skills"], "format": "agent-skills"},
            plugin={"supported": "yes", "system": "gemini-extension", "manifests": ["gemini-extension.json"],
                    "install": "gemini extensions install <github-url|local-path>",
                    "cache": ["~/.gemini/extensions/{name}"]},
            mcp={"supported": "yes",
                 "configs": [{"kind": "json", "path": "~/.gemini/settings.json", "pointer": ["mcpServers"], "scope": "user"}],
                 "notes": "Extensions may also bundle MCP servers."},
            rules={"supported": True, "paths": ["~/.gemini/GEMINI.md", "GEMINI.md"], "format": "gemini-md"},
            docs="https://geminicli.com/docs/cli/skills", verification="official+partial",
            notes=["Official docs: user skills ~/.gemini/skills or ~/.agents/skills alias; workspace .gemini/skills or .agents/skills.",
                   "Extensions install with gemini extensions install; manifest is gemini-extension.json; extension skills are a discovery tier.",
                   "Not installed on this machine, so runtime behaviour was not exercised."],
        ),
        "cursor": agent(
            id="cursor", label="Cursor", labels={"zh": "Cursor"},
            cli=["cursor"], home_env="CURSOR_HOME", home_default="~/.cursor", markers=["~/.cursor"],
            skills={"user": ["~/.cursor/skills"], "workspace": [".cursor/skills"], "format": "agent-skills"},
            plugin={"supported": "unverified", "system": "cursor-plugin",
                    "manifests": [".cursor-plugin/plugin.json"],
                    "install": "No verified CLI install path; use the Cursor plugin marketplace UI.", "cache": []},
            mcp={"supported": "yes", "configs": [
                {"kind": "json", "path": "~/.cursor/mcp.json", "pointer": ["mcpServers"], "scope": "user"},
                {"kind": "json", "path": ".cursor/mcp.json", "pointer": ["mcpServers"], "scope": "workspace"}],
                "notes": "Paths confirmed by VS Code MCP reference; not exercised locally."},
            rules={"supported": True, "paths": ["~/.cursor/rules", ".cursor/rules"], "format": "cursor-mdc+agents-md"},
            docs="https://cursor.com/docs", verification="partial",
            notes=["Not installed here. ~/.cursor/skills follows the skills-manager path map; Cursor docs could not be fetched from this network.",
                   ".cursor/rules/*.mdc and ~/.cursor/mcp.json are widely documented and appear in VS Code's MCP reference."],
        ),
        "copilot": agent(
            id="copilot", label="VS Code / GitHub Copilot", labels={"zh": "VS Code / GitHub Copilot"},
            cli=["code"], home_env="COPILOT_HOME", home_default="~/.copilot", markers=["~/.copilot", "~/.vscode"],
            skills={"user": ["~/.copilot/skills"], "workspace": [".github/skills"], "format": "agent-skills"},
            plugin={"supported": "yes", "system": "vscode-agent-plugin",
                    "manifests": ["package.json:contributes", ".github/plugin.json"],
                    "install": "VS Code Agent Plugins via the Customization Marketplace; extensions use code --install-extension <vsix>.", "cache": []},
            mcp={"supported": "yes", "configs": [
                {"kind": "json", "path": "~/.copilot/mcp-config.json", "pointer": ["mcpServers"], "scope": "user"},
                {"kind": "json", "path": ".mcp.json", "pointer": ["mcpServers"], "scope": "workspace"}],
                "notes": "Copilot native config; .vscode/mcp.json is the deprecated Local-harness format."},
            rules={"supported": True,
                   "paths": ["~/.copilot/copilot-instructions.md", ".github/copilot-instructions.md", "AGENTS.md", ".github/instructions"],
                   "format": "copilot-instructions+agents-md"},
            docs="https://code.visualstudio.com/docs/agent-customization/agent-skills",
            verification="official+local",
            notes=["Official docs: project .github/skills, personal ~/.copilot/skills.",
                   "~/.copilot/skills exists on this machine; VS Code 1.115.0 is installed."],
        ),
    }


RESOURCE_TYPES = ("skills", "plugins", "mcp", "rules", "other")
TYPE_TO_KIND = {"skill": "skills", "plugin": "plugins", "mcp": "mcp", "rules": "rules", "other": "other"}

def load_agent_configs(home: Home) -> dict:
    # read-only: scanning must not create the central library as a side effect
    data = read_json(home.agents_path, None) or {}
    agents = data.get("agents")
    if not isinstance(agents, dict) or not agents:
        agents = default_agent_configs()
    return agents


def agent_home(agent: dict) -> Path:
    override = os.environ.get("AEM_AGENT_HOME_" + agent["id"].upper())
    if override:
        return expand_path(override)
    if agent.get("home_env") and os.environ.get(agent["home_env"]):
        return expand_path(os.environ[agent["home_env"]])
    return expand_path(agent.get("home_default") or "~")


def probe_version(command: str):
    for args in (["--version"], ["-v"], ["version"]):
        try:
            result = subprocess.run([command] + args, capture_output=True, text=True, timeout=8,
                                    encoding="utf-8", errors="replace")
            lines = (result.stdout or result.stderr or "").strip().splitlines()
            if lines:
                return lines[0][:120]
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def count_skills(path: Path) -> int:
    path = Path(path)
    if not path.is_dir():
        return 0
    total = 0
    for child in path.iterdir():
        try:
            if child.is_dir() and (child / "SKILL.md").exists():
                total += 1
        except OSError:
            continue
    return total


def resolve_agent_path(agent: dict, raw: str, workspace=None, scope: str = "user"):
    """Resolve a configured path, honouring AEM_AGENT_HOME_<ID> overrides."""
    if scope == "workspace" or (raw.startswith(".") and not raw.startswith("~")):
        if workspace is None:
            return None
        return Path(workspace) / raw
    if raw.startswith("~/"):
        parts = raw[2:].split("/")
        default_base = (agent.get("home_default") or "").replace("\\", "/").rstrip("/").split("/")[-1]
        if parts and parts[0] == default_base:
            tail = "/".join(parts[1:])
            return agent_home(agent) / tail if tail else agent_home(agent)
        return expand_path(raw)
    return expand_path(raw)


def detect_agent(agent: dict, workspace=None) -> dict:
    home_dir = agent_home(agent)
    cli_path = None
    cli_version = None
    for command in agent.get("cli") or []:
        found = shutil.which(command)
        if found:
            cli_path = found
            cli_version = probe_version(found)
            break
    markers = [resolve_agent_path(agent, m) for m in agent.get("markers") or []]
    home_exists = any(p is not None and p.exists() for p in markers) or home_dir.exists()
    skills = []
    for scope, paths in (agent.get("skills") or {}).items():
        if scope not in ("user", "workspace"):
            continue
        for raw in paths:
            path = resolve_agent_path(agent, raw, workspace, scope)
            if path is None:
                continue
            skills.append({
                "scope": scope, "path": str(path), "exists": path.exists(),
                "skill_count": count_skills(path) if path.exists() else 0,
            })
    if cli_path:
        status = "installed"
    elif home_exists:
        status = "config-only"
    else:
        status = "absent"
    plugin = agent.get("plugin") or {}
    return {
        "id": agent["id"], "label": agent["label"], "labels": agent.get("labels") or {},
        "status": status, "cli": cli_path, "cli_version": cli_version,
        "home": str(home_dir), "home_exists": home_dir.exists(),
        "skills": skills,
        "plugin_system": plugin.get("system") if plugin.get("supported") in ("yes", "unverified") else None,
        "plugin_supported": plugin.get("supported"),
        "mcp_supported": (agent.get("mcp") or {}).get("supported"),
        "rules_supported": (agent.get("rules") or {}).get("supported"),
        "supports": agent.get("supports") or {},
        "verification": agent.get("verification"),
        "docs": agent.get("docs"),
        "notes": agent.get("notes") or [],
    }


def resolve_agents(home: Home, requested=None) -> list:
    configs = load_agent_configs(home)
    ids = requested or list(configs.keys())
    return [configs[agent_id] for agent_id in ids if agent_id in configs]


FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", re.DOTALL)


def unquote_scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def parse_frontmatter(text: str) -> dict:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = {}
    current_key = None
    for raw_line in match.group(1).splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        line = raw_line.rstrip()
        nested = re.match(r"^\s+([A-Za-z0-9_.-]+)\s*:\s*(.*)$", line)
        top = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", line)
        if nested and current_key:
            if isinstance(data.get(current_key), dict):
                data[current_key][nested.group(1)] = unquote_scalar(nested.group(2).strip())
            continue
        if top:
            key, value = top.group(1), top.group(2).strip()
            current_key = key
            if value == "":
                data[key] = {}
            elif value.startswith("[") and value.endswith("]"):
                data[key] = [unquote_scalar(v.strip()) for v in value[1:-1].split(",") if v.strip()]
            else:
                data[key] = unquote_scalar(value)
    return data


SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_skill_dir(path: Path, folder_name=None) -> dict:
    path = Path(path)
    skill_md = path / "SKILL.md"
    result = {"valid": False, "errors": [], "warnings": [], "meta": {}, "name": None}
    if not skill_md.exists():
        result["errors"].append("SKILL.md is missing")
        return result
    text = read_text(skill_md, 64 * 1024)
    meta = parse_frontmatter(text)
    result["meta"] = meta
    name = meta.get("name") if isinstance(meta.get("name"), str) else None
    description = meta.get("description") if isinstance(meta.get("description"), str) else ""
    folder = folder_name or path.name
    if not name:
        result["errors"].append("frontmatter name is missing")
    else:
        result["name"] = name
        if not SKILL_NAME_RE.match(name):
            result["errors"].append("frontmatter name " + name + " is not kebab-case")
        if name != folder:
            result["warnings"].append("frontmatter name " + name + " does not match directory " + folder + "; some tools will not load it")
    if not description:
        result["errors"].append("frontmatter description is missing")
    elif len(description) > 1024:
        result["errors"].append("frontmatter description exceeds 1024 characters")
    if not text.startswith("---"):
        result["errors"].append("SKILL.md does not start with YAML frontmatter")
    if "<" in description or ">" in description:
        result["warnings"].append("description contains angle brackets; some validators reject it")
    body = FRONTMATTER_RE.sub("", text).strip()
    if not body:
        result["warnings"].append("SKILL.md has no instructions after the frontmatter")
    result["valid"] = not result["errors"]
    return result

PLUGIN_MANIFESTS = {
    "claude": [".claude-plugin/plugin.json"],
    "cursor": [".cursor-plugin/plugin.json"],
    "kimi": [".kimi-plugin/plugin.json"],
    "codex": [".codex-plugin/plugin.json", "plugin.json"],
    "vscode": [".vscode-plugin/plugin.json", ".github/plugin.json"],
    "generic": ["plugin.json", ".plugin/plugin.json"],
}


def looks_like_plugin(path: Path) -> list:
    path = Path(path)
    evidence = []
    for tool, manifests in PLUGIN_MANIFESTS.items():
        for manifest in manifests:
            if (path / manifest).is_file():
                evidence.append(tool + ":" + manifest)
    package_json = path / "package.json"
    if package_json.is_file():
        data = read_json(package_json, {}) or {}
        if isinstance(data, dict):
            if isinstance(data.get("dsh"), dict):
                evidence.append("dsh:package.json#dsh")
            contributes = data.get("contributes")
            if isinstance(contributes, dict) and ("chatSkills" in contributes or "chatPlugins" in contributes):
                evidence.append("vscode:package.json#contributes")
            if "deepseek-harness" in (data.get("keywords") or []):
                evidence.append("dsh:keyword")
    if (path / ".claude-plugin" / "marketplace.json").is_file():
        evidence.append("marketplace:claude")
    if (path / "gemini-extension.json").is_file():
        evidence.append("gemini:gemini-extension.json")
    return evidence


def looks_like_mcp_config(path: Path) -> bool:
    path = Path(path)
    if not path.is_file():
        return False
    if path.suffix.lower() not in (".json", ".toml"):
        return False
    if path.suffix.lower() == ".json":
        data = read_json(path, None)
        if not isinstance(data, dict):
            return False
        return any(key in data for key in ("mcpServers", "mcp_servers", "servers"))
    text = read_text(path, 512 * 1024)
    return "[mcp_servers" in text or "[mcp.servers" in text


RULE_FILENAMES = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "copilot-instructions.md", ".cursorrules"}
RULE_PATTERNS = (re.compile(r".*\.instructions\.md$"), re.compile(r".*\.mdc$"))


def looks_like_rules(path: Path) -> bool:
    path = Path(path)
    if path.is_file():
        name = path.name
        return name in RULE_FILENAMES or any(pattern.match(name) for pattern in RULE_PATTERNS)
    if path.is_dir() and path.name in ("rules", "instructions"):
        try:
            return any(child.is_file() for child in path.iterdir())
        except OSError:
            return False
    return False


def plugin_display_name(path: Path) -> str:
    for manifest in (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json", "plugin.json", "gemini-extension.json"):
        data = read_json(Path(path) / manifest, None)
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            return data["name"]
    package = read_json(Path(path) / "package.json", None)
    if isinstance(package, dict) and isinstance(package.get("name"), str):
        return package["name"]
    return Path(path).name


def classify_path(path: Path) -> dict:
    path = Path(path)
    result = {"path": str(path), "type": None, "confidence": "none", "evidence": [],
              "name": path.name, "validation": {}, "issues": []}
    if not path.exists():
        result["issues"].append("path does not exist")
        return result
    plugin_evidence = looks_like_plugin(path) if path.is_dir() else []
    if path.is_dir() and (path / "SKILL.md").is_file():
        validation = validate_skill_dir(path)
        result["validation"] = validation
        result["name"] = validation.get("name") or path.name
        result["type"] = "skill"
        result["confidence"] = "high"
        result["evidence"].append("SKILL.md with YAML frontmatter")
        result["issues"].extend(validation.get("errors", []))
        if plugin_evidence:
            result["issues"].append("directory contains both SKILL.md and plugin manifests; importing as skill only")
        return result
    if plugin_evidence:
        result["type"] = "plugin"
        result["confidence"] = "high"
        result["evidence"].extend(plugin_evidence)
        result["name"] = plugin_display_name(path)
        return result
    if looks_like_mcp_config(path):
        result["type"] = "mcp"
        result["confidence"] = "high"
        result["evidence"].append("file contains mcp server definitions")
        result["name"] = path.stem
        return result
    if looks_like_rules(path):
        result["type"] = "rules"
        result["confidence"] = "medium"
        result["evidence"].append("known instructions/rules filename or directory")
        return result
    if path.is_dir():
        result["issues"].append("directory is not itself a resource; scan children")
    else:
        result["issues"].append("file is not a recognised resource")
    result["type"] = "other"
    result["confidence"] = "low"
    return result


def discover_candidates(root: Path, depth: int = 3) -> list:
    root = Path(root)
    found = []
    if not root.exists():
        return found
    direct = classify_path(root)
    if direct["type"] in ("skill", "mcp") or (direct["type"] == "plugin" and not root.is_dir()):
        found.append(direct)
        return found
    root_depth = len(root.parts)
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        if len(current_path.parts) - root_depth >= depth:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if d not in VCS_DIRS and d not in ("node_modules", "dist", "build")]
        if (current_path / "SKILL.md").is_file():
            found.append(classify_path(current_path))
            dirnames[:] = []
            continue
        if looks_like_plugin(current_path):
            found.append(classify_path(current_path))
            dirnames[:] = []
            continue
        for name in filenames:
            candidate = current_path / name
            info = classify_path(candidate)
            if info["type"] in ("mcp", "rules"):
                found.append(info)
    seen = set()
    unique = []
    for item in found:
        key = str(Path(item["path"]).resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique

SAFETY_RULES = [
    ("high", re.compile(r"rm\s+-rf\s+(?:/|~|\$HOME|[A-Za-z]:\\)", re.I), "recursive delete of root/home"),
    ("high", re.compile(r"Remove-Item\b[^\n]*-Recurse[^\n]*-Force", re.I), "recursive force delete"),
    ("high", re.compile(r"curl\b[^\n|]*\|\s*(?:ba)?sh", re.I), "pipe download into shell"),
    ("high", re.compile(r"(?:wget|iwr|Invoke-WebRequest|curl)[^\n]*(?:\|\s*(?:iex|Invoke-Expression))", re.I), "download and execute in memory"),
    ("high", re.compile(r"Invoke-Expression|iex\s*\(", re.I), "PowerShell Invoke-Expression"),
    ("high", re.compile(r"base64\s+(?:-d|--decode)[^\n]*\|\s*(?:ba)?sh", re.I), "base64 payload piped to shell"),
    ("high", re.compile(r"\b(?:schtasks|reg\s+add)\b[^\n]*(?:/create|Run)", re.I), "persistence via scheduled task/registry"),
    ("high", re.compile(r"(?:/etc/shadow|\.ssh/id_|\.aws/credentials|\.claude/\.credentials|\.codex/auth\.json|Login Data|keychain)", re.I), "credential file access"),
    ("high", re.compile(r"(?:child_process|subprocess)[^\n]*(?:shell\s*=\s*True|execSync)", re.I), "shell execution from script"),
    ("medium", re.compile(r"\b(?:sudo|runas)\b", re.I), "privilege escalation"),
    ("medium", re.compile(r"\b(?:npm|pnpm|yarn|pip|pipx|uv)\s+(?:install|add)\b", re.I), "installs packages at runtime"),
    ("medium", re.compile(r"\bgit\s+clone\b", re.I), "clones remote code"),
    ("medium", re.compile(r"\beval\s*\(", re.I), "dynamic code evaluation"),
    ("low", re.compile(r"chmod\s+(?:777|a\+rwx)", re.I), "world-writable permissions"),
]

SECRET_PATTERNS = [
    ("openai", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("anthropic", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("github", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("aws", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("google", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    ("slack", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer", re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}")),
]

BINARY_MAGIC = (b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xce")


def scan_safety(root: Path, max_files: int = 300, max_bytes: int = 256 * 1024) -> dict:
    root = Path(root)
    findings = []
    scanned = 0
    binaries = []
    secrets = []
    for file_path in iter_payload_files(root):
        if scanned >= max_files:
            break
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        if size > max_bytes:
            continue
        try:
            head = file_path.read_bytes()[:4]
        except OSError:
            continue
        if size > 0 and any(head.startswith(magic) for magic in BINARY_MAGIC):
            binaries.append(file_path.name if root.is_file() else file_path.relative_to(root).as_posix())
        if not text_like(head):
            continue
        text = read_text(file_path, max_bytes)
        if not text:
            continue
        scanned += 1
        rel = file_path.name if root.is_file() else file_path.relative_to(root).as_posix()
        for severity, pattern, label in SAFETY_RULES:
            match = pattern.search(text)
            if not match:
                continue
            snippet = text[max(0, match.start() - 40): match.end() + 40].replace("\n", " ")
            findings.append({"severity": severity, "rule": label, "file": rel,
                             "line": text[: match.start()].count("\n") + 1, "snippet": snippet[:160]})
        for name, pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                value = match.group(0)
                secrets.append({"kind": name, "file": rel,
                                "preview": (value[:6] + "..." + value[-2:]) if len(value) > 10 else "***"})
    counts = {"high": 0, "medium": 0, "low": 0}
    for item in findings:
        counts[item["severity"]] += 1
    risk = "high" if counts["high"] else ("medium" if counts["medium"] else "low")
    return {
        "risk": risk, "counts": counts, "findings": findings[:60],
        "binaries": binaries, "secrets": secrets, "files_scanned": scanned,
        "requires_confirmation": risk in ("high", "medium") or bool(binaries) or bool(secrets),
    }


def text_like(head: bytes) -> bool:
    if not head:
        return True
    if any(head.startswith(magic) for magic in BINARY_MAGIC):
        return False
    control = sum(1 for byte in head if byte < 9 or (13 < byte < 32))
    return control == 0


def looks_secret_key(key: str) -> bool:
    return bool(re.search(r"(api[_-]?key|token|secret|password|passwd|credential|auth[_-]?key|private[_-]?key)",
                          str(key), re.I))


def redact_mapping(mapping: dict):
    clean = {}
    placeholders = []
    dollar = chr(36)
    for key, value in (mapping or {}).items():
        if isinstance(value, dict):
            nested, nested_placeholders = redact_mapping(value)
            clean[key] = nested
            placeholders.extend(nested_placeholders)
            continue
        if isinstance(value, str):
            if value.startswith(dollar + "{") and value.endswith("}"):
                clean[key] = value
                continue
            if looks_secret_key(key) or any(pattern.search(value) for _, pattern in SECRET_PATTERNS):
                env_name = re.sub(r"[^A-Z0-9]+", "_", str(key).upper()).strip("_") or "SECRET"
                clean[key] = dollar + "{" + env_name + "}"
                placeholders.append({"key": key, "env": env_name})
                continue
        clean[key] = value
    return clean, placeholders

STATE_DESCRIPTIONS = {
    "in-sync": "library and target are identical",
    "A": "only the central library changed since the last sync",
    "B": "only the target tool changed since the last sync",
    "C": "both the library and the target changed (manual merge needed)",
    "D": "the target copy was deleted or is incomplete",
    "E": "the target directory does not exist",
    "untracked": "the target has a copy that was never imported/synced",
}


def compute_target_state(record: dict, target, actual_hash, exists: bool, library_hash=None) -> dict:
    """Classify one target copy against the library.

    library_hash must be the *current* payload hash when the caller can compute it.
    Passing only record["hash"] would miss edits made directly inside the central
    library and could misreport state C as state B (then let an import overwrite the
    library-side change).
    """
    if not exists:
        state = "D" if target else "E"
        return {"state": state, "description": STATE_DESCRIPTIONS[state]}
    if not target:
        if actual_hash and actual_hash == (library_hash or record.get("hash")):
            return {"state": "in-sync", "description": "target copy is identical to the library (not yet recorded)"}
        return {"state": "untracked", "description": STATE_DESCRIPTIONS["untracked"]}
    recorded_source = target.get("source_hash")
    recorded_target = target.get("target_hash")
    library_hash = library_hash or record.get("hash")
    if actual_hash and actual_hash == library_hash:
        return {"state": "in-sync", "description": STATE_DESCRIPTIONS["in-sync"]}
    library_unchanged = recorded_source == library_hash
    target_unchanged = actual_hash == recorded_target
    if library_unchanged and target_unchanged:
        return {"state": "A", "description": STATE_DESCRIPTIONS["A"]}
    if library_unchanged:
        return {"state": "B", "description": STATE_DESCRIPTIONS["B"]}
    if target_unchanged:
        return {"state": "A", "description": STATE_DESCRIPTIONS["A"]}
    return {"state": "C", "description": STATE_DESCRIPTIONS["C"]}


def make_resource_id(kind: str, name: str, existing: dict) -> str:
    base = kind + "/" + slugify(name)
    if base not in existing:
        return base
    index = 2
    while base + "-" + str(index) in existing:
        index += 1
    return base + "-" + str(index)


def version_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y.%m.%d-%H%M%S")


def build_record(kind: str, name: str, payload: Path, source: dict, slug=None,
                 version=None, safety=None, validation=None) -> dict:
    manifest = tree_manifest(payload)
    stats = tree_stats(manifest)
    slug = slug or slugify(name)
    stamp = utcnow()
    return {
        "id": kind + "/" + slug, "type": kind, "name": name, "slug": slug,
        "version": version or version_label(), "hash": manifest_hash(manifest),
        "manifest": manifest, "files": stats["files"], "bytes": stats["bytes"],
        "source": source, "created_at": stamp, "updated_at": stamp,
        "supported_agents": [], "targets": {}, "sync_mode": "copy", "status": "active",
        "dependencies": [], "safety": safety or {}, "validation": validation or {},
        "versions": [], "notes": [],
    }


def next_version_dir(resource_dir: Path) -> str:
    versions = Path(resource_dir) / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    candidate = stamp
    index = 1
    while (versions / candidate).exists():
        index += 1
        candidate = stamp + "-" + str(index)
    return candidate


def save_version_snapshot(home: Home, record: dict, note: str = "") -> str:
    resource_dir = home.resource_dir(record["type"], record["slug"])
    payload = resource_dir / "payload"
    if not payload.exists():
        return ""
    label = next_version_dir(resource_dir)
    destination = resource_dir / "versions" / label / "payload"
    copy_tree(payload, destination)
    entry = {"version": record.get("version"), "hash": record.get("hash"), "label": label,
             "created_at": utcnow(), "note": note}
    record.setdefault("versions", []).append(entry)
    write_json_atomic(resource_dir / "versions" / label / "version.json", entry)
    return label


def write_resource_files(home: Home, record: dict) -> None:
    resource_dir = home.resource_dir(record["type"], record["slug"])
    resource_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(resource_dir / "resource.json", record)


def skill_supports(agent: dict) -> bool:
    return bool((agent.get("skills") or {}).get("user"))


def compat_check(record: dict, agent: dict) -> dict:
    kind = record["type"]
    agent_id = agent["id"]
    if kind == "skill":
        if not skill_supports(agent):
            return {"compatible": False, "reason": agent["label"] + " has no verified Agent Skills directory"}
        return {"compatible": True, "reason": "Agent Skills is portable across these tools"}
    if kind == "plugin":
        plugin = agent.get("plugin") or {}
        if plugin.get("supported") not in ("yes", "unverified"):
            return {"compatible": False, "reason": agent["label"] + " has no verified plugin mechanism"}
        if plugin.get("supported") == "unverified":
            return {"compatible": False, "reason": agent["label"] + " plugin installation is unverified; install manually"}
        supported = record.get("supported_agents") or []
        if supported and agent_id not in supported:
            return {"compatible": False,
                    "reason": "plugin was packaged for " + str(supported) + ", not for " + agent_id + "; per-tool plugins are not portable"}
        return {"compatible": True, "requires_command": True,
                "reason": "install through " + str(plugin.get("system")) + ": " + str(plugin.get("install"))}
    if kind == "mcp":
        mcp = agent.get("mcp") or {}
        configs = mcp.get("configs") or []
        writable = [c for c in configs if c.get("kind") == "json" and c.get("scope") in ("user", "workspace")]
        if mcp.get("supported") == "no" or not configs:
            return {"compatible": False, "reason": agent["label"] + " has no verified MCP config location"}
        if not writable:
            return {"compatible": False,
                    "reason": agent["label"] + " MCP config needs manual editing: " + str(mcp.get("notes"))}
        return {"compatible": True, "config": writable[0],
                "reason": "merge mcpServers into " + str(writable[0]["path"])}
    if kind == "rules":
        rules = agent.get("rules") or {}
        if not rules.get("supported"):
            return {"compatible": False, "reason": agent["label"] + " has no verified rules location"}
        return {"compatible": True, "paths": rules.get("paths"),
                "reason": "place under " + str(rules.get("format")) + " locations"}
    return {"compatible": False, "reason": "resource type " + kind + " has no automated distribution path"}


def summarize_counts(items: list, key: str) -> dict:
    counts = {}
    for item in items:
        value = item.get(key)
        counts[value] = counts.get(value, 0) + 1
    return counts


def exit_code_for(result: dict) -> int:
    if result.get("conflicts"):
        return 2
    if result.get("errors"):
        return 1
    return 0

# ---------------------------------------------------------------------------
# CLI helpers and target resolution
# ---------------------------------------------------------------------------

import argparse


def common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--home", default=None, help="central library root (default: $AEM_HOME or ~/.ai-extension-manager)")
    parser.add_argument("--workspace", default=None, help="workspace root for project-scoped resources")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    return parser


def resolve_home(args) -> Home:
    return Home(getattr(args, "home", None)).ensure()


def workspace_path(args):
    value = getattr(args, "workspace", None)
    return Path(value).expanduser().resolve() if value else None


def output(result: dict, args, human_lines=None) -> None:
    if getattr(args, "json", False):
        emit_json(result)
        return
    for line in human_lines or []:
        print(line)
    if not human_lines:
        print(pj(result))


def skill_target_for(agent: dict, workspace=None, scope: str = "user") -> dict:
    skills = agent.get("skills") or {}
    candidates = skills.get(scope) or []
    if not candidates:
        return {"ok": False, "reason": agent.get("label", agent.get("id")) + " has no " + scope + "-scope skills directory"}
    raw = candidates[0]
    base = resolve_agent_path(agent, raw, workspace, scope)
    if base is None:
        return {"ok": False, "reason": "workspace scope requested without --workspace"}
    return {"ok": True, "root": base, "scope": scope, "all_candidates": candidates}


def target_for(record: dict, agent: dict, workspace=None, scope: str = "user") -> dict:
    kind = record["type"]
    if kind == "skill":
        info = skill_target_for(agent, workspace, scope)
        if not info["ok"]:
            return info
        return {"ok": True, "kind": "dir", "path": info["root"] / record["slug"],
                "root": info["root"], "scope": scope}
    if kind == "plugin":
        plugin = agent.get("plugin") or {}
        command = str(plugin.get("install") or "")
        package = record.get("package") or record.get("name") or record.get("slug")
        command = command.replace("{profile}", str(plugin.get("profile") or "desktop"))
        command = command.replace("{package}", str(package))
        return {"ok": False, "reason": "plugins are installed through " + str(plugin.get("system")),
                "manual": True, "install": command, "cache": plugin.get("cache")}
    if kind == "mcp":
        mcp = agent.get("mcp") or {}
        configs = [c for c in (mcp.get("configs") or []) if c.get("kind") == "json"]
        if not configs:
            return {"ok": False, "reason": agent.get("label") + " has no JSON MCP config"}
        chosen = None
        for config in configs:
            if config.get("scope") == scope:
                chosen = config
                break
        chosen = chosen or configs[0]
        raw = chosen["path"]
        resolved_scope = chosen.get("scope") or scope
        path = resolve_agent_path(agent, raw, workspace, resolved_scope)
        if path is None:
            return {"ok": False, "reason": "workspace MCP config requested without --workspace"}
        server_name = mcp_server_name(record)
        return {"ok": True, "kind": "mcp", "path": path, "scope": chosen.get("scope"),
                "pointer": chosen.get("pointer") or ["mcpServers"], "server": server_name}
    if kind == "rules":
        raw_paths = (agent.get("rules") or {}).get("paths") or []
        for raw in raw_paths:
            path = resolve_agent_path(agent, raw, workspace, "workspace" if raw.startswith(".") else "user")
            if path is None:
                continue
            return {"ok": True, "kind": "rules", "path": path, "raw": raw,
                    "is_dir": raw.endswith("rules") or raw.endswith("instructions") or path.is_dir()}
        return {"ok": False, "reason": agent.get("label") + " has no resolvable rules path"}
    return {"ok": False, "reason": "unsupported resource type " + str(kind)}


def mcp_server_name(record: dict) -> str:
    info = record.get("mcp") or {}
    if isinstance(info.get("server"), str):
        return info["server"]
    return record["slug"]


def mcp_server_config(record: dict) -> dict:
    info = record.get("mcp") or {}
    if isinstance(info.get("config"), dict):
        return info["config"]
    return {}


def payload_path(home: Home, record: dict) -> Path:
    return home.resource_dir(record["type"], record["slug"]) / "payload"


def backup_target(home: Home, agent_id: str, record: dict, source: Path, reason: str) -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = home.backups / (stamp + "-" + record["type"] + "-" + record["slug"] + "-" + agent_id)
    copy_tree(source, destination / "payload")
    manifest = tree_manifest(source)
    entry = {
        "backup_id": destination.name, "reason": reason, "agent": agent_id,
        "resource_id": record["id"], "resource_version": record.get("version"),
        "source_path": str(source), "hash": record.get("hash"),
        "target_hash": manifest_hash(manifest), "created_at": utcnow(),
        "files": len(manifest), "bytes": tree_stats(manifest)["bytes"],
    }
    write_json_atomic(destination / "manifest.json", entry)
    home.log_event("backup", backup_id=entry["backup_id"], resource_id=record["id"], agent=agent_id, reason=reason)
    return entry


def record_conflict(home: Home, record: dict, agent: dict, info: dict) -> dict:
    conflict = {
        "id": record["id"] + "@" + agent["id"],
        "resource_id": record["id"],
        "resource_name": record.get("name"),
        "agent": agent["id"],
        "agent_label": agent.get("label"),
        "state": info.get("state"),
        "description": info.get("description"),
        "detected_at": utcnow(),
        "library": {"version": record.get("version"), "hash": record.get("hash"),
                    "path": str(payload_path(home, record))},
        "target": info.get("target"),
        "resolution_options": ["keep-library", "keep-target", "manual-merge", "save-as-new-version"],
        "resolved": False,
    }
    write_json_atomic(home.conflicts / (slugify(record["slug"]) + "-" + agent["id"] + ".json"), conflict)
    home.log_event("conflict-detected", resource_id=record["id"], agent=agent["id"], state=info.get("state"))
    return conflict


def install_payload(home: Home, record: dict, agent: dict, *, workspace=None, scope="user",
                    mode="copy", on_conflict="skip", dry_run=False, force=False) -> dict:
    """Install or update one resource in one agent. Returns an action report."""
    compat = compat_check(record, agent)
    if not compat["compatible"]:
        return {"resource": record["id"], "agent": agent["id"], "action": "blocked",
                "reason": compat["reason"]}
    target = target_for(record, agent, workspace, scope)
    if not target.get("ok"):
        if target.get("manual"):
            inventory = plugin_inventory(agent)
            return {"resource": record["id"], "agent": agent["id"], "action": "manual",
                    "reason": target.get("reason"), "install": target.get("install"),
                    "installed_plugins": plugin_version_drift(inventory, record)}
        return {"resource": record["id"], "agent": agent["id"], "action": "unavailable",
                "reason": target.get("reason")}
    payload = payload_path(home, record)
    if not payload.exists():
        return {"resource": record["id"], "agent": agent["id"], "action": "error",
                "reason": "library payload is missing: " + str(payload)}
    kind = record["type"]
    if kind == "skill":
        return _install_dir_resource(home, record, agent, payload, target, mode, on_conflict, dry_run, force)
    if kind == "mcp":
        return _install_mcp(home, record, agent, target, on_conflict, dry_run)
    if kind == "rules":
        return _install_rules(home, record, agent, payload, target, on_conflict, dry_run)
    return {"resource": record["id"], "agent": agent["id"], "action": "blocked",
            "reason": "no installer for " + kind}


def _install_dir_resource(home, record, agent, payload, target, mode, on_conflict, dry_run, force) -> dict:
    agent_id = agent["id"]
    destination: Path = target["path"]
    recorded = (record.get("targets") or {}).get(agent_id)
    exists = destination.exists()
    actual_hash = tree_hash(destination) if exists and destination.is_dir() else None
    library_hash = tree_hash(payload)
    base = {"resource": record["id"], "agent": agent_id, "path": str(destination),
            "mode": mode, "scope": target.get("scope")}
    if is_link(destination):
        try:
            resolved = Path(destination).resolve()
            if is_within(resolved, payload):
                target_hash = tree_hash(payload)
                return dict(base, action="skip", state="in-sync", reason="already linked to the library")
        except OSError:
            pass
    if not recorded and exists:
        if actual_hash and actual_hash == library_hash:
            if not dry_run:
                _record_target(home, record, agent, target, mode, "adopt")
            return dict(base, action="adopt", state="in-sync", reason="target already identical; recorded without writing")
        state = {"state": "untracked", "description": STATE_DESCRIPTIONS["untracked"],
                 "target": {"path": str(destination), "hash": actual_hash}}
        if on_conflict in ("library", "overwrite") or force:
            pass
        elif on_conflict == "target":
            return dict(base, action="kept-target", state="untracked",
                        reason="explicitly keeping the untracked target copy")
        else:
            if not dry_run:
                record_conflict(home, record, agent, state)
            return dict(base, action="conflict", state="untracked",
                        reason="target exists with different content and was never tracked")
    elif not recorded and not exists:
        if not destination.parent.exists():
            # A tool whose home exists but has never created its skills folder can
            # still receive a resource: the common install path below creates the
            # parent. An absent tool is different and must never be written to.
            if not agent_home(agent).exists():
                return dict(base, action="unavailable", state="E",
                            reason="tool home does not exist for " + agent_id + ": " + str(agent_home(agent)))
    else:
        state = compute_target_state(record, recorded, actual_hash, exists, library_hash=library_hash)
        if state["state"] == "in-sync" and recorded.get("mode") == mode:
            return dict(base, action="skip", state="in-sync", reason=state["description"])
        if state["state"] == "B" and on_conflict == "target":
            return dict(base, action="kept-target", state="B",
                        reason="explicitly keeping the target copy; import it to make it the library version")
        if state["state"] == "B" and on_conflict not in ("library", "overwrite") and not force:
            info = dict(state, target={"path": str(destination), "hash": actual_hash})
            if not dry_run:
                record_conflict(home, record, agent, info)
            return dict(base, action="conflict", state="B",
                        reason="target changed since last sync; import it or pass --on-conflict library")
        if state["state"] == "C" and on_conflict == "target":
            return dict(base, action="kept-target", state="C",
                        reason="explicitly keeping the target copy; run the import direction to capture it")
        if state["state"] == "C" and on_conflict not in ("library", "overwrite") and not force:
            info = dict(state, target={"path": str(destination), "hash": actual_hash})
            if not dry_run:
                record_conflict(home, record, agent, info)
            return dict(base, action="conflict", state="C",
                        reason="both sides changed; resolve the conflict first")
        if state["state"] == "A" and mode == "copy" and force is False:
            pass  # library-only change: safe to update after backup
    if dry_run:
        return dict(base, action="would-install", reason="dry run")
    backup = None
    if exists and not is_link(destination):
        backup = backup_target(home, agent_id, record, destination, "pre-" + mode)["backup_id"]
    if is_link(destination):
        remove_tree(destination)
    staging = home.staging / ("install-" + slugify(record["slug"]) + "-" + agent_id + "-" + uuid.uuid4().hex[:6])
    remove_tree(staging)
    try:
        if mode == "link":
            if exists:
                remove_tree(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            mechanism = link_tree(payload, destination)
            written_hash = tree_hash(destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            copy_tree(payload, staging / "payload")
            atomic_replace_dir(staging / "payload", destination, None)
            written_hash = tree_hash(destination)
    except (OSError, shutil.Error) as exc:
        remove_tree(staging)
        return dict(base, action="error", reason="write failed: " + str(exc))
    remove_tree(staging)
    if written_hash != library_hash:
        return dict(base, action="error", reason="post-write hash mismatch",
                    expected=library_hash, actual=written_hash, backup=backup)
    if library_hash != record.get("hash"):
        # The library payload was edited outside the import pipeline; adopt the
        # current payload hash so target records and future state checks are honest.
        refresh_library_hash(home, record, payload, library_hash)
    _record_target(home, record, agent, target, mode, "install", written_hash)
    return dict(base, action="install", state="in-sync", backup=backup, hash=written_hash,
                files=record.get("files"))


def refresh_library_hash(home, record, payload, current_hash=None) -> str:
    """Recompute a skill record's hash/manifest from its payload after an out-of-band edit."""
    manifest = tree_manifest(payload)
    current_hash = current_hash or manifest_hash(manifest)
    stats = tree_stats(manifest)
    record["hash"] = current_hash
    record["manifest"] = manifest
    record["files"] = stats["files"]
    record["bytes"] = stats["bytes"]
    record["updated_at"] = utcnow()
    home.upsert_resource(record)
    return current_hash


def _record_target(home, record, agent, target, mode, action, written_hash=None) -> None:
    record.setdefault("targets", {})[agent["id"]] = {
        "agent": agent["id"],
        "scope": target.get("scope"),
        "path": str(target["path"]),
        "mode": mode,
        "source_hash": record["hash"],
        "target_hash": written_hash or record["hash"],
        "version": record.get("version"),
        "synced_at": utcnow(),
        "last_action": action,
    }
    record["updated_at"] = utcnow()
    home.upsert_resource(record)
    write_resource_files(home, record)


def _install_mcp(home, record, agent, target, on_conflict, dry_run) -> dict:
    config_path: Path = target["path"]
    pointer = target.get("pointer") or ["mcpServers"]
    server_name = target["server"]
    entry = mcp_server_config(record)
    current = read_json(config_path, {}) if config_path.exists() else {}
    if not isinstance(current, dict):
        return {"resource": record["id"], "agent": agent["id"], "action": "error",
                "reason": "target config is not a JSON object: " + str(config_path)}
    container = current
    for key in pointer:
        container = container.setdefault(key, {}) if isinstance(container, dict) else {}
    existing = container.get(server_name) if isinstance(container, dict) else None
    base = {"resource": record["id"], "agent": agent["id"], "path": str(config_path),
            "server": server_name}
    if existing is not None:
        if existing == entry:
            return dict(base, action="skip", state="in-sync", reason="server entry already identical")
        if on_conflict not in ("library", "overwrite"):
            info = {"state": "C", "description": "MCP server entry exists with different settings",
                    "target": {"path": str(config_path), "hash": short_hash(pj(existing))}}
            if not dry_run:
                record_conflict(home, record, agent, info)
            return dict(base, action="conflict", state="C",
                        reason="MCP server entry differs; pass --on-conflict library to replace")
    if dry_run:
        return dict(base, action="would-install", reason="dry run")
    backup = None
    if config_path.exists():
        backup = backup_target(home, agent["id"], record, config_path, "pre-mcp")["backup_id"]
    merged = read_json(config_path, {}) if config_path.exists() else {}
    if not isinstance(merged, dict):
        merged = {}
    node = merged
    for key in pointer:
        node = node.setdefault(key, {})
    node[server_name] = entry
    write_json_atomic(config_path, merged)
    _record_mcp_target(home, record, agent, target, entry, backup)
    return dict(base, action="install", state="in-sync", backup=backup)


def _record_mcp_target(home, record, agent, target, entry, backup) -> None:
    record.setdefault("targets", {})[agent["id"]] = {
        "agent": agent["id"], "scope": target.get("scope"), "path": str(target["path"]),
        "mode": "mcp", "source_hash": record["hash"], "entry_hash": short_hash(pj(entry)),
        "version": record.get("version"), "synced_at": utcnow(), "last_action": "install",
        "backup": backup,
    }
    record["updated_at"] = utcnow()
    home.upsert_resource(record)
    write_resource_files(home, record)


def _install_rules(home, record, agent, payload, target, on_conflict, dry_run) -> dict:
    destination: Path = target["path"]
    source_file = payload
    if payload.is_dir():
        files = [f for f in iter_payload_files(payload)]
        source_file = files[0] if files else payload
    base = {"resource": record["id"], "agent": agent["id"], "path": str(destination)}
    if target.get("is_dir"):
        suffix = ".mdc" if "cursor-mdc" in str((agent.get("rules") or {}).get("format")) else ".md"
        destination = destination / (record["slug"] + suffix)
        base["path"] = str(destination)
        if destination.exists():
            existing = sha256_file(destination)
            expected = (record.get("content") or {}).get("sha256")
            if expected and existing == expected:
                _record_rules_target(home, record, agent, destination, expected, "dir")
                return dict(base, action="skip", state="in-sync")
            if on_conflict not in ("library", "overwrite"):
                info = {"state": "C", "description": "rule file exists with different content",
                        "target": {"path": str(destination), "hash": existing}}
                if not dry_run:
                    record_conflict(home, record, agent, info)
                return dict(base, action="conflict", state="C", reason="rule file differs")
        if dry_run:
            return dict(base, action="would-install", reason="dry run")
        backup = None
        if destination.exists():
            backup = backup_target(home, agent["id"], record, destination, "pre-rules")["backup_id"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy_tree(source_file, destination)
        _record_rules_target(home, record, agent, destination, expected, "dir")
        return dict(base, action="install", state="in-sync", backup=backup,
                    note="rule file placed without touching other rule files")
    # Single shared file (AGENTS.md / CLAUDE.md / GEMINI.md): never overwrite.
    expected = (record.get("content") or {}).get("sha256") or ""
    marker = "<!-- ai-extension-manager:" + record["slug"] + " hash:" + expected[:12] + " -->"
    if destination.exists():
        text = read_text(destination)
        if marker in text:
            _record_rules_target(home, record, agent, destination, expected, "shared-file")
            return dict(base, action="skip", state="in-sync", note="managed block already present")
        return dict(base, action="manual", state="manual",
                    reason="shared instruction file exists; append the managed block manually",
                    marker=marker, source=str(source_file))
    if dry_run:
        return dict(base, action="would-install", reason="dry run")
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = marker + "\n# " + record["name"] + " (managed by AI Extension Manager)\n\n"
    body = read_text(source_file)
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(header + body + "\n\n<!-- /ai-extension-manager:" + record["slug"] + " -->\n")
    _record_rules_target(home, record, agent, destination, expected, "shared-file")
    return dict(base, action="install", state="in-sync", note="created new instruction file")


def _record_rules_target(home, record, agent, destination: Path, expected_sha: str, kind: str) -> None:
    record.setdefault("targets", {})[agent["id"]] = {
        "agent": agent["id"], "scope": "user", "path": str(destination), "mode": "rules",
        "source_hash": record["hash"], "target_hash": expected_sha, "kind": kind,
        "version": record.get("version"), "synced_at": utcnow(), "last_action": "install",
    }
    home.upsert_resource(record)


def verify_target(home: Home, record: dict, agent: dict, workspace=None, scope="user") -> dict:
    target = target_for(record, agent, workspace, scope)
    if not target.get("ok"):
        return {"resource": record["id"], "agent": agent["id"], "status": "unavailable",
                "reason": target.get("reason")}
    kind = record["type"]
    base = {"resource": record["id"], "agent": agent["id"], "path": str(target["path"])}
    if kind == "skill":
        destination = target["path"]
        if not destination.exists():
            return dict(base, status="missing", detail="target directory does not exist")
        if is_link(destination):
            expected = (home.resource_dir(record["type"], record["slug"]) / "payload").resolve()
            try:
                actual_link = Path(destination).resolve()
            except OSError:
                return dict(base, status="corrupted", detail="link cannot be resolved")
            if actual_link != expected:
                return dict(base, status="corrupted", detail="link points to " + str(actual_link))
        actual = tree_hash(destination)
        if actual == record["hash"]:
            return dict(base, status="ok", detail="hash matches library", hash=actual)
        missing, extra, changed = diff_manifests(record.get("manifest") or {}, tree_manifest(destination))
        return dict(base, status="drifted", detail="target differs from library", hash=actual,
                    missing=missing, extra=extra, changed=changed)
    if kind == "mcp":
        config_path = target["path"]
        data = read_json(config_path, {}) if config_path.exists() else {}
        node = data
        for key in target.get("pointer") or ["mcpServers"]:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        entry = node.get(target["server"]) if isinstance(node, dict) else None
        expected = mcp_server_config(record)
        if not config_path.exists():
            return dict(base, status="missing", detail="config file does not exist")
        if entry is None:
            return dict(base, status="missing", detail="server entry is absent")
        if entry == expected:
            return dict(base, status="ok", detail="server entry matches library")
        return dict(base, status="drifted", detail="server entry differs", actual=entry, expected=expected)
    if kind == "rules":
        destination = target["path"]
        expected_sha = (record.get("content") or {}).get("sha256") or ""
        if target.get("is_dir"):
            suffix = ".mdc" if "cursor-mdc" in str((agent.get("rules") or {}).get("format")) else ".md"
            destination = destination / (record["slug"] + suffix)
        if not destination.exists():
            return dict(base, status="missing", detail="rule file does not exist")
        text = read_text(destination)
        if expected_sha and "hash:" + expected_sha[:12] in text:
            return dict(base, status="ok", detail="managed block hash matches")
        if target.get("is_dir") and expected_sha and sha256_file(destination) == expected_sha:
            return dict(base, status="ok", detail="rule file hash matches")
        if "<!-- ai-extension-manager:" + record["slug"] in text:
            return dict(base, status="drifted", detail="managed block exists but content changed")
        return dict(base, status="manual", detail="rule file is not managed by AI Extension Manager")
    return dict(base, status="unsupported", detail="no verifier for " + kind)


def diff_manifests(expected: dict, actual: dict):
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(rel for rel in set(expected) & set(actual)
                     if expected[rel].get("sha256") != actual[rel].get("sha256"))
    return missing, extra, changed


# ---------------------------------------------------------------------------
# installed plugin inventory (read-only, per tool)
# ---------------------------------------------------------------------------

def _toml_load(path: Path):
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        return None
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except (OSError, ValueError):
        return None


def plugin_inventory(agent: dict) -> list:
    """Return installed plugins for one agent: [{name, version, path, enabled, source}]."""
    agent_id = agent["id"]
    found = []
    if agent_id == "claude":
        data = read_json(resolve_agent_path(agent, "~/.claude/plugins/installed_plugins.json") or Path(), None)
        plugins = (data or {}).get("plugins") if isinstance(data, dict) else None
        if isinstance(plugins, dict):
            for plugin_id, installs in plugins.items():
                for install in installs if isinstance(installs, list) else []:
                    if not isinstance(install, dict):
                        continue
                    found.append({
                        "name": plugin_id.split("@")[0], "id": plugin_id,
                        "marketplace": plugin_id.split("@")[1] if "@" in plugin_id else None,
                        "version": install.get("version"), "path": install.get("installPath"),
                        "enabled": install.get("enabled", True), "source": "installed_plugins.json",
                    })
        return found
    if agent_id == "codex":
        config_path = resolve_agent_path(agent, "~/.codex/config.toml")
        data = _toml_load(config_path) if config_path else None
        cache_root = resolve_agent_path(agent, "~/.codex/plugins/cache")
        cache_versions = {}
        if cache_root and cache_root.is_dir():
            for marketplace in cache_root.iterdir():
                if not marketplace.is_dir():
                    continue
                for plugin in marketplace.iterdir():
                    if not plugin.is_dir():
                        continue
                    versions = sorted(child.name for child in plugin.iterdir() if child.is_dir())
                    cache_versions[(marketplace.name, plugin.name)] = versions
        plugins = (data or {}).get("plugins") if isinstance(data, dict) else None
        if isinstance(plugins, dict):
            for plugin_id, settings in plugins.items():
                name = plugin_id.split("@")[0]
                marketplace = plugin_id.split("@")[1] if "@" in plugin_id else None
                versions = cache_versions.get((marketplace, name), [])
                found.append({
                    "name": name, "id": plugin_id, "marketplace": marketplace,
                    "version": versions[-1] if versions else None,
                    "versions": versions, "path": str(cache_root / str(marketplace) / name) if cache_root else None,
                    "enabled": bool((settings or {}).get("enabled", True)) if isinstance(settings, dict) else True,
                    "source": "config.toml",
                })
        return found
    if agent_id == "dsh":
        profile = (agent.get("plugin") or {}).get("profile") or "desktop"
        profile_json = agent_home(agent) / "profiles" / profile / "package.json"
        data = read_json(profile_json, None)
        if isinstance(data, dict):
            for package in (data.get("dsh", {}).get("profile", {}) or {}).get("bundles", []):
                package_json = agent_home(agent) / "profiles" / profile / "node_modules" / package / "package.json"
                meta = read_json(package_json, None) or {}
                found.append({
                    "name": package, "id": package, "marketplace": None,
                    "version": meta.get("version"), "path": str(package_json.parent),
                    "enabled": True, "source": "profile bundles",
                })
        return found
    if agent_id == "gemini":
        extensions = resolve_agent_path(agent, "~/.gemini/extensions")
        if extensions and extensions.is_dir():
            for child in extensions.iterdir():
                manifest = read_json(child / "gemini-extension.json", None)
                if isinstance(manifest, dict):
                    found.append({
                        "name": manifest.get("name") or child.name, "id": child.name,
                        "marketplace": None, "version": manifest.get("version"),
                        "path": str(child), "enabled": True, "source": "gemini-extension.json",
                    })
        return found
    if agent_id == "copilot":
        extensions = resolve_agent_path(agent, "~/.vscode/extensions")
        if extensions and extensions.is_dir():
            for child in sorted(extensions.iterdir()):
                if len(found) >= 50 or not child.is_dir():
                    continue
                package = read_json(child / "package.json", None)
                if not isinstance(package, dict):
                    continue
                contributes = package.get("contributes")
                if isinstance(contributes, dict) and ("chatSkills" in contributes or "chatPlugins" in contributes):
                    found.append({
                        "name": str(package.get("name") or child.name), "id": child.name,
                        "marketplace": "vscode", "version": package.get("version"),
                        "path": str(child), "enabled": True, "source": "package.json contributes",
                    })
        return found
    return found


def plugin_version_drift(inventory: list, record: dict) -> dict:
    """Compare a library plugin record with installed copies by name."""
    name = str(record.get("name") or "")
    bare = name.split("/")[-1].lower()
    matches = [item for item in inventory
               if str(item.get("name", "")).split("/")[-1].lower() == bare]
    versions = sorted({str(item.get("version")) for item in matches if item.get("version")})
    return {
        "installed": matches,
        "installed_versions": versions,
        "library_version": record.get("version"),
        "drift": bool(versions) and record.get("version") not in versions,
        "installed_elsewhere": len(matches) > 0,
    }
