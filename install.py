#!/usr/bin/env python3
"""
仿写百万字小说软件 - 自动化安装脚本
支持: Windows / Linux / macOS
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_step(msg):
    print(f"\n{Colors.BLUE}[步骤]{Colors.END} {msg}")


def print_success(msg):
    print(f"{Colors.GREEN}[成功]{Colors.END} {msg}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[警告]{Colors.END} {msg}")


def print_error(msg):
    print(f"{Colors.RED}[错误]{Colors.END} {msg}")


def run_command(cmd, check=True):
    """运行命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"命令执行失败: {cmd}")
            print(f"错误信息: {e.stderr}")
        raise


def check_python():
    """检查 Python 版本"""
    print_step("检查 Python 环境...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print_error(f"Python 版本过低: {version.major}.{version.minor}")
        print("需要 Python 3.10 或更高版本")
        print("\n安装方法:")
        print("- Windows: 访问 https://www.python.org/downloads/")
        print("- Linux: sudo apt install python3.10")
        print("- macOS: brew install python@3.10")
        return False
    
    print_success(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True


def check_pip():
    """检查并升级 pip"""
    print_step("检查 pip...")
    
    try:
        run_command("python -m pip --version", check=False)
        print_success("pip 已安装")
        
        # 升级 pip
        print_step("升级 pip...")
        run_command("python -m pip install --upgrade pip -q")
        print_success("pip 已升级")
        return True
    except Exception as e:
        print_error(f"pip 检查失败: {e}")
        return False


def install_dependencies():
    """安装 Python 依赖"""
    print_step("安装 Python 依赖...")
    
    # 检测国内网络，使用镜像源
    mirror = ""
    try:
        # 测试连接清华镜像
        result = run_command("python -c \"import urllib.request; urllib.request.urlopen('https://pypi.tuna.tsinghua.edu.cn', timeout=5)\"", check=False)
        if result.returncode == 0:
            mirror = "-i https://pypi.tuna.tsinghua.edu.cn/simple"
            print("使用清华镜像源加速下载")
    except:
        pass
    
    # 安装依赖
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print_error("未找到 requirements.txt 文件")
        return False
    
    try:
        cmd = f"python -m pip install -r requirements.txt {mirror}"
        print(f"执行: {cmd}")
        run_command(cmd)
        print_success("依赖安装完成")
        return True
    except Exception as e:
        print_error(f"依赖安装失败: {e}")
        print("\n尝试使用预编译包...")
        try:
            run_command(f"python -m pip install -r requirements.txt --only-binary :all: {mirror}")
            print_success("依赖安装完成 (使用预编译包)")
            return True
        except Exception as e2:
            print_error(f"预编译包安装也失败: {e2}")
            return False


def setup_config():
    """设置配置文件"""
    print_step("设置配置文件...")
    
    config_dir = Path("config")
    config_file = config_dir / "config.yaml"
    example_file = config_dir / "config.example.yaml"
    
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
    
    if config_file.exists():
        print_warning("配置文件已存在，跳过创建")
        return True
    
    if example_file.exists():
        shutil.copy(example_file, config_file)
        print_success("配置文件已创建: config/config.yaml")
        print_warning("请编辑 config/config.yaml 填入你的 API 密钥")
        return True
    else:
        print_error("未找到配置模板文件")
        return False


def create_directories():
    """创建必要的目录"""
    print_step("创建数据目录...")
    
    dirs = ["data/input", "data/output", "data/templates", "logs"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    print_success("目录创建完成")
    return True


def test_installation():
    """测试安装"""
    print_step("测试安装...")
    
    try:
        # 测试导入关键模块
        run_command("python -c \"import fastapi, pydantic, yaml\"", check=False)
        print_success("核心模块导入成功")
        
        # 运行简单测试
        test_file = Path("tests/test_e2e_shuihu.py")
        if test_file.exists():
            print("是否运行完整测试? (需要 API 密钥) [y/N]", end=" ")
            choice = input().strip().lower()
            if choice == 'y':
                print_step("运行端到端测试...")
                run_command("python tests/test_e2e_shuihu.py")
                print_success("测试通过!")
        
        return True
    except Exception as e:
        print_error(f"测试失败: {e}")
        return False


def install_cli():
    """安装 CLI 前端 (可选)"""
    print_step("检查 Node.js 环境...")
    
    try:
        result = run_command("node --version", check=False)
        if result.returncode == 0:
            print_success(f"Node.js 已安装: {result.stdout.strip()}")
            
            print("是否安装 CLI 前端? [Y/n]", end=" ")
            choice = input().strip().lower()
            if choice != 'n':
                print_step("安装 CLI 依赖...")
                
                # 使用国内镜像
                run_command("npm config set registry https://registry.npmmirror.com", check=False)
                run_command("npm install")
                print_success("CLI 安装完成")
                print("使用方法: node cli/index.js")
        else:
            print_warning("未检测到 Node.js，跳过 CLI 安装")
            print("如需 CLI 功能，请访问 https://nodejs.org/ 下载安装")
    except Exception as e:
        print_warning(f"CLI 安装检查失败: {e}")


def print_usage():
    """打印使用说明"""
    print("\n" + "="*60)
    print("安装完成! 使用指南:")
    print("="*60)
    print("\n1. 配置 API 密钥:")
    print("   编辑 config/config.yaml，填入你的 DeepSeek/OpenAI API 密钥")
    print("\n2. 启动服务:")
    print("   python -m uvicorn backend.main:app --reload")
    print("\n3. 访问 API 文档:")
    print("   http://localhost:8000/docs")
    print("\n4. 运行测试:")
    print("   python tests/test_e2e_shuihu.py")
    print("\n5. 使用 CLI (如果已安装):")
    print("   node cli/index.js start")
    print("\n" + "="*60)


def main():
    """主函数"""
    print("="*60)
    print("仿写百万字小说软件 - 自动化安装")
    print("="*60)
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python: {sys.executable}")
    print("="*60)
    
    # 检查是否在项目根目录
    if not Path("requirements.txt").exists():
        print_error("请在项目根目录运行此脚本")
        print(f"当前目录: {Path.cwd()}")
        sys.exit(1)
    
    # 执行安装步骤
    steps = [
        ("Python 环境检查", check_python),
        ("pip 检查", check_pip),
        ("依赖安装", install_dependencies),
        ("目录创建", create_directories),
        ("配置文件设置", setup_config),
        ("安装测试", test_installation),
    ]
    
    failed_steps = []
    
    for name, func in steps:
        try:
            if not func():
                failed_steps.append(name)
        except Exception as e:
            print_error(f"{name} 失败: {e}")
            failed_steps.append(name)
    
    # 可选步骤
    try:
        install_cli()
    except Exception as e:
        print_warning(f"CLI 安装失败: {e}")
    
    # 总结
    print("\n" + "="*60)
    if not failed_steps:
        print_success("安装完成!")
        print_usage()
    else:
        print_error("安装过程中出现以下问题:")
        for step in failed_steps:
            print(f"  - {step}")
        print("\n请根据错误提示修复问题后重新运行安装脚本")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n安装已取消")
        sys.exit(1)
