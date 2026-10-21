# Abdullah's GTA-Style Browser Game

A browser-based 3D driving game project with graphics and performance options.

## Run locally

1. Clone or download this repository.
2. Supply the required game data locally only if you have the legal right to use it. That data is not included here.
3. On Windows, run `Launch-Local.cmd`.
4. Open the local address shown by the launcher.

The local server is important because this runtime uses WebAssembly, worker threads, and cross-origin isolation. A simple static host may not provide the required headers.

## Graphics and performance options

The page supports URL options such as:

- `low=0` — disable the low-memory profile.
- `fps=60` — request a 60 FPS target where supported.
- `res=1920x1080` — request a 1920×1080 render size.
- `shadows=1` — use the project's current shadow setting.
- `clarity=1` — enable the optional GPU sharpening pass (adds work per pixel).

Example: `?low=0&fps=60&res=1920x1080&shadows=1&clarity=1`

Real performance depends on your device, browser, GPU, and available game data. A sharpening pass can improve perceived clarity, but it is not AI upscaling. True AI upscaling, AI texture enhancement, and AI-generated reflections need compatible models and deeper renderer integration.

## Access code

The game now shows a client-side access prompt before the engine starts. Enter the configured code `Abdullah_Chico` to continue. This is a casual gate only: the code is stored in browser JavaScript and can be inspected, so it is not secure private authentication.

## Diagnostics and recovery

The browser page includes a local Smart Performance Advisor for automatic settings and live FPS warnings, plus a server-backed Game Performance Coach using Cloudflare Workers AI through `functions/api/game-ai.js`. The actual AI requires a Workers AI binding named `AI` on the Cloudflare Pages project; without that binding, the API intentionally returns a helpful setup error. Follow [Cloudflare's Pages binding guide](https://developers.cloudflare.com/pages/functions/bindings/) and add Workers AI with binding name `AI`, then redeploy. Workers AI usage may incur charges. The game still uses conventional WebGPU sharpening and color tuning; it does not automatically gain DLSS, RTX ray tracing, or a Forza Horizon rendering engine. The Game Doctor detects JavaScript errors, failed engine tasks, GPU device loss, and startup stalls, and offers diagnostics, reload, and safe-mode recovery.

## AI service endpoint

The game coach sends only a bounded summary of device capabilities, the current profile, FPS, and a short visible issue summary to `/api/game-ai`. It does not upload full source files or browser logs. The function limits request size and applies a soft per-isolate rate limit; production hosting should also enable platform-level rate limiting and verify AI usage limits. Keep the code gate in mind: the browser access prompt is not server-side authentication, so it should not be treated as a secure authorization boundary.

## Notes

This repository contains runtime/client code and a local launcher. It does not include proprietary game data or provide a ready-to-play public game server. Keep existing license notices intact and only use assets and game data you are authorized to use.


## Visual reference target

The linked walkthrough description highlights open-world exploration on foot and in vehicles, with a 4K/60 FPS target in the video metadata. See [reference walkthrough](https://mastersingaming.com/2026/06/12/gta-5-gameplay-walkthrough-full-game-4k-60fps-no-commentary/). This is a visual target, not a performance guarantee; no scene-by-scene video comparison was completed. Use the advisor to pick a device-appropriate profile.
