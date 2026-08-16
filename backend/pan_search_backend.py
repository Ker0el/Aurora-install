# -*- coding: utf-8 -*-
"""
全网搜下载：对接多个游戏下载站，爬取百度网盘/夸克网盘链接

站点（均需走系统代理，直连超时）：
  - gamer520.com   WordPress，文章 /{id}.html，网盘链接在二维码 img data 参数中
  - steamzg.com    文章 /{id}/，正文含 pan.baidu.com/s/xxx?pwd=6666
  - 52yx.net       搜索 /search/{kw}，文章 /{id}.html
  - playzip.com    搜索 /?s={kw}，文章 /game/{id}
  - cagames.top    经常不可达，失败跳过
  - galgamebox.com  JSON API（直连可达，无需代理）；搜索接口固定返回最新 10 个游戏需客户端过滤；
                    资源接口给网盘链接（含 pwd/code）与站点直链（dl.galgamebox.net 需登录仅展示）
"""
import re
import ssl
import json
import urllib.parse
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter("ignore", InsecureRequestWarning)

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0")

SITES = [
    {"name": "CA游戏", "api": True, "search": "https://www.cagameapi.sbs/api/games?search={kw}&page=1&platform=web",
     "detail": "https://www.cagameapi.sbs/api/games/{gid}", "page_url": "https://www.cagames.top/games/{gid}"},
    {"name": "Gamer520", "search": "https://www.gamer520.com/?s={kw}", "post_re": r'https://www\.gamer520\.com/(\d+)\.html'},
    {"name": "flysheep6", "search": "https://www.flysheep6.com/?s={kw}", "post_re": r'https://www\.flysheep6\.com/archives/\d+'},
    {"name": "PlayZip", "search": "https://playzip.com/?keywords={kw}", "post_re": r'(?:https://playzip\.com)?/game/(\d+)'},
    {"name": "123资源库", "search": "https://www.123zyk.com/?s={kw}&type=post", "post_re": r'https://www\.123zyk\.com/(\d+)'},
    # SteamZG 搜索是纯客户端 hash 路由（服务端不筛关键词，?s= 返回 500），无法服务端搜索，暂不接入
    {"name": "52游戏网", "search": "https://www.52yx.net/search/{kw}", "post_re": r'https://www\.52yx\.net/(\d+)\.html'},
    {"name": "GalgameBox", "api": True},
]


def _scan_cagames(keywords: List[str]) -> List[Dict]:
    """CA游戏站：走 JSON API（cagameapi.sbs），返回多条结果（惰性加载详情）"""
    for kw in keywords:
        if not kw:
            continue
        try:
            collected = []
            seen_ids = set()
            for page in (1, 2, 3):
                r = _http_get(SITES[0]['search'].format(kw=urllib.parse.quote(kw)).replace('page=1', f'page={page}'))
                if r is None:
                    break
                data = r.json()
                items = data.get('data', []) if isinstance(data, dict) else []
                if not items:
                    break
                for g in items:
                    gid = g.get('id')
                    title = str(g.get('title', ''))
                    if gid in seen_ids or not title:
                        continue
                    seen_ids.add(gid)
                    # 标题含关键词的才收（避免无关结果）
                    if kw.lower() in title.lower():
                        collected.append({
                            'site': 'CA游戏',
                            'title': title[:60],
                            'gid': gid,
                            'slug': g.get('slug', ''),
                            'page_url': f"https://www.cagames.top/game/{g.get('slug', '')}",
                            'baidu': [],
                            'quark': [],
                        })
                        if len(collected) >= 10:
                            break
                if len(collected) >= 10 or len(items) < 10:
                    break
            if collected:
                return collected
        except Exception:
            continue
    return []


