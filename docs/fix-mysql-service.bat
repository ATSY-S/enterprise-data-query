@echo off
chcp 65001 >nul
echo ============================================
echo  MySQL80 服务修复脚本（必须以管理员身份运行）
echo ============================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 请右键本文件 - 以管理员身份运行
    pause
    exit /b 1
)

set MYSQL_HOME=D:\123
set CONF_DIR=C:\ProgramData\MySQL\MySQL Server 8.0
set DATA_DIR=%CONF_DIR%\Data

echo [1/5] 创建配置与数据目录
if not exist "%CONF_DIR%" mkdir "%CONF_DIR%"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

echo [2/5] 写入 my.ini
copy /Y "%~dp0mysql-my.ini" "%CONF_DIR%\my.ini" >nul

echo [3/5] 初始化数据目录（首次运行需要，已初始化可跳过）
if not exist "%DATA_DIR%\mysql" (
    "%MYSQL_HOME%\bin\mysqld.exe" --defaults-file="%CONF_DIR%\my.ini" --initialize-insecure --console
)

echo [4/5] 授权 NetworkService 访问数据目录
icacls "%CONF_DIR%" /grant "NT AUTHORITY\NetworkService:(OI)(CI)F" /T /Q

echo [5/5] 启动服务
sc config MYSQL80 binPath= "\"%MYSQL_HOME%\bin\mysqld.exe\" --defaults-file=\"%CONF_DIR%\my.ini\" MYSQL80"
net start MYSQL80

echo.
echo 完成。用以下命令测试（密码为空）：
echo   "%MYSQL_HOME%\bin\mysql.exe" -u root -p
echo.
pause
