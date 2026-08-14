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


def _find_steam_api(root: Path) -> Optional[Tuple[Path, str, str]]:
    """递归遍历 root（深度≤4）找 steam_api*.dll。
    返回 (dll所在目录, 文件名, 位宽)；优先级：根目录 > 浅层子目录 > 全树。
    跳过隐藏目录（.git 等）与 Steam 自身目录。"""
    import os

    def _walk(d: Path, depth: int) -> Optional[Tuple[Path, str, str]]:
        if depth > 4:
            return None
        try:
            # 先看本目录
            for fname, bit in [('steam_api64.dll', 'x64'), ('steam_api.dll', 'x86')]:
                if (d / fname).exists():
                    return d, fname, bit
            # 递归子目录
            for sub in sorted(d.iterdir()):
                if not sub.is_dir() or sub.name.startswith('.') or sub.name.lower() == 'steam':
                    continue
                r = _walk(sub, depth + 1)
                if r:
                    return r
        except Exception:
            pass
        return None

    return _walk(root, 0)


def detect_steam_api(game_dir: Path) -> Optional[Tuple[Path, str, str]]:
    """检测游戏目录（含子目录树）的 steam_api，返回 (dll所在目录, 文件名, 位宽)，无则 None"""
    return _find_steam_api(game_dir)


def _normalize_name(s: str) -> str:
    """归一化目录名/游戏名用于模糊匹配（小写、去空格、去标点）"""
    import re as _re
    return _re.sub(r'[^a-z0-9一-鿿]', '', s.lower())


def detect_appid(game_dir: Path) -> Optional[str]:
    """自动检测游戏 AppID：
    1. 已有 steam_appid.txt 直接读
    2. 反向全库扫描 steamapps/appmanifest_*.acf（精确 + 模糊匹配目录名）
    3. 入库记录匹配
    返回 appid 字符串，找不到返回 None
    """
    # 1. 已有 steam_appid.txt
    sa = game_dir / 'steam_appid.txt'
    if sa.exists():
        v = sa.read_text(encoding='utf-8').strip()
        if v.isdigit():
            return v

    # 2. 反向全库扫描 steamapps/appmanifest_*.acf
    import re
    steamapps = game_dir.parent.parent  # common → steamapps
    target = _normalize_name(game_dir.name)
    best = None
    for mf in steamapps.glob('appmanifest_*.acf'):
        try:
            txt = mf.read_text(encoding='utf-8', errors='ignore')
            m_appid = re.search(r'"appid"\s+"(\d+)"', txt)
            m_dir = re.search(r'"installdir"\s+"([^"]+)"', txt)
            if not (m_appid and m_dir):
                continue
            install = _normalize_name(m_dir.group(1))
            # 精确匹配
            if install == target:
                return m_appid.group(1)
            # 模糊匹配：包含关系
            if target and (target in install or install in target):
                if best is None:
                    best = m_appid.group(1)
        except Exception:
            continue
    if best:
        return best

    # 3. 记录匹配（installed_games.json）
    try:
        import json
        rec_path = Path(__file__).resolve().parent.parent / 'config' / 'installed_games.json'
        if rec_path.exists():
            recs = json.loads(rec_path.read_text(encoding='utf-8'))
            for r in recs:
                if _normalize_name(str(r.get('name', ''))) == target and str(r.get('appid', '')).isdigit():
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

        dll_dir, fname, bit = detect
        gbe_dll = _gbe_dll_dir() / fname
        if not gbe_dll.exists():
            return {"success": False, "message": f"assets/gbe/{fname} 不存在，请先下载 GBE dll 放入（见 assets/gbe/README.txt）"}

        # 1. 备份原 dll（已有备份说明已应用过，跳过）
        bak = dll_dir / (fname + '.bak')
        if not bak.exists():
            shutil.copy2(dll_dir / fname, bak)

        # 2. 复制 GBE dll（替换到 dll 所在目录）
        shutil.copy2(gbe_dll, dll_dir / fname)

        # 3. 写 steam_appid.txt（GBE 惯例：与 dll 同目录）
        (dll_dir / 'steam_appid.txt').write_text(str(appid), encoding='utf-8')

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
    """还原原 dll（递归找 .bak 备份，恢复原版）"""
    try:
        found = []
        for d in game_dir.rglob('*'):
            if not d.is_dir():
                continue
            for fname in ['steam_api64.dll', 'steam_api.dll']:
                bak = d / (fname + '.bak')
                if bak.exists():
                    shutil.copy2(bak, d / fname)
                    bak.unlink()
                    found.append(f"{fname} ({d.relative_to(game_dir)})")
        if found:
            return {"success": True, "message": f"已还原: {', '.join(found[:3])}"}
        return {"success": False, "message": "没有找到备份 dll"}
    except Exception as e:
        return {"success": False, "message": f"还原失败: {e}"}


def launch_game(game_dir: Path) -> dict:
    """启动游戏（免 Steam），自动找 exe：根目录优先，找不到递归（深度 4）"""
    if not game_dir.exists():
        return {"success": False, "message": "游戏目录不存在"}

    def _find_exe(d: Path, depth: int):
        if depth > 4:
            return None
        for f in sorted(d.glob('*.exe')):
            if 'unins' not in f.name.lower():
                return f
        for sub in sorted(d.iterdir()):
            if sub.is_dir() and not sub.name.startswith('.'):
                r = _find_exe(sub, depth + 1)
                if r:
                    return r
        return None

    exe = _find_exe(game_dir, 0)
    if not exe:
        return {"success": False, "message": "未找到游戏 exe"}
    try:
        subprocess.Popen([str(exe)], cwd=str(exe.parent))
        return {"success": True, "message": f"已启动: {exe.name}"}
    except Exception as e:
        return {"success": False, "message": f"启动失败: {e}"}
