#!/usr/bin/env python3
"""Render docs/og.png: a 1200x630 social card for posts and link previews.

    python docs/make_og.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent / "og.png"

HTML = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; }
  body { margin: 0; width: 1200px; height: 630px; overflow: hidden;
         background: radial-gradient(900px 520px at 12% -20%, #16304f 0%, #080b12 58%, #05070b 100%);
         font-family: 'Segoe UI', system-ui, sans-serif; color: #e8eefb; }
  .glow { position: absolute; width: 620px; height: 420px; border-radius: 50%;
          background: radial-gradient(closest-side, rgba(64,140,255,.28), transparent);
          top: -60px; right: -140px; }
  .wrap { position: absolute; inset: 54px 60px 48px 60px; display: flex; flex-direction: column; }
  .brand { display: flex; align-items: baseline; gap: 14px; }
  .mark { font-family: Consolas, monospace; font-size: 30px; font-weight: 700; color: #7fd1ff; letter-spacing: -1px; }
  .name { font-size: 21px; font-weight: 600; color: #c8d6ec; }
  .tag { margin-left: auto; font-size: 15px; color: #7e93b1; }
  h1 { margin: 34px 0 0; font-size: 62px; line-height: 1.08; letter-spacing: -1.6px; font-weight: 800; }
  h1 .dim { color: #8fa9c9; }
  h1 .accent { color: #6ee7a8; }
  .sub { margin-top: 18px; font-size: 21px; color: #a9bbd4; }
  .term { margin-top: auto; border-radius: 14px; border: 1px solid rgba(140,175,225,.25);
          background: #0b0f17; overflow: hidden; box-shadow: 0 26px 60px rgba(0,0,0,.55); }
  .bar { height: 34px; display: flex; align-items: center; gap: 8px; padding: 0 14px;
         background: linear-gradient(#161c27, #11161f); border-bottom: 1px solid #1d2532; }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .title { margin-left: 8px; font-family: Consolas, monospace; font-size: 12px; color: #7b8da6; }
  .code { padding: 16px 20px 18px; font-family: Consolas, 'Cascadia Mono', monospace;
          font-size: 15px; line-height: 1.4; white-space: pre; color: #b9c8de; }
  .prompt { color: #6ee7a8; font-weight: 700; }
  .conflict { color: #ffb86b; font-weight: 700; }
  .ok { color: #6ee7a8; }
  .foot { margin-top: 14px; display: flex; font-size: 14px; color: #71849e; font-family: Consolas, monospace; }
  .foot .right { margin-left: auto; }
</style></head><body>
<div class="glow"></div>
<div class="wrap">
  <div class="brand">
    <span class="mark">aem</span><span class="name">AI Extension Manager</span>
    <span class="tag">local-first · zero dependencies · MIT</span>
  </div>
  <h1>Six AI tools.<br>One skill library.<br><span class="accent">No silent overwrites.</span></h1>
  <div class="sub">SHA-256 state tracking for Claude Code, Codex, Gemini CLI, Cursor, Copilot and DSH.</div>
  <div class="term">
    <div class="bar">
      <span class="dot" style="background:#ff5f57"></span>
      <span class="dot" style="background:#febc2e"></span>
      <span class="dot" style="background:#28c840"></span>
      <span class="title">both sides changed -&gt; nothing written</span>
    </div>
    <div class="code"><span class="prompt">$ </span>aem sync --direction distribute --agent claude --resource my-skill
  claude   skill/my-skill    <span class="conflict">conflict [C]  both sides changed</span>
  <span class="ok">conflicts were left untouched; resolve them explicitly</span></div>
  </div>
  <div class="foot"><span>github.com/Jack91124/ai-extension-manager</span><span class="right">npx skills add Jack91124/ai-extension-manager</span></div>
</div>
</body></html>"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    page_file = OUT.parent / "_og.html"
    page_file.write_text(HTML, encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
        page.goto(page_file.as_uri())
        page.wait_for_timeout(250)
        page.screenshot(path=str(OUT))
        browser.close()
    page_file.unlink(missing_ok=True)
    print("wrote " + str(OUT) + " (" + str(OUT.stat().st_size) + " bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
