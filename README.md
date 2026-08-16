<div align="center">

# ⚡ Aurora Install · 极光入库

Steam 游戏入库工具 — **什么游戏都能搜到，一键入库即玩**

现代 Fluent Design · 多解锁器 · 全网资源搜索

![Python](https://img.shields.io/badge/Python-3.8%2B-4B8BBE) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Windows-11%20%2F%2010-0078D6) ![Version](https://img.shields.io/badge/Release-v1.8-blue)

**简体中文** | [English](./README_EN.md)

</div>

---

## ✨ 特性

| | |
|---|---|
| 🔍 **全网搜下载** | 对接多个下载站 API（百度网盘 / 夸克 / 迅雷直链），Steam 搜不到？下载站兜底，**什么游戏都能搜到** |
| 🎮 **多清单源入库** | 内置 SWA V2、Cysaw、Walftech、Sudama、MHub、GitHub 仓库等多种清单源，自动调度 |
| 🔓 **多解锁器** | 自动检测 SteamTools / OpenSteamTools / GreenLuma，一键初始化，开箱即用 |
| 🧰 **内置工具** | 修改器搜索下载（自动解压）、免 Steam 启动（Goldberg）、联机启动模式 |
| ⚡ **批量入库** | 多选游戏一键排队入库，实时进度反馈，自动去重（含 DLC） |
| 🗑️ **一键删除** | 自动清理解锁文件、清单文件与备份，干净利落 |
| 💾 **本地备份恢复** | 一键备份 / 还原入库数据与清单文件 |
| 🎨 **Fluent Design** | Windows 11 风格界面，深色 / 浅色主题 + 自定义主题色，8 种语言 |

## 🚀 快速开始

> **三步入库，直接开玩：**

1. **初始化** — 初次打开先点击「主页」的 **初始化** 按钮（需先关闭 Steam），自动安装解锁器内核，完成后重启应用
2. **搜游戏入库** — 「搜索」页搜游戏 → 点卡片入库（可多选批量）。搜不到？勾选「搜下载站」直接给你网盘资源链接
3. **开玩** — 打开 Steam 客户端，游戏已出现在仓库中，直接下载游玩

> 之后每次入库新游戏都只需第 2、3 步；删除游戏在主页卡片右键即可一键清理。

## 📥 安装

### 方式一：直接下载（推荐）

从 [Releases](https://github.com/Ker0el/Aurora-install/releases) 下载 `AuroraInstall.exe`，双击运行，无需安装任何环境。

### 方式二：手动运行

```bash
pip install -r requirements.txt
python main.py
```

> 国内网络可在 pip 后追加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` 加速。

## ⚠️ 免责声明

本工具仅供学习和研究使用，请勿用于商业用途或非法用途。使用者需自行承担使用本工具可能带来的风险与后果。

## 📄 许可证

[MIT](LICENSE)
