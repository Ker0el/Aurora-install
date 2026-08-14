<div align="center">

# ⚡ Aurora Install · 极光入库

A modern Fluent Design style Steam game library tool

Clean · Efficient · Multi-manifest-source

[中文版](./README.md) | **English**

![Python](https://img.shields.io/badge/Python-3.8%2B-4B8BBE) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Windows-11%20%2F%2010-0078D6)

</div>

---

## ✨ Features

- **Fluent Design UI** — Windows 11 style modern interface with dark / light themes and custom accent colors
- **Multi-language** — 简体中文, English, Français, Русский, Deutsch, 日本語, 繁體中文
- **One-click OpenSteamTool setup** — The "Initialize" button on the Home page downloads and installs the OpenSteamTool core from GitHub and generates its config, ready to use out of the box
- **Multiple manifest sources** — SWA V2, Cysaw, Walftech, Sudama, MHub, GitHub repositories and more, with automatic fallback
- **Duplicate protection** — Automatically skips games already in your library (including DLCs)
- **Batch install** — Select multiple games and queue them for installation with live progress
- **One-click removal** — Delete a game from the Home page; unlock files, manifests and backups are cleaned up automatically (SteamTools / OpenSteamTools / GreenLuma)
- **Online co-op mode** — Built-in launch service for online games
- **Trainer downloader** — Search and download trainers, with automatic ZIP / RAR / 7z extraction
- **Backup & restore** — One-click backup / restore of your library data and manifest files
- **Faster downloads** — Auto-detects your network and switches to China GitHub mirrors when needed
- **One-click setup** — Automated installer script with dependency conflict cleanup

## 📥 Installation

### Option 1: Direct download (Recommended)

Grab `AuroraInstall.exe` from the [Releases](https://github.com/Ker0el/Aurora-install/releases) page and run it. No environment setup needed.

### Option 2: One-click script

```bat
install.bat
```

Automatically checks your Python environment, installs dependencies, and launches the app.

### Option 3: Run manually

```bash
pip install -r requirements.txt
python main.py
```

> For users in mainland China, append `-i https://pypi.tuna.tsinghua.edu.cn/simple` to pip for faster downloads.

## 📖 Usage

1. Open the Steam client and sign in
2. Launch Aurora Install — it auto-detects your Steam path and unlocker (SteamTools / OpenSteamTools / GreenLuma)
3. If OpenSteamTool is not detected, click **Initialize** on the Home page to download and install the OpenSteamTool core automatically (close Steam first)
4. Search for a game on the **Search** page → click install (or select multiple games for batch install)
5. Back in Steam, the game appears in your library — download and play
6. To remove a game: Home page card → "More" → "Delete" — unlock files, manifests and backups are cleaned up automatically

See in-app hints and the Settings panel for more details.

## ⚠️ Disclaimer

This tool is provided for learning and research purposes only. Do not use it for commercial or illegal purposes. Users assume all risks and consequences arising from the use of this tool. Please support official releases.

## 🤝 Community

- GitHub Issues: report bugs and suggestions

## 📄 License

[MIT](LICENSE)
