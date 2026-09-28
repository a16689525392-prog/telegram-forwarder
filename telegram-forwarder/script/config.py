import os

# ==================== 机器人配置（脚本版） ====================
# 直接在此文件中填写密钥，改完后重新运行 start_bot.sh / start_bot.bat
# ⚠️ 填入真实密钥后请勿提交到公开仓库

# Telegram API 凭证，从 https://my.telegram.org 获取
API_ID = 0                  # 数字，例如 12345678
API_HASH = ''               # 字符串，例如 '0123456789abcdef0123456789abcdef'

# 机器人 Token，从 @BotFather 获取
BOT_TOKEN = ''              # 例如 '123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# 代理（可选），不需要代理保持 None
# 格式：(类型, 主机, 端口)，类型为 'http' / 'socks5'，例如 ('http', '127.0.0.1', 7890)
PROXY = None

# Telethon 登录会话文件路径（不带 .session 后缀），默认为 script/session/message_forwarder_session.session
# 该文件为空时使用 BOT_TOKEN 登录；替换成已登录账号的会话文件即可使用该账号
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'session', 'message_forwarder_session')