def fetch_cagames_detail(gid) -> Dict:
    """按需查询 CA 游戏详情，返回 {baidu, quark, notice}（notice 为解压密码提示）"""
    try:
        r = _http_get(SITES[0]['detail'].format(gid=gid), timeout=10)
        if r is None:
            return {'baidu': [], 'quark': [], 'notice': ''}
        d = r.json()
        baidu, quark = [], []
        for link_key, out in (('baidu_link', baidu), ('quark_link', quark), ('uc_link', quark), ('xunlei_link', baidu)):
            link = d.get(link_key) or ''
            if link and 'pan.baidu.com/s/' in link:
                pwd_m = re.search(r'pwd=([A-Za-z0-9]+)', link)
                baidu.append({'url': link, 'pwd': pwd_m.group(1) if pwd_m else None})
            elif link and 'quark.cn/s/' in link:
                quark.append({'url': link, 'pwd': None})
        return {'baidu': baidu[:3], 'quark': quark[:3], 'notice': str(d.get('notice') or '')}
    except Exception:
        return {'baidu': [], 'quark': [], 'notice': ''}


def _system_proxies() -> Optional[Dict[str, str]]:
    """从 Windows 注册表读取系统代理（Clash 类）"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')
        enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
        server, _ = winreg.QueryValueEx(key, 'ProxyServer')
        winreg.CloseKey(key)
        if enable and server:
            if '://' not in server:
                server = 'http://' + server
            return {'http': server, 'https': server}
    except Exception:
        pass
    # 环境变量兜底
    for k in ('HTTPS_PROXY', 'https_proxy', 'HTTP_PROXY', 'http_proxy'):
        v = __import__('os').environ.get(k)
        if v:
            return {'http': v, 'https': v}
    return None


def _http_get(url: str, timeout: int = 10) -> Optional[requests.Response]:
    """代理优先请求（这些站直连超时，必须走代理），失败 cloudscraper 兜底"""
    headers = {'User-Agent': UA, 'Accept': 'text/html,*/*'}
    proxies = _system_proxies()
    # 1. 系统代理
    if proxies:
        try:
            r = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, verify=False)
            if r.status_code == 200:
                return r
        except Exception:
            pass
    # 2. 直连
    try:
        r = requests.get(url, headers=headers, timeout=timeout, verify=False)
        if r.status_code == 200:
            return r
    except Exception:
        pass
    # 3. cloudscraper 兜底
    if cloudscraper:
        try:
            scraper = cloudscraper.create_scraper()
            r = scraper.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r
        except Exception:
            pass
    return None


def _extract_links(html: str) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """从文章 HTML 提取百度/夸克/迅雷/其他网盘链接与提取码"""
    baidu, quark, xunlei, other = [], [], [], []
    # 百度网盘：pan.baidu.com/s/{id}?pwd={code}
    for m in re.finditer(r'https?://pan\.baidu\.com/s/([A-Za-z0-9_\-]+)', html):
        link_id = m.group(1)
        seg = html[m.start():m.start() + 300]
        pwd_m = re.search(r'pwd=([A-Za-z0-9]+)', seg)
        pwd = pwd_m.group(1) if pwd_m else None
        url = f"https://pan.baidu.com/s/{link_id}" + (f"?pwd={pwd}" if pwd else "")
        if url not in [b['url'] for b in baidu]:
            baidu.append({'url': url, 'pwd': pwd})
    # 夸克网盘
    for m in re.finditer(r'https?://pan\.quark\.cn/s/([A-Za-z0-9]+)', html):
        url = f"https://pan.quark.cn/s/{m.group(1)}"
        if url not in [q['url'] for q in quark]:
            quark.append({'url': url, 'pwd': None})
    # 迅雷网盘
    for m in re.finditer(r'https?://pan\.xunlei\.com/s/([A-Za-z0-9]+)', html):
        seg = html[m.start():m.start() + 300]
        pwd_m = re.search(r'pwd=([A-Za-z0-9]+)', seg)
        pwd = pwd_m.group(1) if pwd_m else None
        url = f"https://pan.xunlei.com/s/{m.group(1)}" + (f"?pwd={pwd}" if pwd else "")
        if url not in [x['url'] for x in xunlei]:
            xunlei.append({'url': url, 'pwd': pwd})
    # 123资源库自建网盘（中转页，API 解出真实夸克链接）
    for m in re.finditer(r'https?://pan\.123zyk\.com/s/([A-Za-z0-9]+)', html):
        url = f"https://pan.123zyk.com/s/{m.group(1)}"
        if url not in [o['url'] for o in other]:
            other.append({'url': url, 'pwd': None, 'name': '123网盘'})
    # 提取码（gamer520 等：提取码: <strong>xxx</strong> 或 提取码：xxx）
    if not baidu:
        for m in re.finditer(r'提取码[：:\s]*<strong>([A-Za-z0-9]{4})</strong>', html):
            pwd = m.group(1)
            if baidu:
                baidu[0]['pwd'] = pwd
                baidu[0]['url'] = baidu[0]['url'].split('?')[0] + f"?pwd={pwd}"
            break
    # gamer520：二维码图片 data 参数（URL 编码的完整链接）
    if not baidu and not quark:
        for m in re.finditer(r'qrserver\.com[^"\']*data=([^"&\'<>]+)', html):
            try:
                decoded = urllib.parse.unquote(m.group(1))
                if 'pan.baidu.com/s/' in decoded:
                    pwd_m = re.search(r'pwd=([A-Za-z0-9]+)', decoded)
                    baidu.append({'url': decoded, 'pwd': pwd_m.group(1) if pwd_m else None})
                elif 'pan.quark.cn/s/' in decoded:
                    quark.append({'url': decoded, 'pwd': None})
            except Exception:
                continue
    # 通用提取码：百度链接后跟"提取码：xxxx"（gamer520 明文格式）
    if baidu and not baidu[0].get('pwd'):
        for m in re.finditer(r'pan\.baidu\.com/s/[A-Za-z0-9_\-]+[^<]{0,60}?提取码[：:\s]*([A-Za-z0-9]{4})', html):
            baidu[0]['pwd'] = m.group(1)
            baidu[0]['url'] = baidu[0]['url'].split('?')[0] + f"?pwd={m.group(1)}"
            break
    return baidu, quark, xunlei, other


def _resolve_123zyk_quark(pan_url: str) -> str | None:
    """123网盘中转页 → 调 /get-url?id= 解出真实夸克链接"""
    try:
        rid = pan_url.rstrip('/').rsplit('/', 1)[-1]
        r = _http_get(f"https://pan.123zyk.com/get-url?id={rid}", timeout=8)
        if r is None:
            return None
        data = r.json()
        url = data.get('url', '') if isinstance(data, dict) else ''
        if url and 'pan.quark.cn/s/' in url:
            return url
    except Exception:
        pass
    return None


def _scan_site(site: Dict, keywords: List[str]) -> List[Dict]:
    """扫描单个站点，返回多条 {site, title, page_url, baidu, quark}"""
    for kw in keywords:
        if not kw:
            continue
        search_url = site['search'].format(kw=urllib.parse.quote(kw))
        r = _http_get(search_url)
        if r is None:
            continue
        # 提取文章链接与标题
        post_urls, titles = [], []
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.DOTALL):
            href, text = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if re.match(site['post_re'], href) and href not in post_urls and text:
                post_urls.append(href)
                titles.append(text)
            if len(post_urls) >= 30:
                break
        if not post_urls:
            continue
        # 收集所有标题含关键词的文章（最多 5 条）
        kw_norm = [k.lower() for k in keywords if k]
        matched = []
        for i, t in enumerate(titles):
            tl = t.lower()
            if any(kn in tl or tl in kn for kn in kw_norm):
                url = post_urls[i]
                if not url.startswith('http'):
                    url = urllib.parse.urljoin(site['search'], url)
                matched.append({'site': site['name'], 'title': t[:60], 'page_url': url,
                                'baidu': [], 'quark': []})
                if len(matched) >= 5:
                    break
        if not matched:
            continue
        # 只对第一条文章页提取网盘链接（避免 N 次请求拖慢搜索）
        first = matched[0]['page_url']
        r2 = _http_get(first)
        if r2 is not None:
            baidu, quark, xunlei, other = _extract_links(r2.text)
            matched[0]['baidu'] = baidu[:3]
            matched[0]['quark'] = quark[:3]
            matched[0]['xunlei'] = xunlei[:3]
            # 123网盘中转页 → 解真实夸克链接
            for o in other[:3]:
                real = _resolve_123zyk_quark(o['url'])
                if real:
                    matched[0]['quark'].append({'url': real, 'pwd': None})
        return matched
    return []


def _scan_galgamebox(keywords: List[str], appid: str = "") -> List[Dict]:
    """GalgameBox：JSON API（直连可达）。title= 参数服务端模糊过滤但截断 10 条，短词会漏老游戏，
    故按关键词逐个查询合并；首条命中走 /api/game/{uniqueId} 详情拿完整资源（网盘+直链+解压密码）"""
    kw_norm = [k.lower() for k in keywords if k]
    seen = {}
    for kw in keywords:
        if not kw:
            continue
        try:
            r = _http_get("https://galgamebox.com/api/games?title=" + urllib.parse.quote(kw))
            if r is None:
                continue
            games = (r.json().get('data') or {}).get('games') or []
            for g in games:
                gid = g.get('id')
                if not gid or gid in seen:
                    continue
                name = str(g.get('name') or '')
                alt = g.get('altNames') or []
                sid = str(g.get('steamAppId') or '')
                if appid and appid.isdigit() and sid == appid:
                    pass  # appid 精确命中
                elif not any(k in name.lower() or any(k in (a or '').lower() for a in alt) for k in kw_norm):
                    continue
                seen[gid] = g
        except Exception:
            continue
    if not seen:
        return []
    # 首条深查详情拿完整资源，其余仅给标题+链接
    results = []
    for i, g in enumerate(list(seen.values())[:5]):
        gid = g.get('id')
        uid = g.get('uniqueId')
        base = {
            'site': 'GalgameBox',
            'title': str(g.get('name') or '')[:60],
            'page_url': f"https://galgamebox.com/game/{uid or gid}",
            'baidu': [], 'quark': [], 'xunlei': [], 'direct': [], 'notice': '',
        }
        if i == 0:
            r2 = _http_get(f"https://galgamebox.com/api/game/{uid}", timeout=10)
            if r2 is not None:
                d = (r2.json() or {}).get('data') or {}
                base.update(_parse_galgamebox_resources(d.get('resources') or []))
                base['title'] = str(d.get('name') or base['title'])[:60]
        results.append(base)
    return results


def _parse_galgamebox_resources(res_list: List[Dict]) -> Dict:
    """GalgameBox 资源列表 → {baidu, quark, xunlei, direct, notice}"""
    baidu, quark, xunlei, direct = [], [], [], []
    notice = ''
    for res in res_list:
        code = res.get('code') or ''
        if res.get('unzipCode'):
            notice = str(res['unzipCode'])
        for u in (res.get('urls') or []):
            if 'pan.baidu.com/s/' in u:
                m = re.search(r'pwd=([A-Za-z0-9]+)', u)
                pwd = m.group(1) if m else (code or None)
                url = u.split('?')[0] + (f"?pwd={pwd}" if pwd else "")
                if url not in [b['url'] for b in baidu]:
                    baidu.append({'url': url, 'pwd': pwd})
            elif 'pan.quark.cn/s/' in u:
                if u not in [q['url'] for q in quark]:
                    quark.append({'url': u, 'pwd': code or None})
            elif 'pan.xunlei.com/s/' in u:
                if u not in [x['url'] for x in xunlei]:
                    xunlei.append({'url': u, 'pwd': code or None})
            elif 'dl.galgamebox.net/' in u:
                if u not in [d['url'] for d in direct]:
                    direct.append({'url': u, 'size': res.get('size') or ''})
    return {'baidu': baidu[:3], 'quark': quark[:3], 'xunlei': xunlei[:3],
            'direct': direct[:3], 'notice': notice}


def _scan_jidiyouxi(keywords: List[str]) -> List[Dict]:
    """jidiyouxi：搜索页内嵌 JSON（topic id + 标题），详情页 content 字段含网盘链接（/ 转义）"""
    for kw in keywords:
        if not kw:
            continue
        try:
            r = _http_get(f"https://www.jidiyouxi.com/?s={urllib.parse.quote(kw)}")
            if r is None:
                continue
            html = r.text
            # 提取匹配关键词的 topic（JSON: "id":xxx,"topic":"标题"）
            found = []
            for m in re.finditer(r'"id":(\d+),"tid":\1,"topic":"([^"]+)"', html):
                tid, topic = m.group(1), m.group(2).replace('\\u002F', '/').replace('\\"', '"')
                if kw.lower() in topic.lower():
                    found.append((tid, topic))
            if not found:
                continue
            # 取第一条详情页提取网盘链接
            tid, topic = found[0]
            r2 = _http_get(f"https://www.jidiyouxi.com/topic/detail/{tid}")
            baidu, quark, xunlei = [], [], []
            if r2 is not None:
                content = r2.text.replace('\\u002F', '/')
                baidu, quark, xunlei, _other = _extract_links(content)
            results = [{
                'site': 'jidiyouxi',
                'title': topic[:60],
                'page_url': f"https://www.jidiyouxi.com/topic/detail/{tid}",
                'baidu': baidu[:3],
                'quark': quark[:3],
                'xunlei': xunlei[:3],
            }]
            # 其余匹配的 topic 只给标题+链接（不逐条查详情）
            for tid2, topic2 in found[1:4]:
                results.append({
                    'site': 'jidiyouxi',
                    'title': topic2[:60],
                    'page_url': f"https://www.jidiyouxi.com/topic/detail/{tid2}",
                    'baidu': [], 'quark': [], 'xunlei': [],
                })
            return results
        except Exception:
            continue
    return []


def search_game_downloads(game_name_zh: str, game_name_en: str, appid: str = "") -> List[Dict]:
    """并行搜索所有站点。返回 [{site, title, page_url, baidu:[{url,pwd}], quark:[{url,pwd}]}]"""
    keywords = []
    for k in (game_name_en, game_name_zh):
        if k and k not in keywords and (len(k) > 1 or any(ord(c) > 0x2E80 for c in k)):
            keywords.append(k)
            # 截断变体：官方源名称常带后缀（如 "- Deluxe Upgrade"），去掉分隔符后的短名提高匹配率
            for sep in (' - ', ' — ', '：', ': ', '（'):
                short = k.split(sep)[0].strip()
                if len(short) > 1 and short != k and short not in keywords:
                    keywords.append(short)
                    break
    if appid and appid.isdigit():
        keywords.append(appid)

    results = []
    pool = ThreadPoolExecutor(max_workers=len(SITES) + 2)
    futures = {pool.submit(_scan_cagames, keywords): 'CA游戏'}
    futures[pool.submit(_scan_jidiyouxi, keywords)] = 'jidiyouxi'
    futures[pool.submit(_scan_galgamebox, keywords, appid)] = 'GalgameBox'
    for site in SITES[1:]:
        futures[pool.submit(_scan_site, site, keywords)] = site['name']
    try:
        for fut in as_completed(futures, timeout=25):
            try:
                res = fut.result()
                if isinstance(res, list):
                    results.extend(res)  # CA游戏返回多条
                elif res and (res['baidu'] or res['quark'] or res['page_url']):
                    results.append(res)
            except Exception:
                continue
    except TimeoutError:
        pass  # 超时的站点放弃，已完成的照常收集
    pool.shutdown(wait=False, cancel_futures=True)  # 不阻塞 UI，未完成线程后台退出
    # 有网盘链接的排前面
    results.sort(key=lambda x: (1 if (x['baidu'] or x['quark']) else 0), reverse=True)
    return results
