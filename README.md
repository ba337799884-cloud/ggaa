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

The project can show a client-side access prompt before the game starts. A code embedded in browser JavaScript is only a casual gate; anyone can inspect the source. Use server-side authentication for real private access.

## Notes

This repository contains runtime/client code and a local launcher. It does not include proprietary game data or provide a ready-to-play public game server. Keep existing license notices intact and only use assets and game data you are authorized to use.
