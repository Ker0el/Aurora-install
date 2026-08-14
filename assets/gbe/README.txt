GBE (Goldberg Emulator) DLL 放置说明
====================================

1. 打开下载页（官方开源项目）：
   https://github.com/Detanup01/gbe_fork/releases

2. 下载最新版（如 release-2026_07_19）的：
   emu-win-release.7z   （Windows 版）

3. 用 7-Zip 解压，找到这两个文件：
   steam_api64.dll   （64 位游戏用）
   steam_api.dll     （32 位游戏用）

4. 把这两个 dll 复制到本目录（assets/gbe/）下：
   D:\111\Aurora-install\assets\gbe\
   （打包进 exe 后软件会自动从内部读取，无需额外操作）

5. 之后在软件主页点「免 Steam 启动」，选择游戏目录即可。
   软件会自动：备份原 dll → 替换 GBE → 写 steam_appid.txt → 启动游戏。
   还原点「还原 GBE」。
