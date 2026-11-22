#!/usr/bin/env python3
"""Render docs/demo.gif from the same real transcript as docs/hero.png.

    python docs/make_demo_gif.py

Each frame reveals one more line of the transcript (terminal typing effect),
then ffmpeg assembles the frames into a looping GIF. Requires Playwright with
Chromium, and ffmpeg on PATH (or ~/.dsh/bin/ffmpeg.exe).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent / "demo.gif"
WIDTH, HEIGHT = 1440, 900

TRANSCRIPT = """$ aem import --source ./my-skill
- imported: my-skill
    id: skill/my-skill
    version: 2026.11.22-034001
    safety: risk=low high=0

$ aem sync --direction distribute --agent claude --agent codex --resource my-skill
Sync distribute (2 steps)
  claude   skill/my-skill                   install [in-sync]
  codex    skill/my-skill                   install [in-sync]
summary: {   "install": 2 }

$ aem verify --all
Verify sync (2 checks)
  claude   skill/my-skill                   ok  hash matches library
  codex    skill/my-skill                   ok  hash matches library
summary: {   "ok": 2 }

$ aem sync --direction distribute --agent claude --resource my-skill
Sync distribute (1 step)
  claude   skill/my-skill                   conflict [C]  both sides changed
summary: {   "conflict": 1 }
conflicts were left untouched; use compare_resources.py and resolve them explicitly"""

HTML = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; }
  body { margin: 0; width: __W__px; height: __H__px; overflow: hidden;
         background: radial-gradient(1200px 700px at 20% -10%, #123 0%, #070a10 55%, #04060a 100%);
         font-family: 'Segoe UI', system-ui, sans-serif; }
  .glow { position: absolute; width: 700px; height: 480px; border-radius: 50%;
          background: radial-gradient(closest-side, rgba(64,140,255,.20), transparent);
          top: 40px; right: -120px; }
  .wrap { position: absolute; inset: 40px 48px 40px 48px; display: flex; flex-direction: column; }
  .brand { display: flex; align-items: baseline; gap: 16px; color: #dfe7f5; }
  .brand .mark { font-family: Consolas, monospace; font-size: 30px; font-weight: 700;
                 color: #7fd1ff; letter-spacing: -1px; }
  .brand .name { font-size: 22px; font-weight: 600; }
  .brand .tag { margin-left: auto; font-size: 15px; color: #8fa3bf; }
  .window { margin-top: 20px; flex: 1; border-radius: 14px; overflow: hidden;
            border: 1px solid rgba(140,175,225,.22); background: #0b0f17;
            box-shadow: 0 40px 90px rgba(0,0,0,.55); }
  .bar { height: 40px; display: flex; align-items: center; gap: 8px; padding: 0 16px;
         background: linear-gradient(#161c27, #11161f); border-bottom: 1px solid #1d2532; }
  .dot { width: 11px; height: 11px; border-radius: 50%; }
  .title { margin-left: 10px; font-family: Consolas, monospace; font-size: 13px; color: #8194ad; }
  .term { padding: 22px 26px 18px; font-family: Consolas, 'Cascadia Mono', monospace;
          font-size: 16px; line-height: 1.45; white-space: pre; color: #c7d3e6; }
  .prompt { color: #6ee7a8; font-weight: 700; }
  .cmd { color: #eaf2ff; font-weight: 600; }
  .out { color: #93a5bf; }
  .ok { color: #6ee7a8; }
  .conflict { color: #ffb86b; font-weight: 700; }
  .badge { margin-top: 16px; display: flex; align-items: center; gap: 14px;
           font-family: Consolas, monospace; font-size: 15px; color: #9fb2ca; }
  .pill { padding: 6px 12px; border-radius: 999px; background: rgba(255,184,107,.12);
          border: 1px solid rgba(255,184,107,.45); color: #ffc98d; }
  .foot { margin-left: auto; color: #6f8199; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
  .cursor { color: #7fd1ff; }
</style></head><body>
<div class="glow"></div>
<div class="wrap">
  <div class="brand">
    <span class="mark">aem</span>
    <span class="name">AI Extension Manager</span>
    <span class="tag">one library · six tools · two-way sync</span>
  </div>
  <div class="window">
    <div class="bar">
      <span class="dot" style="background:#ff5f57"></span>
      <span class="dot" style="background:#febc2e"></span>
      <span class="dot" style="background:#28c840"></span>
      <span class="title">aem — demo/run_demo.py (real transcript, paths shortened)</span>
    </div>
    <div class="term">__BODY__</div>
  </div>
  <div class="badge">
    <span class="pill">exit code 2 &rarr; nothing overwritten</span>
    <span>SHA-256 state tracking · per-target backups · local-first</span>
    <span class="foot">github.com/Jack91124/ai-extension-manager</span>
  </div>
</div>
</body></html>"""


def colorize(line: str) -> str:
    escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if escaped.startswith("$ "):
        return '<span class="prompt">$ </span><span class="cmd">' + escaped[2:] + "</span>"
    if "conflict [C]" in escaped:
        return '<span class="conflict">' + escaped + "</span>"
    if " ok " in escaped or "in-sync" in escaped or "imported:" in escaped:
        return '<span class="ok">' + escaped + "</span>"
    return '<span class="out">' + escaped + "</span>"


def find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    fallback = Path.home() / ".dsh" / "bin" / "ffmpeg.exe"
    if fallback.exists():
        return str(fallback)
    raise SystemExit("ffmpeg not found; put it on PATH or in ~/.dsh/bin")


def main() -> int:
    from playwright.sync_api import sync_playwright

    lines = TRANSCRIPT.splitlines()
    frames_dir = Path(tempfile.mkdtemp(prefix="aem-gif-"))
    html_template = HTML.replace("__W__", str(WIDTH)).replace("__H__", str(HEIGHT))
    frame_paths = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        for index in range(1, len(lines) + 1):
            body = "\n".join(colorize(item) for item in lines[:index])
            if index < len(lines):
                body += '\n<span class="cursor">_</span>'
            page.set_content(html_template.replace("__BODY__", body))
            page.wait_for_timeout(40)
            frame = frames_dir / ("frame-%03d.png" % index)
            page.screenshot(path=str(frame))
            frame_paths.append(frame)
        browser.close()

    concat = frames_dir / "frames.txt"
    durations = []
    for index, frame in enumerate(frame_paths):
        if index == 0:
            duration = 1.0
        elif index == len(frame_paths) - 1:
            duration = 3.0
        else:
            duration = 0.45
        durations.append("file '%s'\nduration %s" % (frame.as_posix(), duration))
    durations.append("file '%s'" % frame_paths[-1].as_posix())
    concat.write_text("\n".join(durations) + "\n", encoding="utf-8")

    ffmpeg = find_ffmpeg()
    command = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-vf",
        "fps=12,scale=1000:-1:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=max_colors=128:stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=3",
        "-loop", "0", str(OUT),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    shutil.rmtree(frames_dir, ignore_errors=True)
    print("wrote %s (%s bytes)" % (OUT, OUT.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
