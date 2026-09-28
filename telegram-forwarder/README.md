# Telegram消息转发机器人 📬

一个功能强大的Telegram机器人，能够转发指定链接的消息，支持随机消息获取和批量消息管理。

## ✨ 功能特性

- 🔗 **消息链接解析**: 支持解析公开频道和私有频道的消息链接
- 📨 **智能转发**: 自动转发消息内容，包括文本、图片、视频等媒体文件
- 🎲 **随机消息**: 根据指定链接随机获取指定数量的历史消息
- 🧹 **批量清理**: 一键删除机器人发送的所有消息
- 📷 **媒体组支持**: 完整转发媒体组消息
- 🔒 **突破转发限制**: 支持转发被限制的频道消息

## 🛠️ 技术栈

- **Python 3.9+**
- **python-telegram-bot**: 处理机器人API
- **Telethon**: 访问Telegram客户端API
- **python-socks**: 支持代理


## 📁 目录结构

项目提供两个版本，代码相同，只是运行方式和会话文件路径不同，按需选择其一：

```text
telegram-forwarder/
├── docker/                    # Docker 专用版
│   ├── config.py              # ← 在这里填写密钥
│   ├── telegram_bot.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── session/
│       └── message_forwarder_session.session   # 登录会话文件（默认为空）
└── script/                    # 直接运行的脚本版
    ├── config.py              # ← 在这里填写密钥
    ├── telegram_bot.py
    ├── start_bot.sh           # Mac/Linux 启动脚本
    ├── start_bot.bat          # Windows 启动脚本
    ├── requirements.txt
    └── session/
        └── message_forwarder_session.session   # 登录会话文件（默认为空）
```

> 修改机器人功能时，`docker/telegram_bot.py` 和 `script/telegram_bot.py` 需要同步修改。

## 🚀 快速开始

### 1. 获取API凭证

#### 获取Bot Token:
1. 在Telegram中找到 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建新机器人
3. 按提示设置机器人名称和用户名
4. 获取Bot Token

#### 获取API ID和API Hash:
1. 访问 [https://my.telegram.org](https://my.telegram.org)
2. 登录你的Telegram账号
3. 创建新应用获取API ID和API Hash

### 2. 填写配置

编辑所用版本目录下的 `config.py`，把密钥直接写进去：

```python
API_ID = 12345678                      # 数字
API_HASH = '0123456789abcdef...'       # 字符串
BOT_TOKEN = '123456789:AAxxxxxxxx'     # 字符串

# 代理（可选），不需要代理保持 None
PROXY = ('http', '127.0.0.1', 7890)
```

未填写 `API_ID` / `API_HASH` / `BOT_TOKEN` 时，程序启动会提示缺少哪一项并退出。

> ⚠️ 如果仓库是公开的，填入真实密钥后不要提交 `config.py`，或者先把仓库设为私有。

### 3. 登录会话文件

`session/message_forwarder_session.session` 是 Telethon 的登录会话文件，默认为空：

- **文件为空**：启动时自动使用 `BOT_TOKEN` 登录，并把会话写入该文件
- **替换为已登录账号的会话文件**：启动时直接使用该账号，不再用 `BOT_TOKEN` 登录

替换时保持文件名不变（或同步修改 `config.py` 中的 `SESSION_FILE`），然后重启机器人即可。

> ⚠️ 会话文件等同于账号登录凭证。为防止误提交真实会话文件，建议在仓库中执行一次：
> ```bash
> git update-index --skip-worktree docker/session/message_forwarder_session.session script/session/message_forwarder_session.session
> ```

### 4. 运行机器人

#### 方式一：Docker 版

```bash
cd docker
docker compose up -d --build     # 修改 config.py 后需要重新执行
docker compose logs -f           # 查看日志
```

`docker/session/` 会挂载到容器内的 `/app/session/`，替换会话文件后执行 `docker compose restart` 即可生效。

#### 方式二：脚本版

需要先安装 Python 3.9+。首次运行会自动创建虚拟环境 `venv` 并安装依赖。

- Windows: 双击 `script/start_bot.bat`
- Mac/Linux: `./script/start_bot.sh`

也可以手动运行：

```bash
cd script
pip install -r requirements.txt
python3 telegram_bot.py
```

### 5. 机器人命令菜单

机器人启动时会自动设置命令菜单，无需再到 @BotFather 手动设置。

## 📖 使用说明

### 支持的命令

| 命令        | 描述                 | 示例                                    |
| --------- | ------------------ | ------------------------------------- |
| `/start`  | 启动机器人并显示欢迎信息       | `/start`                              |
| `/help`   | 显示帮助信息和命令列表        | `/help`                               |
| `/random` | 随机发送指定数量的消息(默认10条) | `/random https://t.me/channel/123 20` |
| `/range`  | 按ID范围或数量批量转发消息     | `/range https://t.me/channel/123 100 120` |
| `/stop`   | 停止当前正在进行的发送任务      | `/stop`                               |
| `/clear`  | 删除机器人最近发送的所有消息     | `/clear`                              |

### 支持的链接格式

- **公开频道/群组**: `https://t.me/channel_name/message_id`
- **私有频道/群组**: `https://t.me/c/channel_id/message_id`

### 使用场景

1. **发送链接**: 直接发送Telegram消息链接
2. **随机消息**: 使用 `/random` 命令获取指定链接中随机消息
3. **清理消息**: 使用 `/clear` 命令删除发送的消息


## ⚠️ 注意事项

1. **隐私保护**: 请妥善保管你的API凭证，不要在公开代码中暴露
2. **使用限制**: 遵守Telegram的使用条款和API限制
3. **网络环境**: 某些地区可能需要代理才能正常使用
4. **消息权限**: 只能转发你有权限访问的消息
5. **删除限制**: 只能删除48小时内发送的消息
6. 公开/私有群组以及私有频道需要将机器人添加为管理员成员才能正常使用

## 🐛 故障排除

### 常见问题

**Q: 机器人无法获取消息**
A: 检查消息链接是否正确，确认你有权限访问该频道

**Q: 代理连接失败**
A: 检查代理设置是否正确，确认代理服务器可用

**Q: API请求失败**
A: 检查API凭证是否正确，网络连接是否稳定

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

感谢以下开源项目：
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Telethon](https://github.com/LonamiWebs/Telethon)

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！