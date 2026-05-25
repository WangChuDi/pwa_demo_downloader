import requests
import hashlib
import json
import zipfile
import os
import random
import subprocess
import sys
import time

import configparser

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

url_getmatchid = 'https://pwaweblogin.wmpvp.com/user-info/recent-ladder-score-list'

# demo URL 默认使用内置签名实现。
# PvpAlive.dll 保留为 fallback 通道，可通过 PWA_SIGN_BACKEND=dll 强制使用。
PVP_WEB_API_APPID = 20000
PVP_SIGN_TAIL64 = "969c1bcfdc527c319157cc48f83b1d106ebdeca3e8d9763f1ae6b88dde9b3ea9"
_ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON32_EXE = os.path.join(_ROOT, "python32", "python.exe")
SIGN_HELPER = os.path.join(_ROOT, "sign_helper.py")
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'perfectworldarena/1.0.26051411 Chrome/80.0.3987.163 Electron/8.5.5 Safari/537.36'
)

# 自动探测 PvpAlive.dll 的常见安装路径（按优先级）。
# 用户可在 config.ini 的 [global] 段用 pvp_alive_dll 字段显式覆盖。
COMMON_DLL_PATHS = [
    r"D:\ProgramFile\game\perfectworld\plugin\PvpAlive.dll",
    r"C:\Program Files\perfectworld\plugin\PvpAlive.dll",
    r"C:\Program Files (x86)\perfectworld\plugin\PvpAlive.dll",
    r"D:\perfectworld\plugin\PvpAlive.dll",
    r"C:\perfectworld\plugin\PvpAlive.dll",
]

PVP_ALIVE_DLL_PATH = ""
_runtime_config = None


def _resolve_dll_path(cf) -> str:
    """优先 [global].pvp_alive_dll；否则按 COMMON_DLL_PATHS 探测；都失败则给出指引并退出。"""
    configured = ""
    if cf.has_section("global") and cf.has_option("global", "pvp_alive_dll"):
        configured = cf.get("global", "pvp_alive_dll").strip()
    if configured:
        if os.path.isfile(configured):
            return configured
        sys.exit(
            f"config.ini [global] pvp_alive_dll 指向的文件不存在: {configured}\n"
            f"请检查路径，或留空让程序按常见安装位置自动探测。"
        )
    for p in COMMON_DLL_PATHS:
        if os.path.isfile(p):
            return p
    sys.exit(
        "找不到 PvpAlive.dll。请在 config.ini 加上:\n"
        "  [global]\n"
        "  pvp_alive_dll = <PvpAlive.dll 的绝对路径>\n"
        "通常位于：完美对战平台客户端安装目录\\plugin\\PvpAlive.dll\n"
        "(右键桌面/任务栏的「完美对战平台」快捷方式 → 打开文件所在位置即可定位)"
    )


def _load_config():
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = configparser.ConfigParser(interpolation=None)
        _runtime_config.read("config.ini")
    return _runtime_config


def _get_pvp_alive_dll_path() -> str:
    global PVP_ALIVE_DLL_PATH
    if not PVP_ALIVE_DLL_PATH:
        PVP_ALIVE_DLL_PATH = _resolve_dll_path(_load_config())
    return PVP_ALIVE_DLL_PATH


def _require_python32():
    if not os.path.isfile(PYTHON32_EXE):
        sys.exit(
            f"missing 32-bit Python: {PYTHON32_EXE}\n"
            f"sign_helper.py 需要 32 位 Python 才能加载 PvpAlive.dll。"
            f"请从 python.org 下载 python-3.12.x-embed-win32.zip 解压到 python32/。"
        )


def _pure_swap_data_sign(randnum: str, ts: str, data: str) -> str:
    prefix = hashlib.md5((randnum + ts + data).encode("utf-8")).hexdigest()
    payload = f"{PVP_WEB_API_APPID}{prefix}{PVP_SIGN_TAIL64}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _dll_swap_data_sign(randnum: str, ts: str, data: str) -> str:
    _require_python32()
    inner = json.dumps(
        {"randnum": randnum, "ts": ts, "data": data, "version": 1},
        separators=(",", ":"),
    )
    res = subprocess.run(
        [PYTHON32_EXE, SIGN_HELPER, _get_pvp_alive_dll_path(), inner],
        capture_output=True, text=True, check=True,
    )
    sig = res.stdout.strip()
    if not sig:
        raise RuntimeError(f"swapData returned empty: {res.stderr}")
    return sig


def _swap_data_sign(randnum: str, ts: str, data: str) -> str:
    if os.environ.get("PWA_SIGN_BACKEND", "").strip().lower() == "dll":
        return _dll_swap_data_sign(randnum, ts, data)
    try:
        return _pure_swap_data_sign(randnum, ts, data)
    except Exception:
        return _dll_swap_data_sign(randnum, ts, data)


def _x_pwa_signature(steamid: str, ts: int, ip_addr: str) -> str:
    """
    复刻 background.js 的 getRefererHeader():
      key = (ts_str + steamid[ts_len-16:])  # 共 16 字节,后半截从 steamid 末尾切
      iv  = steamid[-16:]                    # 16 字节
      plaintext = ipAddr (服务器告知的客户端公网 IP)
      sig = "{ts}-" + AES-128-CBC(key, iv, plaintext, PKCS7).hex()
    """
    iv = steamid[-16:].encode("utf-8")
    n_str = str(ts)
    key = (n_str + steamid[len(n_str) - 16:]).encode("utf-8")
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    padder = PKCS7(128).padder()
    padded = padder.update(ip_addr.encode("utf-8")) + padder.finalize()
    return f"{ts}-{(cipher.update(padded) + cipher.finalize()).hex()}"


