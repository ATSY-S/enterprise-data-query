@echo off
chcp 65001 >nul
echo ============================================
echo  MYSQL80 服务启动脚本
echo ============================================
echo.
echo 请右键本文件，选择"以管理员身份运行"。
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 当前不是管理员权限。
    echo 请关闭窗口，右键本文件 -^> 以管理员身份运行。
    pause
    exit /b 1
)

echo [1/3] 检查配置文件...
if not exist "C:\ProgramData\MySQL\MySQL Server 8.0\my.ini" (
    echo [错误] 配置文件不存在，请先运行 fix-mysql-service.bat
    pause
    exit /b 1
)
echo     配置文件正常

echo [2/3] 检查数据目录...
if not exist "C:\ProgramData\MySQL\MySQL Server 8.0\Data\mysql.ibd" (
    echo [错误] 数据目录未初始化，请先运行 fix-mysql-service.bat
    pause
    exit /b 1
)
echo     数据目录正常

echo [3/3] 授权并启动服务...
icacls "C:\ProgramData\MySQL\MySQL Server 8.0" /grant "NT AUTHORITY\NetworkService:(OI)(CI)F" /T >nul
net start MYSQL80
if %errorlevel% equ 0 (
    echo.
    echo [成功] MYSQL80 服务已启动！
    echo 测试连接：mysql -h127.0.0.1 -uroot
) else (
    echo.
    echo [失败] 服务启动失败，查看错误日志：
    echo C:\ProgramData\MySQL\MySQL Server 8.0\Data\mysql.err
)
echo.
pause
