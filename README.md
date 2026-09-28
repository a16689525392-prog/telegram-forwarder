# Telegram 消息转发机器人 📬

把 Telegram 消息链接发给机器人，它就把这条消息（包括图片、视频和整组相册）取回来发给你。

## 📖 项目简介

这是一个用 Python 编写的 Telegram 机器人，用来快速获取频道和群组中的消息。把消息链接发给机器人，它会读取这条消息，连同同一相册里的全部图片、视频一起重新发送给你，并在末尾附上原始消息链接，方便回溯来源。

除了逐条获取，它还能从频道历史中随机抽取消息、按消息 ID 范围批量获取，并支持随时停止任务、一键清理机器人发出的消息，适合用来浏览、回顾和整理频道内容。

项目同时使用 Telegram 的两套接口：

- **Bot API**（python-telegram-bot）：接收命令、回复提示信息
- **MTProto 客户端 API**（Telethon）：读取频道消息、发送媒体、删除消息

Telethon 默认以机器人身份（`BOT_TOKEN`）登录。也可以把登录会话文件换成个人账号的会话，改用该账号的权限读取消息（此时消息也会由该账号发出）。

## ✨ 主要功能

| 功能 | 用法 | 说明 |
| --- | --- | --- |
| 🔗 链接获取 | 直接发送消息链接 | 支持公开频道 `https://t.me/频道名/消息ID` 和私有频道 `https://t.me/c/频道ID/消息ID` |
| 📷 相册完整发送 | 自动 | 同一相册（媒体组）里的图片、视频一次全部发出，并附上原始消息链接 |
| 🎲 随机获取 | `/random <链接> [数量]` | 在 1 到链接消息 ID 之间随机抽取，默认 10 条，自动跳过重复和已删除的消息 |
| 📏 范围获取 | `/range <链接> <起始ID> <结束ID>`<br>`/range <链接> <数量>` | 按 ID 区间批量获取，或从链接那条往前取指定条数，完成后汇报成功和失败条数 |
| ⏹️ 停止任务 | `/stop` | 随时中断正在进行的批量发送 |
| 🧹 一键清理 | `/clear` | 删除机器人最近发出的消息和你的指令消息 |
| 👥 群聊使用 | 在群里 @机器人 或回复机器人 | 命令无需 @；取回的内容会私聊发给发起人 |

> 💡 `/random` 的链接用频道最新一条消息，随机范围就能覆盖整个频道。

## 📦 两个版本

| 版本 | 目录 | 适用场景 |
| --- | --- | --- |
| Docker 版 | [`telegram-forwarder/docker/`](telegram-forwarder/docker/) | 部署到服务器长期运行，异常退出或服务器重启后自动拉起 |
| 脚本版 | [`telegram-forwarder/script/`](telegram-forwarder/script/) | 在 Windows / macOS / Linux 本机直接运行，首次启动自动创建虚拟环境并安装依赖 |

两个版本的机器人代码相同，密钥都直接写在各自目录的 `config.py` 中。

## 🚀 快速开始

1. 在 [@BotFather](https://t.me/BotFather) 创建机器人获取 `BOT_TOKEN`，在 [my.telegram.org](https://my.telegram.org) 获取 `API_ID` 和 `API_HASH`
2. 把它们填进所用版本的 `config.py`
3. 启动机器人：
   - Docker 版：`cd telegram-forwarder/docker && docker compose up -d --build`
   - 脚本版：Windows 双击 `telegram-forwarder/script/start_bot.bat`，macOS / Linux 运行 `./telegram-forwarder/script/start_bot.sh`
4. 在 Telegram 里私聊机器人发送 `/start`，然后发送消息链接即可

配置项、登录会话文件的替换方法和常见问题见 [详细使用说明](telegram-forwarder/README.md)。

## ⚠️ 注意事项

- 只能获取机器人（或所登录账号）有权访问的频道和群组，私有频道、群组需要先把机器人加进去
- 在群里使用前，需要先私聊机器人发送过 `/start`，否则机器人无法把内容私聊发给你
- `/clear` 只能删除 48 小时内的消息；发送记录保存在内存中，重启机器人后清空
- `config.py` 和会话文件等同于登录凭证，请妥善保管，不要公开分享
- 请遵守 Telegram 使用条款，仅获取你有权访问的内容

## 🛠️ 技术栈

Python 3.9+ · python-telegram-bot · Telethon · python-socks · Docker

## 📁 目录结构

```text
telegram-forwarder/
├── docker/      Docker 版（Dockerfile、docker-compose.yml、config.py、session/）
├── script/      脚本版（start_bot.sh、start_bot.bat、config.py、session/）
├── README.md    详细使用说明
└── LICENSE      MIT 许可证
```

## 📄 许可证与致谢

本项目基于开源项目 [telegram-msg-forwarder](https://github.com/zhaochengcube/telegram-msg-forwarder) 修改，采用 [MIT 许可证](telegram-forwarder/LICENSE)。
