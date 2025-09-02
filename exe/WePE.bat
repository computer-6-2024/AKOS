@echo off
chcp 65001 > nul

setlocal

set "DOWNLOAD_URL=https://mirrors.lzu.edu.cn/wepe/WePE_64_V2.3.exe"
set "OUTPUT_FILENAME=WePE_64_V2.3.exe"
set "DOWNLOAD_DIR=%~dp0"

set "FULL_OUTPUT_PATH=%DOWNLOAD_DIR%%OUTPUT_FILENAME%"
set "DOWNLOADED_FILENAME=WePE_64_V2.3.exe"  
set "RENAMED_FILENAME=WePE.exe"             
set "FULL_RENAMED_PATH=%DOWNLOAD_DIR%%DOWNLOADED_FILENAME%"

echo 
echo.
echo 正在尝试从 %DOWNLOAD_URL% 下载 %OUTPUT_FILENAME% (使用 curl)...
echo 下载到: %FULL_OUTPUT_PATH%
echo.


curl -L -o "%FULL_OUTPUT_PATH%" "%DOWNLOAD_URL%" --progress-bar
ren "%FULL_OUTPUT_PATH%" "%RENAMED_FILENAME%"

if %errorlevel% equ 0 (
    echo.
    echo 文件 %OUTPUT_FILENAME% 下载成功！
) else (
    echo.
    echo 错误: 文件下载失败。错误代码: %errorlevel%
    echo 请检查 URL, 网络连接或文件是否存在。
    echo 如果 curl 提示 SSL/TLS 错误，可能是证书问题。
)

:end
echo.
endlocal
