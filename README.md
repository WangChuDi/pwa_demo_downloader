# PWA Demo Downloader

完美对战平台 (Perfect World Arena) CSGO demo 自动下载工具，支持多用户。
Automatically downloads CSGO demos from the Perfect World Arena platform.

> 维护提示：后续请优先使用新项目 [CS-Demo-Downloader](https://github.com/WangChuDi/CS-Demo-Downloader)，当前项目之后可能不再维护。
>
> Maintenance notice: please prefer the new project [CS-Demo-Downloader](https://github.com/WangChuDi/CS-Demo-Downloader). This project may no longer be maintained in the future.
>
> 侵权联系：如本项目存在侵权问题，请通过 GitHub issue 或邮件 `wangchudi666@gmail.com` 联系。
>
> Infringement contact: if this project infringes your rights, please open a GitHub issue or email `wangchudi666@gmail.com`.

## 一次性准备 / Setup

1. **主环境依赖**：
   ```
   pip install requests cryptography
   ```
2. **配置**：复制 `config.ini.example` 为 `config.ini`，按需填写。每个用户一个 `[section]`：
   ```ini
   [user1]
   userid=76561198159976336
   access_token=xxxxxxxx...
   demoPath=./demos/user1
   ```

## 运行 / Run

```
python main.py
```

程序会拉取该账号最近 20 场 demo URL，跳过已下载的，新文件下载完后自动解压。服务器对已过期/不存在的 demo 返回 JSON 错误而非 302，会被打印 `Demo Url out of date`。

## 获取 userid 与 access_token

- **userid**：Steam64 id，例如 `76561198159976336`。Steam 个人资料 URL 末尾即是；若设了自定义 URL，可在 https://steamid.io/lookup/ 反查。
- **access_token**：浏览器登录 https://partner.wmpvp.com/#/login 后从 cookie 里取。

![cookie](cookie.png)

## 查找其他玩家的 Steam64 id

普通玩家：游戏内或 demo 查看页点击头像 → 查看个人资料。
职业选手：liquipedia.net 等站点。
