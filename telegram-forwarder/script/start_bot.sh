#!/bin/bash

# 切换到脚本所在目录，保证从任意位置运行都能找到 config.py 和 session/
cd "$(dirname "$0")" || exit 1

echo "正在启动 Telegram Bot..."
echo

# 检查Python命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "错误: 未找到Python"
    exit 1
fi

# 检查虚拟环境是否存在并激活，不存在则自动创建并安装依赖
if [ -d "venv" ]; then
    echo "激活虚拟环境 (venv)..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "激活虚拟环境 (.venv)..."
    source .venv/bin/activate
else
    echo "未找到虚拟环境，正在创建 venv 并安装依赖..."
    $PYTHON_CMD -m venv venv || exit 1
    source venv/bin/activate
    pip install -r requirements.txt || exit 1
fi

echo "启动机器人..."
python telegram_bot.py

echo
echo "机器人已停止运行"
read -p "按Enter键继续..."
