#!/usr/bin/env python3
"""Render docs/hero.png from a real demo transcript (Playwright + Chromium).

    python docs/make_hero.py

The image is a terminal-style capture of the commands demo/run_demo.py runs; the
excerpt below mirrors the real transcript, with machine-specific paths shortened.
"""
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "hero.png"

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
  body { margin: 0; width: 1600px; height: 1000px; overflow: hidden;
         background: radial-gradient(1200px 700px at 20% -10%, #123 0%, #070a10 55%, #04060a 100%);
         font-family: 'Segoe UI', system-ui, sans-serif; }
  .glow { position: absolute; width: 700px; height: 480px; border-radius: 50%;
          background: radial-gradient(closest-side, rgba(64,140,255,.20), transparent);
          top: 40px; right: -120px; }
  .wrap { position: absolute; inset: 56px 64px 64px 64px; display: flex; flex-direction: column; }
  .brand { display: flex; align-items: baseline; gap: 18px; color: #dfe7f5; }
  .brand .mark { font-family: Consolas, monospace; font-size: 34px; font-weight: 700;
                 color: #7fd1ff; letter-spacing: -1px; }
  .brand .name { font-size: 25px; font-weight: 600; letter-spacing: .2px; }
  .brand .tag { margin-left: auto; font-size: 17px; color: #8fa3bf; }
  .window { margin-top: 26px; flex: 1; border-radius: 16px; overflow: hidden;
            border: 1px solid rgba(140,175,225,.22); background: #0b0f17;
            box-shadow: 0 40px 90px rgba(0,0,0,.55), 0 2px 0 rgba(255,255,255,.04) inset; }
  .bar { height: 46px; display: flex; align-items: center; gap: 9px; padding: 0 18px;
         background: linear-gradient(#161c27, #11161f); border-bottom: 1px solid #1d2532; }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .title { margin-left: 12px; font-family: Consolas, monospace; font-size: 15px; color: #8194ad; }
  .term { padding: 26px 30px 22px; font-family: Consolas, 'Cascadia Mono', monospace;
          font-size: 18px; line-height: 1.42; white-space: pre; color: #c7d3e6; }
  .prompt { color: #6ee7a8; font-weight: 700; }
  .cmd { color: #eaf2ff; font-weight: 600; }
  .out { color: #93a5bf; }
  .ok { color: #6ee7a8; }
  .conflict { color: #ffb86b; font-weight: 700; }
  .badge { margin-top: 22px; display: flex; align-items: center; gap: 16px;
           font-family: Consolas, monospace; font-size: 18px; color: #9fb2ca; }
  .pill { padding: 7px 14px; border-radius: 999px; background: rgba(255,184,107,.12);
          border: 1px solid rgba(255,184,107,.45); color: #ffc98d; }
  .foot { margin-left: auto; color: #6f8199; font-family: 'Segoe UI', sans-serif; font-size: 16px; }
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
      <span class="title">Windows PowerShell — demo/run_demo.py (real transcript, paths shortened)</span>
    </div>
    <div class="term">__BODY__</div>
  </div>
  <div class="badge">
    <span class="pill">exit code 2 → nothing overwritten</span>
    <span>SHA-256 state tracking · per-target backups · local-first</span>
    <span class="foot">github.com/Jack91124/ai-extension-manager</span>
  </div>
</div>
</body></html>"""


def colorize(line: str) -> str:
    escaped = (line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    if escaped.startswith("$ "):
        return '<span class="prompt">$ </span><span class="cmd">' + escaped[2:] + "</span>"
    if "conflict [C]" in escaped:
        return '<span class="conflict">' + escaped + "</span>"
    if " ok " in escaped or "in-sync" in escaped or "imported:" in escaped:
        return '<span class="ok">' + escaped + "</span>"
    return '<span class="out">' + escaped + "</span>"


def main() -> int:
    body = "\n".join(colorize(line) for line in TRANSCRIPT.splitlines())
    html = HTML.replace("__BODY__", body)
    page_file = OUT.parent / "_hero.html"
    page_file.write_text(html, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page.goto(page_file.as_uri())
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT))
        browser.close()
    page_file.unlink(missing_ok=True)
    print("wrote " + str(OUT) + " (" + str(OUT.stat().st_size) + " bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
