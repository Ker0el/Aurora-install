# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Aurora Install（极光入库）— Python 3.8+ / PyQt6 桌面应用，Steam 游戏入库工具（解锁器：SteamTools / OpenSteamTools / GreenLuma）。UI 用 PyQt6-Fluent-Widgets。

## 常用命令

```bash
# 开发模式运行
python main.py

# 单元测试（全部）
python -m unittest discover -s tests -v

# 打包 exe（PyInstaller onefile，输出 dist/AuroraInstall.exe）
python build_exe.py
```

打包前若 exe 被占用（程序运行中），先 `taskkill /F /IM AuroraInstall.exe` 并删除 `dist/AuroraInstall.exe`。打包后会自动跑 `backend/_insert_drm.py`（D加密），该脚本不存在时跳过（正常）。

## 架构

- **入口** `main.py` → `app/fluent_app.py` 的 `MainWindow`（MSFluentWindow）
- **UI** `app/fluent_app.py`（单文件约 9000 行，所有页面都在这里）：
  - `HomePage`（已入库游戏主页，删除/初始化/版本切换）、`SearchPage`（搜索入库）、`LauncherPage`（联机）、`TrainerPage`（修改器）、`GbePage`（免 Steam 启动）、`SettingsPage`
  - 后台任务统一用 `AsyncWorker(QThread)` + `_replace_worker` 模式；关闭窗口靠 `MainWindow.closeEvent` 统一清理所有页面的 worker（否则 PyInstaller 退出弹 "Failed to remove temporary directory"）
- **后端** `backend/`：
  - `cai_backend.py`（CaiBackend 类，核心）：入库/删除/清单/密钥/Steam 路径
  - `gbe_backend.py`（Goldberg 模拟器）、`trainer_backend.py`（修改器下载）
- **数据文件**：`config/config.json`（配置，含 `Custom_Steam_Path`、`force_unlocker_type`）、`config/installed_games.json`（已入库记录）、`config/name_cache.json`（游戏名称缓存）、`manifest_records.json`（清单跟踪）

## 关键机制

### 解锁器（unlocker_type）
`CaiBackend.initialize()` 自动检测：`opensteamtools`（有 `OpenSteamTool.dll`/`opensteamtool.toml`）→ `steamtools`（`config/stplug-in/`）→ `greenluma`（`GreenLuma_2026_*.dll`），可被 `force_unlocker_type` 覆盖。**这是全项目最核心的分支逻辑。**

各类型文件位置与操作路径：

| 类型 | 解锁文件位置 | 主页 source_type |
|---|---|---|
| steamtools | `<Steam>\config\stplug-in\{appid}.lua` + `steamtools.lua` 索引 | `'st'` |
| opensteamtools | `<Steam>\config\lua\{appid}.lua`（无索引文件） | `'ost'` |
| greenluma | `<Steam>\AppList\{appid}.txt` | `'gl'` |

### 删除游戏（delete_game）
`HomePage.delete_game` → `CaiBackend.delete_managed_files(file_type, items)`。`file_type` 必须是 `st`/`gl`/`ost` 之一，否则返回失败。删除动作：改 steamtools.lua（仅 st）、删解锁文件、按 lua 内 `setManifestid` gid 删 depotcache manifest、清备份、清 manifest_records 记录。**注意**：主页 ost 游戏必须标记为 `'ost'` 类型（fluent_app.py `on_games_loaded`），标记错成 `'st'` 会导致删错目录但返回成功。

### 入库（unlock）
`SearchPage._unlock` → `process_zip_source` / `process_github_manifest` → 写解锁文件 + manifest 到 depotcache + `_mirror_lua_to_ost`（仅 OST 模式同步到 config/lua）+ 可选 `complete_manifest_files` → `_add_installed_record` 写记录。GreenLuma 会 `depotkey_merge` 密钥进 `config.vdf` 并全量重写 AppList。

### 初始化 OpenSteamTool（主页按钮）
`HomePage.on_init_ost_clicked` → `CaiBackend.install_opensteamtool`：检测 `opensteamtool.toml` 存在则跳过；否则从 GitHub release 下载 Release.zip 解压到 Steam 根目录 + 写 `[manifest] url = "wurm"`。Steam 路径查找顺序：注册表 → config → 桌面快捷方式（PowerShell 解析）→ UI 弹窗。

## 其他要点

- **翻译**：`fluent_app.py` 里 `TEXTS` 字典 + `_NEW_FEATURE_TEXTS`（新键放这里，其他语言自动回退中文），`tr(key, *args)` 取词
- **版本号**：`backend/cai_backend.py` 顶部 `CURRENT_VERSION`
- **镜像加速**：`checkcn()` 检测中国大陆 → 用 gh-proxy 镜像（`check_for_updates`/`download_ost_zip` 模式）
- **测试**：`tests/test_core.py` 用 `sys.modules` 注入 mock Qt 模块跑无 GUI 逻辑；`tests/test_core.py` 中 `_make_fake_module`/`_AnyCls` 可复用（如脚本里 `import tests.test_core as tc` 后即可导入后端模块）
- 仓库无 `.cursorrules`/Copilot 规则；README（中英文）描述特性与使用，与代码一致
