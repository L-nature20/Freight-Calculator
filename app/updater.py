"""自动更新：检查 GitHub Releases → 下载新版 exe → 替换"""
import os
import sys
import json
import time
import threading
import requests

from app.version import __version__

# GitHub 仓库地址（发版前需要修改）
GITHUB_REPO = 'L-nature20/Freight-Calculator'
GITHUB_API = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'

# 国内代理（加速下载，免费无需注册）
# 如果代理不稳定，可以注释掉这行，直接用 GitHub 原始地址
GITHUB_PROXY = 'https://ghproxy.net/'

# 缓存检查结果，避免重复请求
_update_cache = {'checked': False, 'has_update': False,
                 'version': None, 'url': None, 'raw_url': None, 'notes': None}


def reset_check_cache():
    """重置缓存，下次 check_update() 会重新请求 GitHub。"""
    _update_cache['checked'] = False


def check_update():
    """检查 GitHub Releases 是否有新版本。
    优先 GitHub 原始 API，失败再走代理。
    返回 (has_update, remote_version, download_url, release_notes)
    """
    if _update_cache['checked']:
        return (_update_cache['has_update'], _update_cache['version'],
                _update_cache['url'], _update_cache['raw_url'], _update_cache['notes'])

    # 优先 GitHub 原始 API，失败再走代理
    api_urls = [GITHUB_API]
    if GITHUB_PROXY:
        api_urls.append(GITHUB_PROXY + GITHUB_API)

    max_retries = 3

    for api_url in api_urls:
        for attempt in range(max_retries):
            try:
                resp = requests.get(api_url, timeout=15)
                if resp.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    break  # 尝试下一个 URL

                data = resp.json()
                remote_ver = data.get('tag_name', '').lstrip('v')
                if not remote_ver or remote_ver == __version__:
                    _update_cache['checked'] = True
                    return False, None, None, None, None

                # 找到 exe 下载链接
                download_url = None
                raw_url = None
                for asset in data.get('assets', []):
                    if asset['name'].endswith('.exe'):
                        raw_url = asset['browser_download_url']
                        # 使用代理加速（如果配置了）
                        download_url = GITHUB_PROXY + raw_url if GITHUB_PROXY else raw_url
                        break

                if download_url:
                    _update_cache.update({
                        'checked': True,
                        'has_update': True,
                        'version': remote_ver,
                        'url': download_url,
                        'raw_url': raw_url,
                        'notes': data.get('body', ''),
                    })
                    return True, remote_ver, download_url, raw_url, data.get('body', '')

                _update_cache['checked'] = True
                return False, None, None, None, None

            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                break  # 尝试下一个 URL

    _update_cache['checked'] = True
    return False, None, None, None, None


def check_update_async(callback=None):
    """后台线程检查更新，完成后调用 callback(has_update, version, url, raw_url, notes)"""
    def _worker():
        result = check_update()
        if callback:
            callback(*result)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def download_update(download_url, progress_callback=None):
    """下载新版 exe。
    仅在 PyInstaller 打包模式下可用。
    下载完成后返回新文件路径（.new 后缀），调用方负责替换。
    """
    if not getattr(sys, 'frozen', False):
        return None, '开发模式不支持自动更新'

    current_exe = sys.executable
    temp_path = current_exe + '.new'

    try:
        resp = requests.get(download_url, stream=True, timeout=30)
        resp.raise_for_status()
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0

        with open(temp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    progress_callback(downloaded, total)

        return temp_path, None
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return None, str(e)
