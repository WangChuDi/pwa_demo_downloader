import requests
import json
import zipfile
import os

import configparser

demoPath = './demo'  # 替换为实际demo解压路径
url_getmatchid = 'https://pwaweblogin.wmpvp.com/user-info/recent-ladder-score-list'


# 发送 GET 请求
def get_matchids(url_getmatchid):
    #response_getmatchid = requests.get(url_getmatchid)
    response_getmatchid = requests.get(url_getmatchid, params=params, headers=headers)
# 检查请求是否成功
    if response_getmatchid.status_code == 200:
    # 解析JSON数据
        data = response_getmatchid.json()
    # 提取match_data列表
        match_data = data.get('data', {})
    
    # 遍历match_data列表，提取每个match_id
        match_ids = [match['match'] for match in match_data]
        return match_ids

    else:
        print("Failed to retrieve data, status code:", response_getmatchid.status_code)


    

def get_demo_url(match_id):
    # 构造URL
    demo_url = f'https://pwaweblogin.wmpvp.com/csgo/demo/{match_id}_0.dem'
    return demo_url
        



def download_file(url, local_filename):
    # 发起GET请求，设置stream=True以流式下载文件
    
    with requests.get(url, stream=True) as r:
        r.raise_for_status()  # 确保请求成功
        if r.status_code == 200 and 'application/octet-stream' in r.headers.get('Content-Type', ''):  
            total_size = int(r.headers.get('content-length', 0))
            chunk_size = 8192  # 每次下载的块大小
            downloaded_size = 0  # 已下载的大小
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:  # 过滤掉保持连接的chunk
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        done = int(50 * downloaded_size / total_size)
                        print(f"\r[{'=' * done}{' ' * (50-done)}] {done * 2}%", end='')
        else :return None

    print("\nDownload completed!")
    return local_filename

def unzip_file(zip_path, demoPath):
    # 使用zipfile解压文件
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(demoPath)

def download_and_extract(url, demoPath):
    if not url:
        print("URL is empty, skipping download and extraction.")
        return
    
    # 从URL中提取文件名
    filename = url.split('/')[-1]
    # 下载文件
    local_filename = download_file(url, filename)
    # 解压文件
    if local_filename == None:
        print("Demo Url out of date")
        return
    unzip_file(local_filename, demoPath)
    # 删除ZIP文件
    os.remove(local_filename)
    print(f"File downloaded and extracted to {demoPath}")



cf = configparser.ConfigParser()
cf.read("config.ini")  # 读取配置文件，如果写文件的绝对路径，就可以不用os模块

secs = cf.sections()  # 获取文件中所有的section(一个配置文件中可以有多个配置，如数据库相关的配置，邮箱相关的配置，
                      #  每个section由[]包裹，即[section])，并以列表的形式返回

for user in secs:
    options = cf.options(user)
    userid=cf.get(user,"userid")
    access_token=cf.get(user,"access_token")

    params = {
        'access_token': access_token,
        'size': 10,
        'uid': userid
    }

    # 设置请求头
    headers = {
        'Host': 'pwaweblogin.wmpvp.com',
        'x-pwa-steamid': userid,
        'pwasteamid': userid,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) perfectworldarena/1.0.24120411 Chrome/80.0.3987.163 Electron/8.5.5 Safari/537.36'
    }    

    match_ids=get_matchids(url_getmatchid)

    # 循环遍历match_ids数组，并获取每个matchid的demo下载链接
    demo_urls = {}
    for match_id in match_ids:
        demo_url = get_demo_url(match_id)
        demo_urls[match_id] = demo_url

    # 打印所有demo的下载链接
    for match_id, demo_url in demo_urls.items():
        print(f"Demo URL for match {match_id}: {demo_url}")

    
    # 批量下载demo文件
    for _ , demo_url in demo_urls.items():
        download_and_extract(demo_url, demoPath)









