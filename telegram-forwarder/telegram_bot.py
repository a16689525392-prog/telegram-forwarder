import os
import re
import logging
import random
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient, events

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)
logger = logging.getLogger(__name__)

# Telegram API 凭证
# 从 https://my.telegram.org 获取
API_ID = os.environ.get('API_ID', 'your_api_id')
API_HASH = os.environ.get('API_HASH', 'your_api_hash')
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token')

# 代理配置（如果需要）
# 设置为 None 或留空则不使用代理
PROXY_TYPE = os.environ.get('PROXY_TYPE', '')
PROXY_HOST = os.environ.get('PROXY_HOST', '')
PROXY_PORT = os.environ.get('PROXY_PORT', '')

proxy = None
if PROXY_TYPE and PROXY_HOST and PROXY_PORT:
    proxy = (PROXY_TYPE, PROXY_HOST, int(PROXY_PORT))

# 创建 Telethon 客户端
client = TelegramClient('/app/session/message_forwarder_session', API_ID, API_HASH, proxy=proxy)

# 消息链接正则表达式模式
# 匹配格式：https://t.me/channel_name/message_id 或 https://t.me/c/channel_id/message_id
MESSAGE_LINK_PATTERN = r'https?://t\.me/(?:c/(\d+)|([^/]+))/(\d+)'

# 存储每个用户最近发送的消息ID，用于批量删除
user_sent_messages = {}
# 存储用户发送的指令消息ID
user_command_messages = {}
# 存储用户停止任务的请求标志
user_stop_requested = {}

def is_stop_requested(user_id):
    """检查用户是否请求停止"""
    return user_stop_requested.get(user_id, False)

def set_stop_requested(user_id, value=True):
    """设置用户停止请求标志"""
    user_stop_requested[user_id] = value

async def track_bot_message(user_id, message):
    """跟踪机器人发送的消息，用于后续删除"""
    if user_id not in user_sent_messages:
        user_sent_messages[user_id] = []
    user_sent_messages[user_id].append(message.message_id)
    return message

async def track_user_message(update):
    """跟踪用户发送的消息，用于后续删除"""
    user_id = update.effective_user.id
    if user_id not in user_command_messages:
        user_command_messages[user_id] = []
    user_command_messages[user_id].append(update.message.message_id)

async def should_respond_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """检查在群聊中是否应该响应消息"""
    # 私聊中总是响应
    if update.message.chat.type == 'private':
        return True
    
    # 群聊中检查是否@了机器人
    message_text = update.message.text or ""
    bot_username = context.bot.username
    
    # 检查消息中是否包含@机器人
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'mention':
                mention = message_text[entity.offset:entity.offset + entity.length]
                if mention == f"@{bot_username}":
                    return True
    
    # 也检查回复消息是否是回复给机器人的
    if update.message.reply_to_message:
        if update.message.reply_to_message.from_user.username == bot_username:
            return True
    
    return False

def parse_link(link):
    """解析消息链接，返回entity和message_id"""
    matches = re.search(MESSAGE_LINK_PATTERN, link)
    if not matches:
        return None, None
    
    channel_id, channel_username, message_id = matches.groups()
    message_id = int(message_id)
    
    if channel_id:  # 私有频道
        channel_id = int(channel_id)
        entity = -1000000000000 - channel_id
    else:  # 公开频道
        entity = channel_username
    
    return entity, message_id

def build_link(entity, message_id):
    """构建消息链接"""
    if isinstance(entity, str):  # 公开频道
        return f"https://t.me/{entity}/{message_id}"
    else:  # 私有频道
        original_channel_id = str(abs(entity + 1000000000000))
        return f"https://t.me/c/{original_channel_id}/{message_id}"

