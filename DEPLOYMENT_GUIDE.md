# 仿写百万字小说软件 - 部署指南

> 面向零基础用户的详细部署教程
> 支持平台：Windows 电脑 / 云服务器 / 荣耀平板

---

## 📋 目录

1. [部署前准备](#部署前准备)
2. [Windows 电脑部署](#windows-电脑部署)
3. [云服务器部署](#云服务器部署)
4. [荣耀平板部署](#荣耀平板部署)
5. [常见问题与修复](#常见问题与修复)
6. [验证安装](#验证安装)

---

## 部署前准备

### 系统要求

| 平台 | 最低配置 | 推荐配置 |
|------|---------|---------|
| Windows | Win10 64位, 4GB内存 | Win11 64位, 8GB内存 |
| 云服务器 | 2核2G, 20GB硬盘 | 2核4G, 50GB硬盘 |
| 荣耀平板 | HarmonyOS 3.0+, 6GB内存 | HarmonyOS 4.0+, 8GB内存 |

### 必需软件

- **Python 3.10+** (后端运行环境)
- **Node.js 18+** (CLI前端，可选)
- **Git** (代码下载，可选)

---

## Windows 电脑部署

### 步骤 1：安装 Python

#### 1.1 下载 Python

1. 打开浏览器，访问 https://www.python.org/downloads/
2. 点击 **"Download Python 3.11.x"** (大黄色按钮)
3. 下载完成后，双击运行安装程序

#### 1.2 安装 Python

⚠️ **关键步骤**：安装时必须勾选 **"Add Python to PATH"**

```
☑️ Add Python 3.11 to PATH  [必须勾选！]
   Install Now
```

#### 1.3 验证安装

打开 **命令提示符** (按 `Win + R`，输入 `cmd`，回车)：

```cmd
python --version
```

应该显示：`Python 3.11.x`

**常见问题 1**：'python' 不是内部或外部命令
- **原因**：安装时未勾选 "Add to PATH"
- **修复**：
  1. 重新运行 Python 安装程序
  2. 选择 "Modify"
  3. 勾选 "Add Python to environment variables"
  4. 点击 Install

---

### 步骤 2：下载项目代码

#### 方法 A：使用 Git (推荐)

```cmd
# 安装 Git (如果未安装)
# 访问 https://git-scm.com/download/win 下载安装

# 克隆项目
git clone https://github.com/your-repo/novel-rewriter.git
cd novel-rewriter
```

#### 方法 B：直接下载 ZIP

1. 访问项目页面
2. 点击 **Code** → **Download ZIP**
3. 解压到 `C:\novel-rewriter` 文件夹
4. 打开命令提示符：

```cmd
cd C:\novel-rewriter
```

---

### 步骤 3：安装 Python 依赖

```cmd
# 升级 pip (包管理工具)
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

**常见问题 2**：pip 安装速度慢 / 超时
- **原因**：默认使用国外源，网络不稳定
- **修复**：使用国内镜像源

```cmd
# 临时使用清华镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或永久设置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

**常见问题 3**：安装失败，提示 "Microsoft Visual C++ 14.0 is required"
- **原因**：某些 Python 包需要编译工具
- **修复**：
  1. 访问 https://visualstudio.microsoft.com/visual-cpp-build-tools/
  2. 下载 "Build Tools for Visual Studio"
  3. 安装时选择 "C++ build tools"
  4. 重新运行 pip install

**简化修复** (推荐)：
```cmd
# 安装预编译版本，避免编译
pip install scikit-learn numpy --only-binary :all:
```

---

### 步骤 4：配置 API 密钥

```cmd
# 复制配置文件模板
copy config\config.example.yaml config\config.yaml

# 使用记事本编辑
notepad config\config.yaml
```

修改以下内容：

```yaml
llm:
  provider: deepseek  # 或 openai
  api_key: "your-api-key-here"  # 替换为你的API密钥
  model: deepseek-chat
```

**获取 API 密钥**：
- DeepSeek: https://platform.deepseek.com/
- OpenAI: https://platform.openai.com/

---

### 步骤 5：运行测试

```cmd
# 运行端到端测试
python tests\test_e2e_shuihu.py
```

---

### 步骤 6：安装 CLI 前端 (可选)

```cmd
# 安装 Node.js (访问 https://nodejs.org/ 下载 LTS 版本)
# 验证安装
node --version  # 应显示 v18.x.x 或更高

# 安装 CLI 依赖
npm install

# 使用 CLI
node cli\index.js start
```

---

## 云服务器部署

### 适用场景

- 24小时不间断运行
- 多设备远程访问
- 处理大量任务

### 推荐云服务商

| 服务商 | 推荐配置 | 预估月费 |
|--------|---------|---------|
| 阿里云 | 2核4G，CentOS 8 | ¥80-150 |
| 腾讯云 | 2核4G，Ubuntu 22.04 | ¥80-150 |
| 华为云 | 2核4G，EulerOS | ¥80-150 |

### 步骤 1：购买并连接服务器

#### 1.1 购买服务器

1. 登录云服务商控制台
2. 选择 **云服务器 ECS**
3. 配置选择：
   - 地域：选择离你最近的
   - 镜像：**Ubuntu 22.04 LTS** (推荐)
   - 实例：2核4G
   - 带宽：3-5Mbps
   - 安全组：开放 22(SSH)、8000(应用)端口

#### 1.2 连接服务器

**Windows 用户**：

```cmd
# 使用 SSH 连接 (Windows 10/11 内置)
ssh root@你的服务器IP

# 输入密码 (购买时设置)
```

或使用 **PuTTY**：
1. 下载 https://www.putty.org/
2. Host Name: `你的服务器IP`
3. Port: `22`
4. 点击 Open

**常见问题 4**：连接超时 / 拒绝连接
- **原因**：安全组未开放 22 端口
- **修复**：
  1. 登录云服务商控制台
  2. 找到安全组配置
  3. 添加规则：
     - 协议：SSH (22)
     - 授权对象：0.0.0.0/0 (或你的IP)

---

### 步骤 2：安装环境

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Python 和依赖
apt install -y python3.10 python3-pip python3-venv git

# 验证
python3 --version  # Python 3.10.x
```

**常见问题 5**：Ubuntu 默认 Python 版本过低
- **修复**：

```bash
# 添加 deadsnakes PPA
apt install -y software-properties-common
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install -y python3.10 python3.10-venv python3.10-dev
```

---

### 步骤 3：部署项目

```bash
# 创建应用目录
mkdir -p /opt/novel-rewriter
cd /opt/novel-rewriter

# 下载代码 (使用 Git)
git clone https://github.com/your-repo/novel-rewriter.git .

# 或使用 wget 下载 ZIP
wget https://github.com/your-repo/novel-rewriter/archive/main.zip
apt install -y unzip
unzip main.zip
mv novel-rewriter-main/* .

# 创建虚拟环境 (推荐)
python3.10 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 步骤 4：配置并启动

```bash
# 配置
cp config/config.example.yaml config/config.yaml
vim config/config.yaml  # 或使用 nano

# 后台启动服务
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# 查看日志
tail -f app.log
```

---

### 步骤 5：使用 systemd 管理 (推荐)

创建服务文件：

```bash
cat > /etc/systemd/system/novel-rewriter.service << 'EOF'
[Unit]
Description=Novel Rewriter Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/novel-rewriter
Environment=PATH=/opt/novel-rewriter/venv/bin
ExecStart=/opt/novel-rewriter/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl enable novel-rewriter
systemctl start novel-rewriter

# 查看状态
systemctl status novel-rewriter
```

---

### 步骤 6：配置域名和 HTTPS (可选)

使用 Nginx 反向代理：

```bash
apt install -y nginx certbot python3-certbot-nginx

# 配置 Nginx
cat > /etc/nginx/sites-available/novel-rewriter << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/novel-rewriter /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 申请 HTTPS 证书
certbot --nginx -d your-domain.com
```

---

## 荣耀平板部署

### 说明

荣耀平板基于 HarmonyOS/Android，**原生不支持直接运行 Python 后端**。需要通过以下方式：

1. **方式 A**：使用 Termux 安装 Linux 环境 (推荐)
2. **方式 B**：通过浏览器访问云端部署的服务
3. **方式 C**：使用 Aid Learning 等 Python IDE

### 方式 A：Termux 部署 (完整功能)

#### 步骤 1：安装 Termux

1. 打开 **华为应用市场** 或 **浏览器**
2. 搜索 **Termux** (或从 F-Droid 下载)
3. 安装应用

⚠️ **注意**：部分荣耀平板可能无法直接从应用市场安装 Termux，需要从官网下载 APK：
- https://f-droid.org/packages/com.termux/

#### 步骤 2：配置 Termux

```bash
# 打开 Termux 应用
# 更新包列表
pkg update

# 安装必要工具
pkg install -y git python python-pip

# 安装依赖 (部分包可能需要编译，耗时较长)
pkg install -y clang pkg-config libxml2 libxslt
```

**常见问题 6**：Termux 安装失败 / 闪退
- **原因**：HarmonyOS 对 Termux 兼容性限制
- **修复**：
  1. 关闭 "纯净模式"：设置 → 系统和更新 → 纯净模式 → 关闭
  2. 允许未知来源安装
  3. 从 F-Droid 下载最新版本

**常见问题 7**：pip 安装内存不足
- **原因**：平板内存有限，编译大型包时 OOM
- **修复**：

```bash
# 增加交换空间
pkg install -y swapspace

# 或使用预编译包
pip install --only-binary :all: numpy scikit-learn
```

#### 步骤 3：部署项目

```bash
# 创建项目目录
mkdir -p ~/novel-rewriter
cd ~/novel-rewriter

# 下载代码
git clone https://github.com/your-repo/novel-rewriter.git .

# 安装依赖 (使用国内源)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置
cp config/config.example.yaml config/config.yaml
```

#### 步骤 4：运行

```bash
# 启动服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 在平板上打开浏览器，访问
# http://localhost:8000
```

---

### 方式 B：访问云端服务 (最简单)

如果已在云服务器部署，直接在平板浏览器访问：

```
http://你的服务器IP:8000
```

**推荐浏览器**：Chrome、Edge、华为浏览器

---

### 方式 C：Aid Learning (图形界面)

1. 安装 **Aid Learning** 应用
2. 内置 Python 环境，可直接运行
3. 通过内置终端执行部署命令

---

## 常见问题与修复

### 🔴 严重问题

#### 问题 1：Python 版本不兼容

**症状**：`SyntaxError` 或 `TypeError`

**修复**：
```bash
# 检查版本
python --version  # 必须 >= 3.10

# 升级 Python
# Windows: 重新安装新版本
# Linux: apt install python3.10
```

#### 问题 2：依赖冲突

**症状**：`ERROR: Cannot install -r requirements.txt`

**修复**：
```bash
# 创建干净环境
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 重新安装
pip install -r requirements.txt
```

---

### 🟡 一般问题

#### 问题 3：API 调用失败

**症状**：`401 Unauthorized` 或 `Connection Error`

**修复**：
1. 检查 `config.yaml` 中的 API 密钥
2. 确认网络连接
3. 检查 API 余额

#### 问题 4：中文显示乱码

**症状**：控制台输出乱码

**修复**：
```bash
# Windows
chcp 65001  # 设置 UTF-8

# 或在代码中添加
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

#### 问题 5：权限不足

**症状**：`Permission denied`

**修复**：
```bash
# Linux/Mac
chmod +x cli/index.js
chmod -R 755 data/

# Windows (以管理员身份运行 CMD)
```

---

### 🟢 性能优化

#### 优化 1：使用国内镜像

```bash
# Python
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Node.js
npm config set registry https://registry.npmmirror.com
```

#### 优化 2：启用缓存

```bash
# pip 缓存
pip install --cache-dir ~/.pip/cache

# 依赖预编译
pip install --only-binary :all: numpy pandas
```

---

## 验证安装

运行以下命令验证部署成功：

```bash
# 1. Python 环境
python --version  # >= 3.10

# 2. 依赖检查
pip list | findstr fastapi  # Windows
pip list | grep fastapi     # Linux/Mac

# 3. 运行测试
python tests/test_e2e_shuihu.py

# 4. 服务启动
python -m uvicorn backend.main:app --reload
# 访问 http://localhost:8000/docs 查看 API 文档
```

---

## 获取帮助

遇到问题？

1. 查看日志：`data/output/` 目录下的日志文件
2. 开启调试模式：修改 `config.yaml` 设置 `debug: true`
3. 提交 Issue：附上错误日志和系统信息

---

**最后更新**：2025-01-12
