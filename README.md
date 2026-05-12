# 仿写百万字小说软件

基于AI的长篇小说仿写工具，支持百万字级别的自动化小说创作。

## 技术栈

- **后端**: Python 3.10+ / FastAPI
- **AI调用**: DeepSeek API (默认) / OpenAI兼容接口
- **CLI前端**: Node.js / commander / inquirer / chalk
- **数据存储**: SQLite + JSON文件

## 项目结构

```
novel-rewriter/
├── config/                 # 配置文件
│   ├── config.yaml         # 主配置
│   └── config.example.yaml # 配置示例
├── backend/                # Python后端
│   ├── main.py             # FastAPI入口
│   ├── config.py           # 配置加载
│   ├── models/             # 数据模型
│   │   ├── schemas.py      # Pydantic模型
│   │   └── enums.py        # 枚举类型
│   ├── services/           # 业务服务
│   │   ├── llm_client.py   # LLM调用客户端
│   │   ├── parser.py       # 文本解析
│   │   ├── world_builder.py# 世界观构建
│   │   ├── writer.py       # 写作引擎
│   │   ├── context_mgr.py  # 上下文管理
│   │   ├── chapter_ctrl.py # 章节控制
│   │   ├── deai.py         # 去AI化
│   │   └── copyright.py    # 版权检测
│   ├── prompts/            # 提示词
│   │   ├── system_prompts.py
│   │   ├── task_prompts.py
│   │   ├── chapter_prompts.py
│   │   └── paragraph_prompts.py
│   ├── core/               # 核心模块
│   │   ├── pipeline.py     # 主流水线
│   │   ├── task_scheduler.py
│   │   └── quality_checker.py
│   └── utils/              # 工具函数
├── cli/                    # Node.js CLI
│   ├── index.js
│   ├── commands/
│   └── utils/
├── data/                   # 数据目录
│   ├── templates/
│   └── output/
└── tests/                  # 测试
```

## 快速开始

### 一键安装 (推荐)

**Windows 用户:**
```cmd
double-click install.bat
```

**Linux/macOS 用户:**
```bash
bash install.sh
```

**Python 安装脚本 (跨平台):**
```bash
python install.py
```

### 手动安装

#### 1. 安装Python依赖

```bash
cd novel-rewriter
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 2. 配置API密钥

```bash
# Windows
copy config\config.example.yaml config\config.yaml
notepad config\config.yaml

# Linux/macOS
cp config/config.example.yaml config/config.yaml
vim config/config.yaml
```

编辑 `config.yaml`，填入你的 API 密钥：
```yaml
llm:
  provider: deepseek  # 或 openai
  api_key: "your-api-key-here"
```

#### 3. 启动后端服务

```bash
# 方式1: 直接启动
python -m uvicorn backend.main:app --reload

# 方式2: 使用虚拟环境 (推荐)
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

python -m uvicorn backend.main:app --reload
```

#### 4. 使用CLI（可选）

```bash
# 安装 Node.js 依赖
npm install

# 使用 CLI
node cli/index.js start    # 开始仿写
node cli/index.js status   # 查看状态
node cli/index.js export   # 导出小说
```

## 部署指南

详细部署文档请参考 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)，包含以下平台的详细步骤：

- **Windows 电脑** - 完整的图形界面安装教程
- **云服务器** (阿里云/腾讯云/华为云) - 生产环境部署
- **荣耀平板** - 通过 Termux 安装或使用云端服务

### 系统要求

| 平台 | 最低配置 | 推荐配置 |
|------|---------|---------|
| Windows | Win10 64位, 4GB内存 | Win11 64位, 8GB内存 |
| 云服务器 | 2核2G, 20GB硬盘 | 2核4G, 50GB硬盘 |
| 平板 | HarmonyOS 3.0+, 6GB内存 | HarmonyOS 4.0+, 8GB内存 |

### 必需软件

- **Python 3.10+** (后端运行环境)
- **Node.js 18+** (CLI前端，可选)
- **Git** (代码下载，可选)

## 核心功能

- **LLM调用**: 支持DeepSeek和OpenAI兼容接口，含成本控制和自动降级
- **世界观构建**: 自动生成地理、历史、社会、文化、力量体系
- **章节生成**: 大纲生成 -> 正文生成 -> 续写 -> 修改
- **质量检查**: 多维度质量评估（连贯性、角色一致性、情节逻辑、语言质量）
- **去AI化**: 检测和消除AI生成痕迹
- **版权检测**: N-gram相似度、句子级和段落级相似度检测
- **上下文管理**: 自动维护前文摘要、角色状态、伏笔追踪

## 配置说明

主要配置项在 `config/config.yaml` 中：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| llm.provider | LLM提供商 | deepseek |
| llm.model | 模型名称 | deepseek-chat |
| llm.temperature | 生成温度 | 0.8 |
| llm.cost.chapter_budget | 每章预算上限(元) | 0.5 |
| novel.default_genre | 默认小说类型 | 玄幻 |
| writing.deai_enabled | 去AI化开关 | true |
| writing.quality_check | 质量检查开关 | true |

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /api/config | 获取配置 |
| POST | /api/rewrite/start | 开始仿写 |
| GET | /api/rewrite/{id}/status | 查询状态 |
| POST | /api/rewrite/{id}/pause | 暂停任务 |
| POST | /api/rewrite/{id}/resume | 恢复任务 |
| POST | /api/export | 导出小说 |

## License

MIT
