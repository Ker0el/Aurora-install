<div align="center">

# ⚡ Aurora Install · 极光入库

现代 Fluent Design 风格的 Steam 游戏入库工具

简洁 · 高效 · 多清单源

![Python](https://img.shields.io/badge/Python-3.8%2B-4B8BBE) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Windows-11%20%2F%2010-0078D6)

</div>

---

## ✨ 特性

- **Fluent Design 界面** — Windows 11 风格现代化 UI，支持深色 / 浅色主题与自定义主题色
- **多语言** — 中文、English、Français、Русский、Deutsch、日本語、繁體中文
- **多清单源** — 内置 SWA V2、Cysaw、Walftech、Sudama、MHub、GitHub 仓库等多种清单源，自动调度
- **入库去重** — 重复入库自动拦截，智能识别已拥有游戏（含 DLC）
- **批量入库** — 多选游戏一键排队入库，实时进度反馈
- **联机模式** — 内置联机核心服务，支持游戏联机启动
- **修改器下载** — 内置修改器搜索与下载，支持 ZIP / RAR / 7z 自动解压
- **本地备份与恢复** — 一键备份 / 还原入库数据与清单文件
- **加速下载** — 自动检测网络环境，国内自动切换 GitHub 镜像
- **一键安装** — 提供自动化安装脚本，依赖冲突自动清理

## 📥 安装

### 方式一：直接下载（推荐）

从 [Releases](https://github.com/Ker0el/Aurora-install/releases) 下载 `AuroraInstall.exe`，双击运行，无需安装任何环境。

### 方式二：一键脚本

```bat
install.bat
```

自动完成 Python 环境检查、依赖安装与程序启动。

### 方式三：手动运行

```bash
pip install -r requirements.txt
python main.py
```

> 国内网络可在 pip 后追加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` 加速。

## 📖 使用

1. 打开 Steam 客户端并登录
2. 启动 Aurora Install，自动检测 Steam 路径与解锁器（SteamTools / GreenLuma）
3. 在「搜索」页搜索游戏 → 点击入库（或勾选多个游戏批量入库）
4. 回 Steam 即可看到游戏出现在库中，开始下载游玩

更多细节见各页面内提示与设置面板。

## ⚠️ 免责声明

本工具仅供学习和研究使用，请勿用于商业用途或非法用途。使用者需自行承担使用本工具可能带来的风险与后果。请支持正版游戏。

## 🤝 社区

- GitHub Issues：报告问题与建议

## 📄 许可证

[MIT](LICENSE)
