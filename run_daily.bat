@echo off
chcp 65001 >nul
cd /d C:\Users\d\Desktop\worksapce\bio

REM 设置环境变量（如果需要，可以在这里设置）
REM set DEEPSEEK_API_KEY=your_key_here
REM set PUBMED_EMAIL=your_email@example.com
REM set PUSHPLUS_TOKENS=token1,token2,token3

REM 执行推送任务（使用新的模块化命令）
python -m app run

REM 如果出错，记录到日志（不暂停，适合定时任务）
if errorlevel 1 (
    echo [%date% %time%] 任务执行失败，错误代码: %errorlevel% >> logs\error.log
)



