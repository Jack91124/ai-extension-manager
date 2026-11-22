#!/usr/bin/env python3
"""Run the AI Extension Manager end to end in a throwaway sandbox.

Everything happens under a temporary directory: a fake central library and six
fake AI tool home directories, so your real ~/.claude, ~/.codex, ... are never
touched.

    python demo/run_demo.py            # clean up afterwards
    python demo/run_demo.py --keep     # print and keep the sandbox path

The output is a real transcript; the README shows the result of this script.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ inside the project
ROOT = Path(__file__).resolve().parents[1]
AEM = ROOT / "scripts" / "aem.py"
AGENTS = ("dsh", "codex", "claude", "gemini", "cursor", "copilot")


def make_skill(base: Path) -> Path:
    skill = base / "demo-skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: demo-skill\n"
        "description: A tiny demo skill used by demo/run_demo.py to show import, distribute, verify and conflict handling.\n"
        "---\n\n"
        "# Demo skill\n\n"
        "When asked, greet the user and report the current sync state.\n",
        encoding="utf-8")
    (skill / "scripts" / "greet.py").write_text(
        "print('hello from demo-skill')\n", encoding="utf-8")
    return skill


def make_sandbox() -> tuple:
    base = Path(tempfile.mkdtemp(prefix="aem-demo-"))
    home = base / "home"
    workspace = base / "workspace"
    workspace.mkdir()
    userhome = base / "userhome"
    (userhome / ".agents" / "skills").mkdir(parents=True)
    for agent in AGENTS:
        (base / "agents" / agent).mkdir(parents=True)
    env = dict(os.environ)
    env.update({
        "AEM_HOME": str(home),
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        # keep "~" inside the sandbox so no real tool directory is ever scanned
        "HOME": str(userhome),
        "USERPROFILE": str(userhome),
    })
    for agent in AGENTS:
        env["AEM_AGENT_HOME_" + agent.upper()] = str(base / "agents" / agent)
    return base, env


def run(env: dict, *args: str, expect: int = 0) -> str:
    command = [sys.executable, str(AEM)] + list(args)
    shown = "aem " + " ".join(args)
    print("\n$ " + shown)
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", env=env, cwd=str(ROOT))
    output = (result.stdout or "").rstrip()
    if output:
        print(output)
    if result.returncode != expect:
        print("--- stderr ---")
        print((result.stderr or "").rstrip())
        raise SystemExit("expected exit " + str(expect) + ", got " + str(result.returncode) +
                         " for: " + shown)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the end-to-end demo in a temp sandbox")
    parser.add_argument("--keep", action="store_true", help="keep the sandbox for inspection")
    args = parser.parse_args()
    base, env = make_sandbox()
    source = make_skill(base / "source")
    try:
        print("AI Extension Manager demo")
        print("sandbox: " + str(base))
        print("fake agents: " + ", ".join(AGENTS))
        run(env, "init")
        run(env, "doctor")
        run(env, "scan")
        run(env, "import", "--source", str(source))
        run(env, "sync", "--direction", "distribute", "--agent", "claude",
            "--agent", "codex", "--agent", "cursor", "--resource", "demo-skill")
        run(env, "verify", "--all")
        run(env, "status")
        # 1) someone edits the Claude copy by hand
        claude_copy = base / "agents" / "claude" / "skills" / "demo-skill" / "SKILL.md"
        with open(claude_copy, "a", encoding="utf-8") as handle:
            handle.write("\nLocal Claude-only note.\n")
        print("\n(edited " + str(claude_copy) + ")")
        run(env, "status")
        # 2) the upstream source also changes and is imported: now both sides differ
        library_copy = source / "SKILL.md"
        with open(library_copy, "a", encoding="utf-8") as handle:
            handle.write("\nUpstream library note.\n")
        run(env, "import", "--source", str(source), "--on-conflict", "keep-source")
        run(env, "sync", "--direction", "distribute", "--agent", "claude",
            "--resource", "demo-skill", expect=2)
        run(env, "status")
        print("\nDemo complete: import, distribute to three tools, verify, drift detection,")
        print("and a two-sided change that is reported as a conflict instead of overwritten.")
        return 0
    finally:
        if args.keep:
            print("\nkept sandbox: " + str(base))
        else:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
