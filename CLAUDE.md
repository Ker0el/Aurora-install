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
- **数据文件**：`config/config.json`（配置，含 `Custom_Steam_Path`、`force_unlocker_type`、`pan_search_default`）、`config/installed_games.json`（已入库记录，运行时生成）、`config/name_cache.json`（游戏名称缓存，gitignore）、`manifest_records.json`（清单跟踪，运行时生成，项目根目录且未 gitignore）

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
`HomePage.delete_game` → `CaiBackend.delete_managed_files(file_type, items)`。`file_type` 必须是 `st`/`gl`/`ost` 之一，否则返回失败。删除动作：改 steamtools.lua（st 和 ost 都改）、删解锁文件、按 lua 内 `setManifestid` gid 删 depotcache manifest、清备份、清 manifest_records 记录。**注意**：主页 ost 游戏必须标记为 `'ost'` 类型（fluent_app.py `on_games_loaded`），标记错成 `'st'` 会导致删错目录但返回成功。隐患仍在：`on_games_loaded` 的记录回退路径（磁盘解锁文件缺失、靠 installed_games.json 补全时）会把所有非 GL 记录标成 `'st'`，OST 游戏经此路径仍可能被标错。

### 入库（unlock）
`SearchPage._unlock` → `process_zip_source` / `process_github_manifest` → 写解锁文件 + manifest 到 depotcache + `_mirror_lua_to_ost`（仅 OST 模式同步到 config/lua）+ 可选 `complete_manifest_files` → `_add_installed_record` 写记录。GreenLuma 会 `depotkey_merge` 密钥进 `config.vdf` 并全量重写 AppList。

### 初始化 OpenSteamTool（主页按钮）
`HomePage.on_init_ost_clicked` → `CaiBackend.install_opensteamtool`：检测 `opensteamtool.toml` 存在则跳过；否则从 GitHub release 下载 Release.zip 解压到 Steam 根目录 + 写 `[manifest] url = "wurm"`。Steam 路径查找顺序：config 的 `Custom_Steam_Path` → 注册表 → 桌面快捷方式（PowerShell 解析）→ UI 弹窗。

### 全网搜下载（v1.7，搜索页面）
`backend/pan_search_backend.py`：搜索游戏下载站拿百度/夸克/迅雷网盘链接。入口 `search_game_downloads(name_zh, name_en, appid)`，ThreadPoolExecutor 并行扫多个站点（CA游戏 JSON API `cagameapi.sbs`、Gamer520、flysheep6、PlayZip、123资源库、52游戏网、jidiyouxi、GalgameBox；SteamZG 已排除），25s 超时非阻塞关闭；`_extract_links` 正则提取网盘链接+提取码，`_resolve_123zyk_quark` 解析 123 中转页到真实夸克链接；`_http_get` 三级网络：系统代理（读 Windows 注册表）→ 直连 → cloudscraper，**这些站点需代理，直连会超时**（例外：GalgameBox 直连可达）。关键词过滤：`len>1` 或含中文字符（单字中文如"涩"要放行）。

GalgameBox 走 `_scan_galgamebox`：`games?title={kw}` 服务端模糊过滤但**截断 10 条**（短词会漏老游戏），需按关键词逐个查询合并去重（uniqueId）+ 客户端按 name/altNames/steamAppId 再过滤；首条命中走 `GET /api/game/{uniqueId}` 详情一次拿全 resources（网盘链接 pwd/code + `dl.galgamebox.net` 站点直链——裸链被 Cloudflare 拦仅展示，`unzipCode` 作解压密码），其余命中条仅给标题+链接。

SearchPage 集成：**「搜下载站」复选框 `pan_search_check`（默认勾选，偏好存配置键 `pan_search_default`）**；Steam 搜不到结果时回退全网搜（用**用户输入原词**），搜到结果时后台并行全网搜并把结果卡合并进列表（合成 `appid='pan-N'`）；**下载站关键词用用户原词优先、Steam 结果名作第二词**（`_search_pan_sites`→`_run_pan_search(appid, query, steam_name)`，单字/别名场景 Steam 名反而搜不到）；结果卡右键「全网搜下载」→ `PanSearchResultsDialog` 逐站展示文章链接+网盘链接+提取码+直链；`PanResultCard` 懒加载 CA 详情 `fetch_cagames_detail`。后台走 `_replace_worker(pan_search_worker)` 标准模式。新翻译键放 `_NEW_FEATURE_TEXTS`。

## 其他要点

- **翻译**：`fluent_app.py` 里 `TEXTS` 字典 + `_NEW_FEATURE_TEXTS`（新键放这里，其他语言自动回退中文），`tr(key, *args)` 取词
- **版本号**：`backend/cai_backend.py` 顶部 `CURRENT_VERSION`
- **镜像加速**：`checkcn()` 检测中国大陆 → 用 gh-proxy 镜像（`check_for_updates`/`download_ost_zip` 模式）
- **测试**：`tests/test_core.py` 用 `sys.modules` 注入 mock Qt 模块跑无 GUI 逻辑；`tests/test_core.py` 中 `_make_fake_module`/`_AnyCls` 可复用（如脚本里 `import tests.test_core as tc` 后即可导入后端模块）
- 仓库无 `.cursorrules`/Copilot 规则；README（中英文）未提全网搜和 GBE，描述已滞后于 v1.7
- **打包注意**：`build_exe.py`/`AuroraInstall.spec` 含已不存在的 hidden-import/数据目录引用（`backend.authorizer_backend`、`backend.cw_extractor_core`、`backend/GBE_Patch`、`backend/GreenLuma_2026_1.7.4-Steam006`），打包异常先查此处；`Resource.json`（顶层的资源站数据）目前无代码引用
