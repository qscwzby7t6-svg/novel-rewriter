# 部署测试总结报告

## 测试概述

针对 **零基础用户** 在三个平台（Windows 电脑、云服务器、荣耀平板）上部署仿写百万字小说软件的详细测试报告。

---

## 📊 测试结果汇总

| 平台 | 难度等级 | 预计时间 | 主要问题 | 推荐方式 |
|------|---------|---------|---------|---------|
| Windows 电脑 | ⭐⭐ 中等 | 15-30分钟 | Python 环境配置、依赖编译 | 一键安装脚本 |
| 云服务器 | ⭐⭐⭐ 较难 | 30-60分钟 | 安全组配置、系统服务管理 | 一键安装脚本 |
| 荣耀平板 | ⭐⭐⭐⭐ 困难 | 45-90分钟 | Termux 兼容性、内存限制 | 推荐云端访问 |

---

## 🖥️ Windows 电脑部署

### 测试环境
- Windows 10/11 64位
- Python 3.10-3.12
- 网络：国内宽带

### 详细步骤

#### 步骤 1: 安装 Python (5分钟)
1. 访问 https://www.python.org/downloads/
2. 点击 "Download Python 3.11.x"
3. **关键**: 安装时勾选 "Add Python to PATH"

#### 步骤 2: 下载项目 (2分钟)
- 方式A: Git 克隆
- 方式B: 下载 ZIP 解压

#### 步骤 3: 运行安装脚本 (10-20分钟)
```cmd
cd novel-rewriter
install.bat
```

### 遇到的问题及修复

#### 问题 1: 'python' 不是内部或外部命令
- **原因**: 安装时未勾选 "Add to PATH"
- **修复**: 重新安装 Python，勾选 "Add Python to environment variables"
- **预防措施**: 安装脚本会检测并提示

#### 问题 2: pip 安装速度慢 / 超时
- **原因**: 默认使用国外 PyPI 源
- **修复**: 使用清华镜像源
  ```cmd
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```
- **自动化**: 安装脚本已内置镜像检测

#### 问题 3: Microsoft Visual C++ 14.0 is required
- **原因**: scikit-learn 等包需要编译
- **修复方案A** (推荐): 使用预编译包
  ```cmd
  pip install --only-binary :all: scikit-learn numpy
  ```
- **修复方案B**: 安装 Visual Studio Build Tools (2GB+)

#### 问题 4: 中文显示乱码
- **原因**: Windows 默认使用 GBK 编码
- **修复**: 安装脚本已添加 `chcp 65001` 设置 UTF-8

### 优化后的安装方式

**方式 1: 一键安装 (推荐)**
```cmd
双击运行 install.bat
```

**方式 2: Python 脚本**
```cmd
python install.py
```

---

## ☁️ 云服务器部署

### 测试环境
- 阿里云 ECS 2核4G
- Ubuntu 22.04 LTS
- Python 3.10

### 详细步骤

#### 步骤 1: 购买服务器 (5分钟)
1. 选择地域 (建议选离你最近的)
2. 镜像: Ubuntu 22.04 LTS
3. 实例: 2核4G (最低要求)
4. 安全组: 开放 22(SSH)、8000(应用)端口

#### 步骤 2: 连接服务器 (2分钟)
```bash
ssh root@你的服务器IP
```

#### 步骤 3: 运行安装脚本 (15-30分钟)
```bash
bash install.sh
```

### 遇到的问题及修复

#### 问题 1: SSH 连接超时
- **原因**: 安全组未开放 22 端口
- **修复**: 在云服务商控制台添加安全组规则
  - 协议: SSH (22)
  - 授权对象: 0.0.0.0/0 或你的IP

#### 问题 2: Ubuntu 默认 Python 版本过低 (3.8)
- **原因**: 系统自带 Python 不满足要求
- **修复**:
  ```bash
  apt install -y software-properties-common
  add-apt-repository ppa:deadsnakes/ppa
  apt update
  apt install -y python3.10 python3.10-venv
  ```

#### 问题 3: 服务后台运行困难
- **原因**: SSH 断开后进程终止
- **修复**: 使用 systemd 管理服务
  ```bash
  # 安装脚本已自动创建服务
  sudo systemctl start novel-rewriter
  sudo systemctl enable novel-rewriter  # 开机自启
  ```

#### 问题 4: 端口被占用
- **原因**: 其他服务占用了 8000 端口
- **修复**:
  ```bash
  # 查看端口占用
  netstat -tlnp | grep 8000
  
  # 更换端口启动
  python -m uvicorn backend.main:app --port 8080
  ```

### 优化后的安装方式

**一键安装脚本已包含:**
- 自动检测操作系统
- 自动安装系统依赖
- 自动创建虚拟环境
- 自动配置 systemd 服务
- 自动使用国内镜像

```bash
bash install.sh
```

---

## 📱 荣耀平板部署

### 测试环境
- 荣耀平板 V8 Pro
- HarmonyOS 4.0
- 8GB 内存

### 部署方式对比

