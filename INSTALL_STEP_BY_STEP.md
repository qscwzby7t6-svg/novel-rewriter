# 仿写百万字小说软件 - 复制粘贴式安装教程

> 零基础用户专用，每一步都可以直接复制粘贴执行

---

## 📋 安装前准备

### 确认您的设备类型

- **Windows 电脑** → 跳转到 [Windows 安装教程](#windows-电脑安装教程)
- **云服务器** (阿里云/腾讯云/华为云) → 跳转到 [云服务器安装教程](#云服务器安装教程)
- **荣耀平板** → 跳转到 [荣耀平板安装教程](#荣耀平板安装教程)

---

## Windows 电脑安装教程

### 第一步：安装 Python

#### 1.1 下载 Python

1. 打开浏览器，访问：https://www.python.org/downloads/
2. 点击黄色大按钮 **"Download Python 3.11.x"**
3. 下载完成后，双击运行安装程序

#### 1.2 安装 Python（关键步骤）

⚠️ **必须勾选这个选项**：

```
☑️ Add Python 3.11 to PATH    [勾选这个！]
   ☐ Install for all users    [可选]
   
   [Install Now]
```

#### 1.3 验证安装

按 `Win + R` 键，输入 `cmd`，回车打开命令提示符，然后复制粘贴：

```cmd
python --version
```

应该显示：`Python 3.11.x`

如果显示错误，说明第 1.2 步没有勾选 "Add to PATH"，请重新安装。

---

### 第二步：下载项目代码

#### 2.1 选择下载方式

**方式 A：使用 Git（推荐，需要安装 Git）**

先安装 Git：https://git-scm.com/download/win

然后打开 CMD，复制粘贴：

```cmd
cd C:\
git clone https://github.com/your-repo/novel-rewriter.git
cd novel-rewriter
```

**方式 B：直接下载 ZIP（更简单）**

1. 访问项目页面
2. 点击绿色按钮 **"Code"** → **"Download ZIP"**
3. 解压到 `C:\novel-rewriter` 文件夹
4. 打开 CMD，复制粘贴：

```cmd
cd C:\novel-rewriter
```

---

### 第三步：运行一键安装脚本

在 CMD 中，确保您在 `C:\novel-rewriter` 目录下，然后复制粘贴：

```cmd
install.bat
```

等待安装完成（约 10-20 分钟）。

如果提示找不到文件，使用这个命令：

```cmd
python install.py
```

---

### 第四步：配置 API 密钥

#### 4.1 复制配置文件

在 CMD 中复制粘贴：

```cmd
copy config\config.example.yaml config\config.yaml
```

#### 4.2 编辑配置文件

在 CMD 中复制粘贴：

```cmd
notepad config\config.yaml
```

会打开记事本，找到这一行：

```yaml
  api_key: "your-api-key-here"
```

把 `your-api-key-here` 替换为您的真实 API 密钥。

**获取 API 密钥：**
- DeepSeek：https://platform.deepseek.com/ → 注册登录 → 创建 API Key
- OpenAI：https://platform.openai.com/ → 注册登录 → 创建 API Key

修改后保存关闭（Ctrl + S，然后关闭记事本）。

---

### 第五步：启动服务

在 CMD 中复制粘贴：

```cmd
python -m uvicorn backend.main:app --reload
```

等待显示：

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### 第六步：访问系统

打开浏览器，访问：

```
http://localhost:8000/docs
```

看到 API 文档页面，说明安装成功！

---

### 第七步：运行测试（可选）

新开一个 CMD 窗口，复制粘贴：

```cmd
cd C:\novel-rewriter
python tests\test_e2e_shuihu.py
```

---

## 云服务器安装教程

> 以阿里云 Ubuntu 22.04 为例，其他云服务商类似

### 第一步：购买云服务器

1. 登录阿里云控制台：https://ecs.console.aliyun.com/
2. 点击 **"创建实例"**
3. 配置选择：
   - **地域**：选择离您最近的（如华东1-杭州）
   - **实例规格**：2核4G（推荐）或 2核2G（最低）
   - **镜像**：Ubuntu 22.04 LTS 64位
   - **带宽**：3Mbps（够用）
   - **安全组**：勾选 **"SSH (22)"** 和 **"HTTP (80)"**
4. 设置登录密码，记住密码！
5. 点击 **"创建实例"**

---

### 第二步：连接服务器

#### 2.1 Windows 用户

按 `Win + R`，输入 `cmd`，回车，然后复制粘贴：

```cmd
ssh root@你的服务器IP地址
```

提示输入密码时，输入您设置的密码（输入时不显示）。

#### 2.2 Mac 用户

打开终端，复制粘贴：

```bash
ssh root@你的服务器IP地址
```

---

### 第三步：更新系统并安装依赖

连接成功后，依次复制粘贴执行以下命令：

```bash
apt update && apt upgrade -y
```

等待完成，然后：

```bash
apt install -y python3.10 python3-pip python3-venv git curl
```

等待完成，然后验证：

```bash
python3.10 --version
```

应该显示：`Python 3.10.x`

---

### 第四步：下载项目代码

复制粘贴：

```bash
cd /opt
```

然后：

```bash
git clone https://github.com/your-repo/novel-rewriter.git
```

如果没有 git，使用 wget：

```bash
apt install -y wget unzip
wget https://github.com/your-repo/novel-rewriter/archive/main.zip
unzip main.zip
mv novel-rewriter-main novel-rewriter
```

进入项目目录：

```bash
cd novel-rewriter
```

---

### 第五步：运行一键安装脚本

复制粘贴：

```bash
bash install.sh
```

等待安装完成（约 15-30 分钟）。

如果提示权限不足，先执行：

```bash
chmod +x install.sh
```

然后再运行：

```bash
bash install.sh
```

---

### 第六步：配置 API 密钥

复制粘贴：

```bash
cp config/config.example.yaml config/config.yaml
```

编辑配置文件：

```bash
nano config/config.yaml
```

（如果 nano 不会用，可以用 vim：）

```bash
vim config/config.yaml
```

找到这一行：

```yaml
  api_key: "your-api-key-here"
```

把 `your-api-key-here` 替换为您的真实 API 密钥。

**nano 保存退出方法：**
1. 按 `Ctrl + O`（保存）
2. 按 `Enter`（确认）
3. 按 `Ctrl + X`（退出）

**vim 保存退出方法：**
1. 按 `Esc` 键
2. 输入 `:wq`
3. 按 `Enter`

---

### 第七步：启动服务

#### 方式 A：直接启动（测试用）

```bash
source venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

按 `Ctrl + C` 停止。

#### 方式 B：后台运行（推荐）

```bash
source venv/bin/activate
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

查看运行日志：

```bash
tail -f app.log
```

按 `Ctrl + C` 退出日志查看（服务仍在运行）。

---

### 第八步：访问系统

打开浏览器，访问：

```
http://你的服务器IP地址:8000/docs
```

看到 API 文档页面，说明安装成功！

---

### 第九步：配置系统服务（可选，推荐）

让服务开机自启：

```bash
sudo systemctl enable novel-rewriter
```

启动服务：

```bash
sudo systemctl start novel-rewriter
```

查看状态：

```bash
sudo systemctl status novel-rewriter
```

---

## 荣耀平板安装教程

> ⚠️ **重要提示**：荣耀平板本地部署较为复杂，强烈推荐使用**云端访问**方式

### 推荐方式：云端访问（最简单）

如果您已经在云服务器上部署了服务，直接在平板浏览器访问：

```
http://你的服务器IP地址:8000/docs
```

**优点：**
- 无需安装任何软件
- 不占用平板资源
- 随时随地访问

---

### 本地部署方式：使用 Termux

#### 第一步：安装 Termux

1. **关闭纯净模式**
   - 打开 **设置** → **系统和更新** → **纯净模式**
   - 关闭纯净模式

2. **下载 Termux**
   - 打开浏览器，访问：https://f-droid.org/packages/com.termux/
   - 下载最新版 APK
   - 安装时允许未知来源

3. **打开 Termux 应用**

---

#### 第二步：更新软件源

在 Termux 中复制粘贴：

```bash
pkg update
```

提示确认时输入 `Y`，回车。

---

#### 第三步：安装必要软件

复制粘贴：

```bash
pkg install -y python python-pip git clang pkg-config
```

等待安装完成（约 5-10 分钟）。

---

#### 第四步：下载项目代码

复制粘贴：

```bash
cd ~
```

然后：

```bash
git clone https://github.com/your-repo/novel-rewriter.git
```

如果没有 git，使用 wget：

```bash
pkg install -y wget unzip
wget https://github.com/your-repo/novel-rewriter/archive/main.zip
unzip main.zip
mv novel-rewriter-main novel-rewriter
```

进入项目目录：

```bash
cd novel-rewriter
```

---

#### 第五步：安装 Python 依赖

复制粘贴：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

⚠️ **如果安装失败（内存不足）**，尝试：

```bash
# 安装交换空间
pkg install -y swapspace

# 或使用预编译包
pip install -r requirements.txt --only-binary :all: -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

#### 第六步：配置 API 密钥

复制粘贴：

```bash
cp config/config.example.yaml config/config.yaml
```

编辑配置文件：

```bash
nano config/config.yaml
```

找到这一行：

```yaml
  api_key: "your-api-key-here"
```

替换为您的真实 API 密钥。

**保存退出：**
1. 按 `Ctrl + O`（保存）
2. 按 `Enter`（确认）
3. 按 `Ctrl + X`（退出）

---

#### 第七步：启动服务

复制粘贴：

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

#### 第八步：访问系统

在平板上打开浏览器，访问：

```
http://localhost:8000/docs
```

看到 API 文档页面，说明安装成功！

---

## 常见问题速查

### 问题 1：Windows 提示 'python' 不是内部命令

**解决：**

重新安装 Python，安装时**必须勾选** "Add Python to PATH"。

---

### 问题 2：pip 安装速度慢或超时

**解决：**

使用国内镜像源：

```bash
# Windows
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Linux/Mac
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 问题 3：提示 Microsoft Visual C++ 14.0 is required

**解决：**

使用预编译包，避免编译：

```bash
pip install -r requirements.txt --only-binary :all: -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 问题 4：云服务器无法连接

**解决：**

1. 登录云服务商控制台
2. 找到安全组配置
3. 添加规则：
   - 协议：SSH (22)
   - 授权对象：0.0.0.0/0

---

### 问题 5：平板 Termux 闪退

**解决：**

1. 关闭 HarmonyOS 纯净模式
2. 从 F-Droid 官网下载最新版 Termux
3. 授予所有必要权限

---

### 问题 6：平板安装时内存不足

**解决：**

```bash
# 安装交换空间
pkg install -y swapspace

# 然后重新安装依赖
pip install -r requirements.txt --only-binary :all:
```

---

## 验证安装成功

### 检查 1：Python 版本

```bash
python --version  # 应 >= 3.10
```

### 检查 2：依赖安装

```bash
pip list | grep fastapi  # 应显示 fastapi
```

### 检查 3：服务启动

浏览器访问 `http://localhost:8000/docs` 或 `http://服务器IP:8000/docs`

应看到 API 文档页面。

### 检查 4：运行测试

```bash
# Windows
python tests\test_e2e_shuihu.py

# Linux/Mac
python tests/test_e2e_shuihu.py
```

---

## 获取帮助

遇到问题？

1. 查看详细部署指南：`DEPLOYMENT_GUIDE.md`
2. 查看部署总结：`DEPLOYMENT_SUMMARY.md`
3. 开启调试模式：编辑 `config/config.yaml`，设置 `debug: true`
4. 查看日志文件：`data/output/` 目录

---

**最后更新**：2025-01-12