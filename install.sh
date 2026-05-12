#!/bin/bash
# 仿写百万字小说软件 - Linux/macOS 一键安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_step() {
    echo -e "\n${BLUE}[步骤]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$NAME
        else
            OS="Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
    else
        OS="Unknown"
    fi
    echo "$OS"
}

# 检查 Python
check_python() {
    print_step "检查 Python 环境..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "未检测到 Python"
        echo "请安装 Python 3.10 或更高版本:"
        echo "- Ubuntu/Debian: sudo apt install python3.10"
        echo "- CentOS/RHEL: sudo yum install python310"
        echo "- macOS: brew install python@3.10"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        print_error "Python 版本过低: $PYTHON_VERSION"
        echo "需要 Python 3.10 或更高版本"
        exit 1
    fi
    
    print_success "Python 版本: $PYTHON_VERSION"
}

# 安装系统依赖
install_system_deps() {
    print_step "安装系统依赖..."
    
    OS=$(detect_os)
    print_step "检测到操作系统: $OS"
    
    case "$OS" in
        *Ubuntu*|*Debian*)
            sudo apt-get update
            sudo apt-get install -y python3-pip python3-venv git curl
            ;;
        *CentOS*|*RHEL*|*Fedora*)
            sudo yum update -y
            sudo yum install -y python3-pip python3-virtualenv git curl
            ;;
        *macOS*)
            if ! command -v brew &> /dev/null; then
                print_warning "未检测到 Homebrew，请先安装: https://brew.sh"
            else
                brew install python@3.10 git
            fi
            ;;
        *)
            print_warning "未知的操作系统，请手动安装依赖"
            ;;
    esac
    
    print_success "系统依赖安装完成"
}

# 安装 Python 依赖
install_python_deps() {
    print_step "安装 Python 依赖..."
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip -q
    
    # 检测国内网络
    MIRROR=""
    if curl -s --max-time 5 https://pypi.tuna.tsinghua.edu.cn > /dev/null 2>&1; then
        MIRROR="-i https://pypi.tuna.tsinghua.edu.cn/simple"
        echo "使用清华镜像源加速下载"
    fi
    
    # 安装依赖
    if ! pip install -r requirements.txt $MIRROR; then
        print_warning "依赖安装失败，尝试使用预编译包..."
        pip install -r requirements.txt --only-binary :all: $MIRROR
    fi
    
    print_success "Python 依赖安装完成"
}

# 创建目录结构
create_directories() {
    print_step "创建数据目录..."
    
    mkdir -p data/input data/output data/templates logs
    
    print_success "目录创建完成"
}

# 设置配置
setup_config() {
    print_step "设置配置文件..."
    
    if [ ! -f "config/config.yaml" ]; then
        if [ -f "config/config.example.yaml" ]; then
            cp config/config.example.yaml config/config.yaml
            print_success "配置文件已创建"
            print_warning "请编辑 config/config.yaml 填入你的 API 密钥"
        else
            print_warning "未找到配置模板"
        fi
    else
        print_warning "配置文件已存在"
    fi
}

# 测试安装
test_installation() {
    print_step "测试安装..."
    
    source venv/bin/activate
    
    # 测试导入
    if python -c "import fastapi, pydantic, yaml" 2>/dev/null; then
        print_success "核心模块导入成功"
    else
        print_warning "模块导入测试失败"
    fi
}

# 安装 CLI
install_cli() {
    print_step "检查 Node.js..."
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js 已安装: $NODE_VERSION"
        
        read -p "是否安装 CLI 前端? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_step "安装 CLI 依赖..."
            npm config set registry https://registry.npmmirror.com
            npm install
            print_success "CLI 安装完成"
        fi
    else
        print_warning "未检测到 Node.js，跳过 CLI 安装"
    fi
}

# 创建 systemd 服务 (仅 Linux)
create_systemd_service() {
    if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
        print_step "创建系统服务..."
        
        read -p "是否创建 systemd 服务? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            SERVICE_FILE="/etc/systemd/system/novel-rewriter.service"
            
            sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Novel Rewriter Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF
            
            sudo systemctl daemon-reload
            sudo systemctl enable novel-rewriter
            print_success "系统服务创建完成"
            echo "启动命令: sudo systemctl start novel-rewriter"
            echo "查看状态: sudo systemctl status novel-rewriter"
        fi
    fi
}

# 打印使用说明
print_usage() {
    echo ""
    echo "========================================"
    echo "  安装完成!"
    echo "========================================"
    echo ""
    echo "使用指南:"
    echo ""
    echo "1. 配置 API 密钥:"
    echo "   编辑 config/config.yaml，填入你的 API 密钥"
    echo ""
    echo "2. 激活虚拟环境:"
    echo "   source venv/bin/activate"
    echo ""
    echo "3. 启动服务:"
    echo "   python -m uvicorn backend.main:app --reload"
    echo ""
    echo "4. 访问 API 文档:"
    echo "   http://localhost:8000/docs"
    echo ""
    echo "5. 运行测试:"
    echo "   python tests/test_e2e_shuihu.py"
    echo ""
    echo "========================================"
}

# 主函数
main() {
    echo "========================================"
    echo "  仿写百万字小说软件 - 安装程序"
    echo "========================================"
    echo ""
    
    # 检查是否在项目根目录
    if [ ! -f "requirements.txt" ]; then
        print_error "请在项目根目录运行此脚本"
        echo "当前目录: $(pwd)"
        exit 1
    fi
    
    # 执行安装步骤
    check_python
    install_system_deps
    install_python_deps
    create_directories
    setup_config
    test_installation
    install_cli
    create_systemd_service
    
    print_usage
}

# 运行主函数
main
