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

echo [3/6] 初始化数据目录（首次运行需要，已初始化可跳过）
set NEED_INIT=0
if not exist "%DATA_DIR%\mysql" set NEED_INIT=1
if "%NEED_INIT%"=="1" (
    "%MYSQL_HOME%\bin\mysqld.exe" --defaults-file="%CONF_DIR%\my.ini" --initialize-insecure --console
)

echo [4/6] 授权 NetworkService 访问数据目录
icacls "%CONF_DIR%" /grant "NT AUTHORITY\NetworkService:(OI)(CI)F" /T /Q

echo [5/6] 启动服务
sc config MYSQL80 binPath= "\"%MYSQL_HOME%\bin\mysqld.exe\" --defaults-file=\"%CONF_DIR%\my.ini\" MYSQL80"
net start MYSQL80

echo [6/6] 设置 root 密码为 123456
if "%NEED_INIT%"=="1" (
    "%MYSQL_HOME%\bin\mysql.exe" -h127.0.0.1 -uroot --skip-password -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456'; FLUSH PRIVILEGES;"
    echo root 密码已设为 123456
) else (
    echo 数据目录已存在，跳过（如密码不对请手动执行：）
    echo   mysql -uroot -p123456 -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';"
)

echo.
echo 完成。DataGrip 连接参数：
echo   主机 localhost  端口 3306  用户 root  密码 123456
echo 命令行测试：
echo   "%MYSQL_HOME%\bin\mysql.exe" -h127.0.0.1 -uroot -p123456
echo.
pause
