# -*- coding: utf-8 -*-
"""
GBE (Goldberg Emulator) 免 Steam 启动支持

用法说明：
1. 下载 GBE（官方开源）：https://github.com/Detanup01/gbe_fork/releases
   → 最新版 → emu-win-release.7z（Windows 版）
2. 解压后把 steam_api64.dll 和 steam_api.dll 复制到本目录（assets/gbe/）
3. 在软件主页点「免 Steam 启动」，选择游戏目录即可

原理：备份游戏目录原 steam_api*.dll 为 .bak → 替换为 GBE 模拟层
     → 写 steam_appid.txt（游戏 AppID）→ 游戏不经过 Steam 直接启动
还原：点「还原 GBE」把 .bak 恢复原样
"""
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


def _gbe_dll_dir() -> Path:
    """GBE dll 所在目录（打包后 assets 在 _MEIPASS，开发时在项目下）"""
    if getattr(sys, 'frozen', False):
        base = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / 'assets' / 'gbe'


def detect_steam_api(game_dir: Path) -> Optional[Tuple[str, str]]:
    """检测游戏目录的 steam_api 类型，返回 (文件名, 位宽)，无则 None"""
    for fname, bit in [('steam_api64.dll', 'x64'), ('steam_api.dll', 'x86')]:
        if (game_dir / fname).exists():
            return fname, bit
    return None


def detect_appid(game_dir: Path) -> Optional[str]:
    """自动检测游戏 AppID：
    1. 已有 steam_appid.txt 直接读
    2. 扫描上级 steamapps/appmanifest_*.acf 匹配 installdir
    3. 从游戏目录名在 installed_games 记录里匹配
    返回 appid 字符串，找不到返回 None
    """
    # 1. 已有 steam_appid.txt
    sa = game_dir / 'steam_appid.txt'
    if sa.exists():
        v = sa.read_text(encoding='utf-8').strip()
        if v.isdigit():
            return v

    # 2. 扫描 steamapps/appmanifest_*.acf（game_dir 位于 steamapps/common/<game>）
    steamapps = game_dir.parent.parent  # common → steamapps
    for mf in steamapps.glob('appmanifest_*.acf'):
        try:
            txt = mf.read_text(encoding='utf-8', errors='ignore')
            import re
            m_appid = re.search(r'"appid"\s+"(\d+)"', txt)
            m_dir = re.search(r'"installdir"\s+"([^"]+)"', txt)
            if m_appid and m_dir and m_dir.group(1).lower() == game_dir.name.lower():
                return m_appid.group(1)
        except Exception:
            continue

    # 3. 记录匹配（installed_games.json）
    try:
        import json
        rec_path = Path(__file__).resolve().parent.parent / 'config' / 'installed_games.json'
        if rec_path.exists():
            recs = json.loads(rec_path.read_text(encoding='utf-8'))
            name = game_dir.name.lower()
            for r in recs:
                if str(r.get('name', '')).lower() == name and str(r.get('appid', '')).isdigit():
                    return str(r['appid'])
    except Exception:
        pass

    return None


def apply_gbe(game_dir: Path, appid: str, mode: str = "emu") -> dict:
    """对游戏目录应用 GBE。
    mode="emu"：完整模式（dll + steam_appid.txt + steam_settings 配置目录）
    mode="lite"：轻量模式（只 dll + steam_appid.txt，不建配置目录）
    """
    try:
        if not game_dir.exists():
            return {"success": False, "message": "游戏目录不存在"}
        detect = detect_steam_api(game_dir)
        if not detect:
            return {"success": False, "message": "未找到 steam_api*.dll，可能不是 Steamworks 游戏"}

        fname, bit = detect
        gbe_dll = _gbe_dll_dir() / fname
        if not gbe_dll.exists():
            return {"success": False, "message": f"assets/gbe/{fname} 不存在，请先下载 GBE dll 放入（见 assets/gbe/README.txt）"}

        # 1. 备份原 dll（已有备份说明已应用过，跳过）
        bak = game_dir / (fname + '.bak')
        if not bak.exists():
            shutil.copy2(game_dir / fname, bak)

        # 2. 复制 GBE dll
        shutil.copy2(gbe_dll, game_dir / fname)

        # 3. 写 steam_appid.txt
        (game_dir / 'steam_appid.txt').write_text(str(appid), encoding='utf-8')

        # 4. 完整模式：创建 steam_settings 基本配置
        if mode == "emu":
            ss = game_dir / 'steam_settings'
            ss.mkdir(exist_ok=True)
            (ss / 'README.txt').write_text(
                "Goldberg Emulator 配置目录\n"
                "- account_name.txt: 玩家名\n"
                "- user_steam_id.txt: SteamID（64位）\n"
                "- configs/ 下放 DLC 解锁等配置\n",
                encoding='utf-8'
            )

        mode_name = "完整模式" if mode == "emu" else "轻量模式"
        return {"success": True, "message": f"已应用 GBE {mode_name}（{bit}），原 dll 已备份为 {fname}.bak"}
    except Exception as e:
        return {"success": False, "message": f"应用失败: {e}"}


def restore_gbe(game_dir: Path) -> dict:
    """还原原 dll（删除 GBE 文件，恢复 .bak）"""
    try:
        for fname in ['steam_api64.dll', 'steam_api.dll']:
            bak = game_dir / (fname + '.bak')
            if bak.exists():
                shutil.copy2(bak, game_dir / fname)
                bak.unlink()
                return {"success": True, "message": f"已还原 {fname} 原版"}
        return {"success": False, "message": "没有找到备份 dll"}
    except Exception as e:
        return {"success": False, "message": f"还原失败: {e}"}


def launch_game(game_dir: Path) -> dict:
    """启动游戏（免 Steam），自动找 exe（跳过卸载程序）"""
    if not game_dir.exists():
        return {"success": False, "message": "游戏目录不存在"}
    exe = None
    for f in sorted(game_dir.glob('*.exe')):
        if 'unins' not in f.name.lower():
            exe = f
            break
    if not exe:
        return {"success": False, "message": "未找到游戏 exe"}
    try:
        subprocess.Popen([str(exe)], cwd=str(game_dir))
        return {"success": True, "message": f"已启动: {exe.name}"}
    except Exception as e:
        return {"success": False, "message": f"启动失败: {e}"}