_public_ip_cache = None


def _get_public_ip() -> str:
    global _public_ip_cache
    if _public_ip_cache:
        return _public_ip_cache
    for url in ("https://api.ipify.org/", "https://ifconfig.me/ip"):
        try:
            ip = requests.get(url, timeout=10).text.strip()
            # 只接受 IPv4 - wmpvp 后端按 IPv4 比对
            parts = ip.split(".")
            if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) < 256 for p in parts):
                _public_ip_cache = ip
                return ip
        except Exception:
            continue
    raise RuntimeError("无法获取公网 IPv4,X-PWA-Signature 算不出来")


def _build_pwa_headers(steamid: str) -> dict:
    ip = _get_public_ip()
    ts = int(time.time())
    return {
        'User-Agent': USER_AGENT,
        'Referer': 'https://client.wmpvp.com',
        'X-PWA-SteamId': steamid,
        'X-PWA-Signature': _x_pwa_signature(steamid, ts, ip),
        'PwaSteamId': steamid,
        'x-pwa-steamid': steamid,
        'pwasteamid': steamid,
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN',
    }


def get_matchids(url_getmatchid):
    response_getmatchid = requests.get(url_getmatchid, params=params, headers=headers)
    if response_getmatchid.status_code == 200:
        data = response_getmatchid.json()
        match_data = data.get('data', {})
        match_ids = [match['match'] for match in match_data]
        return match_ids
    else:
        print("Failed to retrieve data, status code:", response_getmatchid.status_code)


def get_demo_url(match_id, access_token, cup_id=0):
    # 新版服务端要求带 a/r/s/t + 排序参数,等价于 callWebApi_signature(GET) 的输出:
    #   data = sorted("k=v") join "&"
    #   sig  = swapData({"randnum":r,"ts":t,"data":data,"version":1})
    sorted_params = {
        'access_token': access_token,
        'cup_id': str(cup_id),
        'match_id': str(match_id),
    }
    data = '&'.join(f'{k}={v}' for k, v in sorted(sorted_params.items()))
    randnum = str(random.randint(100000, 999999))
    ts = str(int(time.time()))
    sig = _swap_data_sign(randnum, ts, data)
    return (
        f'https://pwaweblogin.wmpvp.com/csgo/demo/{match_id}_{cup_id}.dem'
        f'?a={PVP_WEB_API_APPID}&r={randnum}&s={sig}&t={ts}&{data}'
    )


def download_file(url, local_filename, steamid):
    os.makedirs(os.path.dirname(local_filename), exist_ok=True)
    # X-PWA-Signature 头必带,否则服务器返回 PvpException code:1033
    dl_headers = _build_pwa_headers(steamid)
    with requests.get(url, stream=True, headers=dl_headers) as r:
        r.raise_for_status()
        if r.status_code == 200 and 'application/octet-stream' in r.headers.get('Content-Type', ''):
            total_size = int(r.headers.get('content-length', 0))
            chunk_size = 8192
            downloaded_size = 0
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        done = int(50 * downloaded_size / total_size) if total_size else 0
                        print(f"\r[{'=' * done}{' ' * (50-done)}] {done * 2}%", end='')
        else:
            return None

    print("\nDownload completed!")
    return local_filename


def unzip_file(zip_path, demoPath):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(demoPath)


def download_and_extract(url, demoPath, steamid):
    if not url:
        print("URL is empty, skipping download and extraction.")
        return
    filename = url.split('/')[-1].split('?')[0]
    filename = os.path.join(demoPath, filename)
    if os.path.exists(filename):
        print(f"File {filename} already exists. Skipping download.")
        return

    filename = filename + '.zip'
    local_filename = download_file(url, filename, steamid)
    if local_filename is None:
        print("Demo Url out of date")
        return
    unzip_file(local_filename, demoPath)
    os.remove(local_filename)
    print(f"File downloaded and extracted to {demoPath}")


def main():
    global params, headers
    cf = _load_config()
    secs = [s for s in cf.sections() if s.lower() != "global"]

    for user in secs:
        userid = cf.get(user, "userid")
        access_token = cf.get(user, "access_token")

        params = {
            'access_token': access_token,
            'size': 20,
            'uid': userid
        }

        headers = {
            'Host': 'pwaweblogin.wmpvp.com',
            'x-pwa-steamid': userid,
            'pwasteamid': userid,
            'User-Agent': USER_AGENT,
        }

        match_ids = get_matchids(url_getmatchid)

        demo_urls = {}
        for match_id in match_ids:
            demo_url = get_demo_url(match_id, access_token)
            demo_urls[match_id] = demo_url

        for match_id, demo_url in demo_urls.items():
            print(f"Demo URL for match {match_id}: {demo_url}")

        for _, demo_url in demo_urls.items():
            download_and_extract(demo_url, cf.get(user, "demoPath"), userid)


if __name__ == "__main__":
    main()
