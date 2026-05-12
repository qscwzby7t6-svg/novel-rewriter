@echo off
chcp 65001 >nul
title 仿写百万字小说软件 - 安装程序
echo ============================================
echo  仿写百万字小说软件 - Windows 安装程序
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    echo.
    echo 请按以下步骤安装 Python：
    echo 1. 访问 https://www.python.org/downloads/
    echo 2. 点击 "Download Python 3.11.x"
    echo 3. 安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [成功] Python 已安装
python --version
echo.

REM 升级 pip
echo [步骤] 升级 pip...
python -m pip install --upgrade pip -q
if errorlevel 1 (
    echo [警告] pip 升级失败，尝试继续...
) else (
    echo [成功] pip 已升级
)

REM 安装依赖
echo.
echo [步骤] 安装 Python 依赖...
echo 正在安装，请耐心等待...

REM 尝试使用清华镜像
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet

if errorlevel 1 (
    echo [警告] 使用镜像安装失败，尝试默认源...
    python -m pip install -r requirements.txt --quiet
    
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        echo.
        echo 可能的原因：
        echo 1. 网络连接问题
        echo 2. 缺少 Visual C++ 编译工具
        echo.
        echo 解决方案：
        echo - 检查网络连接
        echo - 访问 https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo - 安装 "C++ build tools"
        echo.
        pause
        exit /b 1
    )
)

echo [成功] 依赖安装完成
echo.

REM 创建目录
echo [步骤] 创建数据目录...
if not exist "data\input" mkdir "data\input"
if not exist "data\output" mkdir "data\output"
if not exist "data\templates" mkdir "data\templates"
if not exist "logs" mkdir "logs"
echo [成功] 目录创建完成
echo.

REM 配置
echo [步骤] 设置配置文件...
if not exist "config\config.yaml" (
    if exist "config\config.example.yaml" (
        copy "config\config.example.yaml" "config\config.yaml" >nul
        echo [成功] 配置文件已创建: config\config.yaml
        echo [重要] 请编辑 config\config.yaml 填入你的 API 密钥
    ) else (
        echo [警告] 未找到配置模板
    )
) else (
    echo [信息] 配置文件已存在
)
echo.

REM 测试
echo [步骤] 测试安装...
python -c "import fastapi, pydantic, yaml" >nul 2>&1
if errorlevel 1 (
    echo [警告] 模块导入测试失败
) else (
    echo [成功] 核心模块导入成功
)
echo.

REM Node.js 检查
node --version >nul 2>&1
if errorlevel 1 (
    echo [信息] 未检测到 Node.js，跳过 CLI 安装
    echo 如需 CLI 功能，请访问 https://nodejs.org/ 下载安装
) else (
    echo [成功] Node.js 已安装
    node --version
    echo.
    set /p install_cli="是否安装 CLI 前端? (Y/n): "
    if /i "!install_cli!"=="n" (
        echo 跳过 CLI 安装
    ) else (
        echo [步骤] 安装 CLI 依赖...
        call npm config set registry https://registry.npmmirror.com
        call npm install
        if errorlevel 1 (
            echo [警告] CLI 安装失败
        ) else (
            echo [成功] CLI 安装完成
        )
    )
)

echo.
echo ============================================
echo  安装完成!
echo ============================================
echo.
echo 使用指南:
echo.
echo 1. 配置 API 密钥:
echo    用记事本打开 config\config.yaml，填入你的 API 密钥
echo.
echo 2. 启动服务:
echo    python -m uvicorn backend.main:app --reload
echo.
echo 3. 访问 API 文档:
echo    http://localhost:8000/docs
echo.
echo 4. 运行测试:
echo    python tests\test_e2e_shuihu.py
echo.
echo 5. 使用 CLI (如果已安装):
echo    node cli\index.js start
echo.
echo ============================================
echo.
pause
