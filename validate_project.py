#!/usr/bin/env python3
"""Static checks for the browser game. Does not replace a real browser gameplay test."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
ERRORS: list[str] = []
WARNINGS: list[str] = []
PASS_COUNT = 0


def check(condition: bool, message: str) -> None:
    global PASS_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"PASS  {message}")
    else:
        ERRORS.append(message)
        print(f"FAIL  {message}")


def read_text(name: str) -> str:
    path = ROOT / name
    if not path.is_file():
        ERRORS.append(f"Missing required file: {name}")
        print(f"FAIL  Missing required file: {name}")
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


html = read_text("homepage.html")
loader = read_text("loader.js")
io_worker = read_text("io_worker.js")
gpu_worker = read_text("wgpu_worker.js")
game_js = read_text("game.js")
read_text("serve_local.py")

# Parse HTML enough to catch duplicate IDs, which break the access and diagnostics UI.
class IdAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.duplicates: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key == "id" and value:
                if value in self.ids:
                    self.duplicates.add(value)
                self.ids.add(value)


audit = IdAudit()
try:
    audit.feed(html)
    audit.close()
    check(not audit.duplicates, "HTML contains no duplicate IDs" if not audit.duplicates else
          "HTML contains duplicate IDs: " + ", ".join(sorted(audit.duplicates)))
except Exception as exc:
    check(False, f"HTML parse failed: {exc}")

required_ids = {
    "canvas", "loading", "label", "pct", "fill", "fps", "hud",
    "access-lock", "access-form", "access-code", "access-error", "graphics-plus", "smart-advisor", "ai-advisor", "ai-advisor-message", "ai-advisor-safe", "ai-advisor-dismiss",
    "game-doctor", "doctor-title", "doctor-advice", "doctor-detail",
    "doctor-reload", "doctor-safe", "doctor-copy", "doctor-close",
}
missing_ids = sorted(required_ids - audit.ids)
check(not missing_ids, "required game/access/diagnostics elements exist" if not missing_ids else
      "missing IDs: " + ", ".join(missing_ids))

# Make sure the access gate waits before engine-worker creation.
module_scripts = re.findall(
    r"<script\b(?=[^>]*\btype\s*=\s*['\"]module['\"])[^>]*>(.*?)</script\s*>",
    html, re.IGNORECASE | re.DOTALL,
)
check(len(module_scripts) == 1, "exactly one inline JavaScript module exists")
module = module_scripts[0] if len(module_scripts) == 1 else ""
if module:
    code_at = module.find('const ACCESS_CODE = "Abdullah_Chico"')
    wait_at = module.find("await new Promise")
    worker_at = module.find("new Worker(BASE + '/loader.js')")
    check(code_at >= 0 and wait_at > code_at and worker_at > wait_at,
          "access-code wait occurs before the game worker starts")
    check('id="access-code"' in html and 'id="access-error"' in html,
          "access-code input and error status exist")
    check("showGameIssue(" in module and "unhandledrejection" in module,
          "runtime error diagnostics are connected")
    check("quiet > 60" in module and "stallReported" in module,
          "stalled-load diagnostics are connected")
    check('id="doctor-safe"' in html and "safeUrl.searchParams.set('low', '1')" in module
          and "safeUrl.searchParams.delete('clarity')" in module,
          "safe-mode recovery switches to a lower-load profile")

check('id="graphics-plus"' in html and "GRAPHICS PLUS" in html,
      "graphics enhancement toggle is visible in the access screen")
check("clarity: q.get('clarity') === '1'" in html
      and "gq.set('clarity', '1')" in loader
      and "const clarityEnabled" in gpu_worker
      and "let sharpened = clamp" in gpu_worker,
      "optional clarity setting is connected from page to GPU shader")
check('id="smart-advisor"' in html and "SMART PERFORMANCE ADVISOR" in html,
      "smart performance advisor toggle exists")
check("function chooseSmartGraphicsProfile()" in module
      and "function observeSmartFps(fps)" in module
      and "observeSmartFps(ev.data.fps)" in module
      and "function restartInSafeMode()" in module,
      "smart advisor tunes settings and detects sustained low FPS")

# Full JS parser checks run in CI where Node.js is installed.
node = shutil.which("node")
if not node:
    WARNINGS.append("Node.js was not found; JavaScript syntax checks were skipped.")
    print("WARN  Node.js not found; JavaScript syntax checks were skipped.")
else:
    js_files = {
        "loader.js": loader,
        "io_worker.js": io_worker,
        "wgpu_worker.js": gpu_worker,
        "game.js": game_js,
    }
    with tempfile.TemporaryDirectory(prefix="game-check-") as temp_dir:
        temp_root = Path(temp_dir)
        for name, source in js_files.items():
            temp_path = temp_root / name
            temp_path.write_text(source, encoding="utf-8")
            proc = subprocess.run([node, "--check", str(temp_path)],
                                  capture_output=True, text=True, check=False)
            check(proc.returncode == 0, f"{name} JavaScript syntax"
                  if proc.returncode == 0 else
                  f"{name} JavaScript syntax: {(proc.stderr or proc.stdout).strip()[:400]}")

    with tempfile.TemporaryDirectory(prefix="game-module-") as temp_dir:
        module_path = Path(temp_dir) / "homepage.mjs"
        module_path.write_text(module, encoding="utf-8")
        proc = subprocess.run([node, "--check", str(module_path)],
                              capture_output=True, text=True, check=False)
        check(proc.returncode == 0, "homepage inline module syntax"
              if proc.returncode == 0 else
              "homepage inline module syntax: " + (proc.stderr or proc.stdout).strip()[:400])

# The game-data mirror is purposely not checked into Git.
expected_data = ROOT / "mirror" / "playgta5.com"
if not expected_data.is_dir():
    WARNINGS.append("Game-data mirror is absent from this checkout; complete gameplay cannot be tested here.")
    print("WARN  mirror/playgta5.com is absent (expected to be supplied locally).")

print(f"\nStatic checks passed: {PASS_COUNT}; failures: {len(ERRORS)}; warnings: {len(WARNINGS)}")
if ERRORS:
    print("\nFailures:")
    for error in ERRORS:
        print(f"- {error}")
    sys.exit(1)
print("Static checks completed. A browser run is still required to certify gameplay.")
