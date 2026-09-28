@echo off
chcp 65001 > nul
REM 切换到脚本所在目录，保证双击运行时能找到 config.py 和 session\
cd /d "%~dp0"

echo 正在启动 Telegram Bot...
echo.

REM 检查虚拟环境是否存在并激活，不存在则自动创建并安装依赖
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境 ^(venv^)...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo 激活虚拟环境 ^(.venv^)...
    call .venv\Scripts\activate.bat
) else (
    echo 未找到虚拟环境，正在创建 venv 并安装依赖...
    python -m venv venv || goto :error
    call venv\Scripts\activate.bat
    pip install -r requirements.txt || goto :error
)

echo 启动机器人...
python telegram_bot.py

echo.
echo 机器人已停止运行
pause
exit /b

:error
echo 错误: 创建虚拟环境或安装依赖失败，请确认已安装 Python 3 并已加入 PATH
pause
exit /b 1
