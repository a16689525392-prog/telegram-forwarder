# ==================== 机器人配置（Docker 版） ====================
# 直接在此文件中填写密钥，改完后重新构建镜像：docker compose up -d --build
# ⚠️ 填入真实密钥后请勿提交到公开仓库

# Telegram API 凭证，从 https://my.telegram.org 获取
API_ID = 0                  # 数字，例如 12345678
API_HASH = ''               # 字符串，例如 '0123456789abcdef0123456789abcdef'

# 机器人 Token，从 @BotFather 获取
BOT_TOKEN = ''              # 例如 '123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# 代理（可选），不需要代理保持 None
# 格式：(类型, 主机, 端口)，类型为 'http' / 'socks5'
# 容器内访问宿主机代理可用 host.docker.internal，例如 ('http', 'host.docker.internal', 7890)
PROXY = None

# Telethon 登录会话文件路径（容器内路径，不带 .session 后缀）
# 对应宿主机 docker/session/message_forwarder_session.session
# 该文件为空时使用 BOT_TOKEN 登录；替换成已登录账号的会话文件即可使用该账号
SESSION_FILE = '/app/session/message_forwarder_session'
