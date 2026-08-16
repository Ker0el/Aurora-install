<div align="center">

# ⚡ Aurora Install · 极光入库

Steam game library tool — **Find any game, unlock with one click, play right away**

Modern Fluent Design · Multiple unlockers · Whole-internet resource search

![Python](https://img.shields.io/badge/Python-3.8%2B-4B8BBE) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Windows-11%20%2F%2010-0078D6) ![Version](https://img.shields.io/badge/Release-v1.8-blue)

[中文版](./README.md) | **English**

</div>

---

## ✨ Features

| | |
|---|---|
| 🔍 **Whole-internet search** | Aggregates multiple game download sites (Baidu / Quark / Xunlei cloud links). Steam has nothing? Download sites have your back — **find any game** |
| 🎮 **Multiple manifest sources** | SWA V2, Cysaw, Walftech, Sudama, MHub, GitHub repositories and more, with automatic fallback |
| 🔓 **Multiple unlockers** | Auto-detects SteamTools / OpenSteamTools / GreenLuma; one-click initialization, ready out of the box |
| 🧰 **Built-in tools** | Trainer search & download (auto-extract), Steam-less launch (Goldberg), online co-op launch mode |
| ⚡ **Batch install** | Queue multiple games with one click and live progress; duplicate protection (incl. DLCs) |
| 🗑️ **One-click removal** | Cleanly removes unlock files, manifests and backups |
| 💾 **Backup & restore** | One-click backup / restore of library data and manifest files |
| 🎨 **Fluent Design** | Windows 11 style UI, dark / light themes + custom accent colors, 8 languages |

## 🚀 Quick Start

> **Three steps to play:**

1. **Initialize** — On first launch, click the **Initialize** button on the Home page (close Steam first) to install the unlocker core, then restart the app
2. **Search & install** — Search a game on the **Search** page → click the card to unlock (multi-select supported). Can't find it? Tick "Search download sites" to get cloud drive links directly
3. **Play** — Open Steam — the game is already in your library. Download and play

> For later installs, only steps 2–3 are needed; right-click a card on the Home page to remove a game.

## 📥 Installation

### Option 1: Direct download (Recommended)

Grab `AuroraInstall.exe` from the [Releases](https://github.com/Ker0el/Aurora-install/releases) page and run it. No environment setup needed.

### Option 2: Run manually

```bash
pip install -r requirements.txt
python main.py
```

> For users in mainland China, append `-i https://pypi.tuna.tsinghua.edu.cn/simple` to pip for faster downloads.

## ⚠️ Disclaimer

This tool is provided for learning and research purposes only. Do not use it for commercial or illegal purposes. Users assume all risks and consequences arising from the use of this tool. Please support official releases.

## 📄 License

[MIT](LICENSE)