async def send_message_to_user(entity, message_id, user_id, add_link=True,
                                skip_group=None, skip_messages=None):
    """发送单个消息给用户
    返回 dict: {success, grouped_id, message_ids}
    skip_group: 已发送的grouped_id集合，属于这些组的消息将被跳过
    skip_messages: 已发送的消息ID集合，这些消息将被跳过
    """
    try:
        if is_stop_requested(user_id):
            return {"success": "stopped", "grouped_id": None, "message_ids": []}

        if skip_group is None:
            skip_group = set()
        if skip_messages is None:
            skip_messages = set()

        # 获取消息组, 前后10条
        message_ids = list(range(message_id - 10, message_id + 10))
        
        if is_stop_requested(user_id):
            return {"success": "stopped", "grouped_id": None, "message_ids": []}
        
        messages = await client.get_messages(entity, ids=message_ids)

        if is_stop_requested(user_id):
            return {"success": "stopped", "grouped_id": None, "message_ids": []}

        # 找到目标消息
        target_msg = next((msg for msg in messages if msg and msg.id == message_id), None)
        if not target_msg:
            return {"success": False, "grouped_id": None, "message_ids": []}

        # 检查是否属于已发送的媒体组
        if target_msg.grouped_id and target_msg.grouped_id in skip_group:
            return {"success": "skipped", "grouped_id": target_msg.grouped_id, "message_ids": []}

        # 检查消息ID是否已发送
        if message_id in skip_messages:
            return {"success": "skipped", "grouped_id": None, "message_ids": [message_id]}

        # 获取同组消息
        if target_msg.grouped_id:
            valid_messages = [msg for msg in messages
                              if msg and msg.grouped_id == target_msg.grouped_id]
        else:
            valid_messages = [target_msg]

        valid_messages.sort(key=lambda x: x.id)
        sent_message_ids = []
        sent_source_ids = [msg.id for msg in valid_messages]
        sent_grouped_id = target_msg.grouped_id

        # 收集媒体文件
        media_list = [msg.media for msg in valid_messages if msg.media]

        # 准备文本内容
        text_content = ""
        for msg in valid_messages:
            if msg.text:
                text_content = msg.text
                break

        if add_link:
            text_content += f"\n\n🔗 原始消息: {build_link(entity, message_id)}"

        if is_stop_requested(user_id):
            return {"success": "stopped", "grouped_id": None, "message_ids": []}

        if media_list:
            caption = text_content[:1024] if len(text_content) > 1024 else text_content

            if is_stop_requested(user_id):
                return {"success": "stopped", "grouped_id": None, "message_ids": []}

            sent_messages = await client.send_file(
                user_id,
                file=media_list,
                caption=caption
            )

            if isinstance(sent_messages, list):
                sent_message_ids.extend([msg.id for msg in sent_messages])
            else:
                sent_message_ids.append(sent_messages.id)

            if len(text_content) > 1024:
                text_msg = await client.send_message(user_id, f"完整内容：\n{text_content}")
                sent_message_ids.append(text_msg.id)

        elif text_content:
            text_msg = await client.send_message(user_id, text_content)
            sent_message_ids.append(text_msg.id)

        # 记录发送的消息
        if user_id not in user_sent_messages:
            user_sent_messages[user_id] = []
        user_sent_messages[user_id].extend(sent_message_ids)

        return {
            "success": True,
            "grouped_id": sent_grouped_id,
            "message_ids": sent_source_ids,
        }

    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        return {"success": False, "grouped_id": None, "message_ids": []}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """当用户发送 /start 命令时的处理函数"""
    await track_user_message(update)
    user = update.effective_user
    message = await update.message.reply_text(f'你好，{user.first_name}！\n'
                                   f'请发送 Telegram 消息链接，我会将消息转发给你。\n\n'
                                   f'💡 在群聊中使用时，请@我或回复我的消息。')
    await track_bot_message(user.id, message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """当用户发送 /help 命令时的处理函数"""
    await track_user_message(update)
    help_text = (
        '📖 *Telegram 消息转发机器人 - 使用教程*\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━\n'
        '🔗 *转发单条消息*\n'
        '直接发送消息链接给机器人，即可获取并转发该条消息。\n'
        '支持的链接格式：\n'
        '• `频道名/消息ID`\n'
        '• `频道ID/消息ID`\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━\n'
        '🎲 *随机转发消息*\n'
        '从指定链接所在的频道随机转发历史消息。\n'
        '• /random <链接> [数量]\n'
        '示例：\n'
        '  /random 频道链接             随机10条\n'
        '  /random 频道链接 5           随机5条\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━\n'
        '📏 *范围转发消息*\n'
        '按指定ID范围批量转发消息，支持两种模式：\n\n'
        '1️⃣ 指定起止ID范围：\n'
        '   /range <链接> <起始ID> <结束ID>\n'
        '   示例：/range 频道链接 100 120\n\n'
        '2️⃣ 指定转发数量（从链接位置往前）：\n'
        '   /range <链接> <数量>\n'
        '   示例：/range 频道链接 20\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━\n'
        '⏹️ *停止任务*\n'
        '停止当前正在进行的发送任务。\n'
        '• /stop\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━\n'
        '🧹 *清理消息*\n'
        '删除机器人最近发送给你的所有消息。\n'
        '• /clear\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━\n'
        '📌 *群聊使用规则*\n'
        '• 在群聊中需要 @我 才会响应\n'
        '• 回复我的消息也能触发\n'
        '• 命令始终有效，无需 @我\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━\n'
        '⚠️ *注意事项*\n'
        '• 只能转发你有权限访问的频道/群组\n'
        '• 机器人需为目标频道的成员/管理员\n'
        '• /clear 只能删除48小时内发送的消息\n'
    )

    message = await update.message.reply_text(help_text, parse_mode='Markdown')
    await track_bot_message(update.effective_user.id, message)

async def process_message_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户发送的消息链接"""
    # 检查是否应该响应（群聊中需要@机器人）
    if not await should_respond_in_group(update, context):
        return
    
    await track_user_message(update)
    entity, message_id = parse_link(update.message.text)
    
    if not entity:
        message = await update.message.reply_text('请发送有效的 Telegram 消息链接。')
        await track_bot_message(update.effective_user.id, message)
        return
    
    success = await send_message_to_user(entity, message_id, update.effective_user.id)

    if not success or not success.get("success"):
        message = await update.message.reply_text('无法获取该消息，请检查链接或权限。')
        await track_bot_message(update.effective_user.id, message)

async def random_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """根据提供的消息链接随机发送指定数量的消息"""
    await track_user_message(update)
    user_id = update.effective_user.id
    set_stop_requested(user_id, False)
    try:
        args = context.args if hasattr(context, 'args') else []
        if not args:
            message = await update.message.reply_text('请提供消息链接。\n用法: /random <链接> [数量]\n示例: /random 频道链接 10')
            await track_bot_message(user_id, message)
            return
        
        entity, max_message_id = parse_link(args[0])
        
        if not entity:
            message = await update.message.reply_text('请发送有效的 Telegram 消息链接。')
            await track_bot_message(update.effective_user.id, message)
            return
        
        # 解析发送数量，默认为10条
        send_count = 10
        if len(args) > 1:
            try:
                send_count = int(args[1])
                if send_count <= 0:
                    message = await update.message.reply_text('发送数量必须大于0。')
                    await track_bot_message(update.effective_user.id, message)
                    return
            except ValueError:
                message = await update.message.reply_text('请输入有效的数字作为发送数量。')
                await track_bot_message(update.effective_user.id, message)
                return
        
        # 清空该用户之前的消息记录，为新的批次做准备
        user_sent_messages[update.effective_user.id] = []
        user_command_messages[update.effective_user.id] = []
        
        random_sent_count = 0
        random_sent_groups = set()
        random_sent_msgs = set()
        attempts = 0
        max_attempts = send_count * 5

        while random_sent_count < send_count and attempts < max_attempts:
            if is_stop_requested(user_id):
                message = await update.message.reply_text('⏹️ 已停止发送任务。')
                await track_bot_message(user_id, message)
                return
            
            rand_id = random.randint(1, max_message_id)
            attempts += 1

            result = await send_message_to_user(
                entity, rand_id, update.effective_user.id,
                skip_group=random_sent_groups,
                skip_messages=random_sent_msgs,
            )
            
            status = result.get("success")
            if status is True:
                random_sent_count += 1
                if result.get("grouped_id"):
                    random_sent_groups.add(result["grouped_id"])
                for mid in result.get("message_ids", []):
                    random_sent_msgs.add(mid)
            elif status == "stopped":
                message = await update.message.reply_text('⏹️ 已停止发送任务。')
                await track_bot_message(user_id, message)
                return
            
            await asyncio.sleep(0.01)

        if random_sent_count > 0:
            message = await update.message.reply_text(f'已成功发送 {random_sent_count} 条随机消息！\n使用 /clear 可以删除这些消息。')
            await track_bot_message(update.effective_user.id, message)
        else:
            message = await update.message.reply_text('未能找到有效消息，请检查链接或稍后重试。')
            await track_bot_message(update.effective_user.id, message)

    except Exception as e:
        logger.error(f'随机消息处理错误: {e}')
        message = await update.message.reply_text(f'获取随机消息时出错: {str(e)}')
        await track_bot_message(update.effective_user.id, message)

async def range_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """根据提供的链接和ID范围转发消息"""
    await track_user_message(update)
    user_id = update.effective_user.id
    set_stop_requested(user_id, False)
    try:
        args = context.args if hasattr(context, 'args') else []
        if len(args) < 2:
            message = await update.message.reply_text(
                '📌 指定起止ID范围：\n'
                '/range <链接> <起始ID> <结束ID>\n'
                '示例: /range 频道链接 100 120\n\n'
                '📌 指定转发数量（从链接位置往前）：\n'
                '/range <链接> <数量>\n'
                '示例: /range 频道链接 20'
            )
            await track_bot_message(user_id, message)
            return

        entity, reference_id = parse_link(args[0])
        if not entity:
            message = await update.message.reply_text('请发送有效的 Telegram 消息链接。')
            await track_bot_message(update.effective_user.id, message)
            return

        # 解析范围参数
        if len(args) == 2:
            # 单数量模式: /range <链接> <数量>
            try:
                count = int(args[1])
                if count <= 0:
                    message = await update.message.reply_text('数量必须大于0。')
                    await track_bot_message(update.effective_user.id, message)
                    return
            except ValueError:
                message = await update.message.reply_text('请输入有效的数字。')
                await track_bot_message(update.effective_user.id, message)
                return

            # 从参考ID往前取count条消息
            end_id = reference_id
            start_id = max(1, reference_id - count + 1)
            message = await update.message.reply_text(f'开始转发 ID {start_id} 到 {end_id} 的消息...')
        else:
            # 范围模式: /range <链接> <起始ID> <结束ID>
            try:
                start_id = int(args[1])
                end_id = int(args[2])
            except ValueError:
                message = await update.message.reply_text('请输入有效的数字作为ID范围。')
                await track_bot_message(update.effective_user.id, message)
                return

            if start_id <= 0 or end_id <= 0:
                message = await update.message.reply_text('ID必须大于0。')
                await track_bot_message(update.effective_user.id, message)
                return
            if start_id > end_id:
                start_id, end_id = end_id, start_id

            message = await update.message.reply_text(f'开始转发 ID {start_id} 到 {end_id} 的消息...')

        await track_bot_message(update.effective_user.id, message)

        # 清空该用户之前的消息记录
        user_sent_messages[update.effective_user.id] = []
        user_command_messages[update.effective_user.id] = []

        # 批量转发消息（带媒体组去重）
        sent_count = 0
        failed_count = 0
        range_sent_groups = set()
        range_sent_msgs = set()
        message_ids = list(range(start_id, end_id + 1))

        for msg_id in message_ids:
            if is_stop_requested(user_id):
                message = await update.message.reply_text('⏹️ 已停止发送任务。')
                await track_bot_message(user_id, message)
                return
            
            result = await send_message_to_user(
                entity, msg_id, update.effective_user.id,
                skip_group=range_sent_groups,
                skip_messages=range_sent_msgs,
            )

            status = result.get("success")
            if status is True:
                sent_count += 1
                if result.get("grouped_id"):
                    range_sent_groups.add(result["grouped_id"])
                for mid in result.get("message_ids", []):
                    range_sent_msgs.add(mid)
            elif status is False:
                failed_count += 1
            elif status == "stopped":
                message = await update.message.reply_text('⏹️ 已停止发送任务。')
                await track_bot_message(user_id, message)
                return
            
            await asyncio.sleep(0.01)

        result_msg = f'✅ 已成功转发 {sent_count} 条消息'
        if failed_count > 0:
            result_msg += f'（{failed_count} 条失败）'
        result_msg += '\n使用 /clear 可以删除这些消息。'

        final_message = await update.message.reply_text(result_msg)
        await track_bot_message(update.effective_user.id, final_message)

    except Exception as e:
        logger.error(f'范围消息处理错误: {e}')
        message = await update.message.reply_text(f'获取范围消息时出错: {str(e)}')
        await track_bot_message(update.effective_user.id, message)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """停止当前发送任务"""
    await track_user_message(update)
    user_id = update.effective_user.id
    set_stop_requested(user_id, True)
    message = await update.message.reply_text('⏹️ 已请求停止，正在停止任务...')
    await track_bot_message(user_id, message)

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """删除最近发送给用户的消息以及用户的指令消息"""
    try:
        user_id = update.effective_user.id
        
        # 获取要删除的消息列表
        bot_messages = user_sent_messages.get(user_id, [])
        user_messages = user_command_messages.get(user_id, [])
        all_messages = bot_messages + user_messages
        
        if not all_messages:
            message = await update.message.reply_text('没有可删除的消息。')
            await track_bot_message(user_id, message)
            return
        
        # 添加当前清理命令消息到删除列表
        all_messages.append(update.message.message_id)
        
        deleted_count = 0
        status_message = await update.message.reply_text(f'正在删除 {len(all_messages)} 条消息...')
        
        # 批量删除消息
        for msg_id in all_messages:
            try:
                await client.delete_messages(user_id, msg_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"删除消息 {msg_id} 失败: {e}")
        
        # 清空记录
        user_sent_messages[user_id] = []
        user_command_messages[user_id] = []
        
        # 删除状态消息
        try:
            await client.delete_messages(user_id, status_message.message_id)
        except:
            pass
        
        if deleted_count > 0:
            result_message = await update.message.reply_text(f'已成功删除 {deleted_count} 条消息！')
            # 延迟删除结果消息
            import asyncio
            await asyncio.sleep(3)
            try:
                await client.delete_messages(user_id, result_message.message_id)
            except:
                pass
        else:
            message = await update.message.reply_text('删除失败，可能消息已被删除或超过48小时。')
            await track_bot_message(user_id, message)
    
    except Exception as e:
        logger.error(f'删除消息时出错: {e}')
        message = await update.message.reply_text(f'删除消息时出错: {str(e)}')
        await track_bot_message(update.effective_user.id, message)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理非链接消息"""
    # 检查是否应该响应（群聊中需要@机器人）
    if not await should_respond_in_group(update, context):
        return
    
    await track_user_message(update)
    message = await update.message.reply_text('请发送 Telegram 消息链接。如需帮助，请使用 /help 命令。')
    await track_bot_message(update.effective_user.id, message)

async def post_init(application: Application) -> None:
    """启动前设置机器人命令菜单"""
    commands = [
        BotCommand("start", "启动机器人"),
        BotCommand("help", "查看完整使用教程"),
        BotCommand("random", "随机转发消息: /random <链接> [数量]"),
        BotCommand("range", "范围转发消息: /range <链接> <起始ID> <结束ID>"),
        BotCommand("stop", "停止当前发送任务"),
        BotCommand("clear", "清理机器人发送的消息"),
    ]
    await application.bot.set_my_commands(commands)

def main() -> None:
    # 创建应用程序，启用并发更新处理
    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).post_init(post_init).build()

    # 添加命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_messages))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("random", random_message))
    application.add_handler(CommandHandler("range", range_message))
    
    # 添加消息处理器，处理消息链接
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(MESSAGE_LINK_PATTERN) & ~filters.COMMAND, 
        process_message_link
    ))
    
    # 处理其他消息
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # 启动 Telethon 客户端
    client.start(bot_token=BOT_TOKEN)
    print("机器人已启动")
    
    # 运行机器人直到按下 Ctrl-C
    application.run_polling()
    
    # 关闭 Telethon 客户端
    client.disconnect()

if __name__ == '__main__':
    main()