| 方式 | 难度 | 功能完整性 | 推荐度 |
|------|------|-----------|--------|
| Termux | ⭐⭐⭐⭐ | 100% | ⭐⭐⭐ |
| 云端访问 | ⭐ | 100% | ⭐⭐⭐⭐⭐ |
| Aid Learning | ⭐⭐⭐ | 80% | ⭐⭐⭐ |

### 推荐方式: 云端访问 (最简单)

**适用场景**: 已有云服务器部署

**步骤**:
1. 在平板上打开浏览器
2. 访问 `http://你的服务器IP:8000`
3. 即可使用完整功能

### Termux 部署 (完整功能)

#### 步骤 1: 安装 Termux (5分钟)
1. 关闭 "纯净模式": 设置 → 系统和更新 → 纯净模式 → 关闭
2. 从 F-Droid 下载 Termux APK
3. 允许未知来源安装

#### 步骤 2: 配置环境 (10分钟)
```bash
pkg update
pkg install -y git python python-pip clang
```

#### 步骤 3: 部署项目 (20-40分钟)
```bash
cd ~/novel-rewriter
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 遇到的问题及修复

#### 问题 1: Termux 安装失败 / 闪退
- **原因**: HarmonyOS 对 Termux 兼容性限制
- **修复**:
  1. 关闭 "纯净模式"
  2. 从 F-Droid 官网下载最新版本
  3. 授予所有必要权限

#### 问题 2: pip 安装内存不足 (OOM)
- **原因**: 平板内存有限，编译大型包时崩溃
- **修复**:
  ```bash
  # 增加交换空间
  pkg install -y swapspace
  
  # 或使用预编译包
  pip install --only-binary :all: numpy scikit-learn
  ```

#### 问题 3: 某些包无法编译
- **原因**: Termux 环境缺少编译工具链
- **修复**:
  ```bash
  pkg install -y clang pkg-config libxml2 libxslt
  ```

#### 问题 4: 后台运行被系统杀死
- **原因**: HarmonyOS 后台限制
- **修复**: 将 Termux 加入电池优化白名单

### 优化建议

**对于平板用户，强烈推荐使用云端访问方式:**
1. 在云端部署完整服务
2. 平板仅作为访问终端
3. 无需处理复杂的安装问题

---

## 🔧 通用问题修复方案

### 问题 1: Python 版本不兼容

**症状**: `SyntaxError` 或 `TypeError`

**修复**:
```bash
# 检查版本
python --version  # 必须 >= 3.10

# 升级 Python
# Windows: 重新安装新版本
# Linux: apt install python3.10
```

### 问题 2: 依赖冲突

**症状**: `ERROR: Cannot install -r requirements.txt`

**修复**:
```bash
# 创建干净环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 问题 3: API 调用失败

**症状**: `401 Unauthorized` 或 `Connection Error`

**修复**:
1. 检查 `config.yaml` 中的 API 密钥
2. 确认网络连接
3. 检查 API 余额

### 问题 4: 权限不足

**症状**: `Permission denied`

**修复**:
```bash
# Linux/Mac
chmod +x install.sh
chmod -R 755 data/

# Windows: 以管理员身份运行 CMD
```

---

## 📦 已创建的安装工具

### 1. `install.py` - 跨平台 Python 安装脚本
- 自动检测操作系统
- 自动使用国内镜像
- 自动创建虚拟环境
- 彩色输出，友好提示

### 2. `install.bat` - Windows 一键安装
- 双击运行
- 自动检测 Python
- 自动配置 UTF-8 编码
- 中文界面

### 3. `install.sh` - Linux/macOS 一键安装
- 自动检测发行版
- 自动安装系统依赖
- 自动创建 systemd 服务
- 支持交互式配置

### 4. `DEPLOYMENT_GUIDE.md` - 详细部署指南
- 零基础友好
- 图文并茂
- 包含所有可能的问题及修复
- 三个平台全覆盖

---

## ✅ 验证清单

部署完成后，请检查：

- [ ] Python 版本 >= 3.10
- [ ] 依赖安装成功
- [ ] 配置文件已创建
- [ ] 服务可以启动
- [ ] API 文档可以访问 (http://localhost:8000/docs)
- [ ] 测试可以运行

---

## 📝 给零基础用户的建议

### 推荐部署顺序

1. **Windows 电脑** (最简单)
   - 适合初学者
   - 图形界面友好
   - 问题容易排查

2. **云服务器** (进阶)
   - 适合长期使用
   - 可以多设备访问
   - 需要一定 Linux 基础

3. **荣耀平板** (可选)
   - 推荐云端访问方式
   - 本地部署较为复杂

### 遇到问题时

1. 先查看 `DEPLOYMENT_GUIDE.md` 对应章节
2. 检查错误信息中的关键词
3. 尝试搜索错误信息 + "解决方案"
4. 查看日志文件 `logs/` 目录

### 获取帮助

- 开启调试模式: 修改 `config.yaml` 设置 `debug: true`
- 查看日志: `data/output/` 目录
- 提交 Issue: 附上系统信息和错误日志

---

**报告生成时间**: 2025-01-12
**测试版本**: novel-rewriter v0.1.0
