"""
FastAPI 应用入口

提供REST API接口，用于控制小说仿写流程。
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 将项目根目录加入Python路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import load_config, get_config


# ============================================================
# 生命周期管理
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时加载配置
    load_config()
    config = get_config()
    print(f"[NovelRewriter] 服务启动 - 监听 {config.server.host}:{config.server.port}")
    print(f"[NovelRewriter] LLM提供商: {config.llm.provider}, 模型: {config.llm.model}")
    yield
    # 关闭时清理资源
    print("[NovelRewriter] 服务关闭")


# ============================================================
# FastAPI 应用实例
# ============================================================

app = FastAPI(
    title="仿写百万字小说软件",
    description="基于AI的长篇小说仿写工具API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API响应模型
# ============================================================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    llm_provider: str
    llm_model: str


class StartRewriteRequest(BaseModel):
    """开始仿写请求"""
    source_novel_path: str = ""
    genre: str = "玄幻"
    total_chapters: int = 300
    chapter_words: int = 3000
    novel_name: str = ""
    novel_description: str = ""


class StartRewriteResponse(BaseModel):
    """开始仿写响应"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    current_chapter: int
    total_chapters: int
    estimated_cost: float
    actual_cost: float


class ExportRequest(BaseModel):
    """导出请求"""
    task_id: str
    format: str = "txt"
    output_path: str = ""


# ============================================================
# API路由
# ============================================================

@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查"""
    config = get_config()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        llm_provider=config.llm.provider,
        llm_model=config.llm.model,
    )


@app.get("/api/config", tags=["配置"])
async def get_api_config():
    """获取当前配置（隐藏敏感信息）"""
    config = get_config()
    return {
        "llm": {
            "provider": config.llm.provider,
            "base_url": config.llm.base_url,
            "model": config.llm.model,
            "max_tokens_per_call": config.llm.max_tokens_per_call,
            "temperature": config.llm.temperature,
            "top_p": config.llm.top_p,
            "stream": config.llm.stream,
            "cost": config.llm.cost.model_dump(),
        },
        "novel": config.novel.model_dump(),
        "writing": config.writing.model_dump(),
        "output": config.output.model_dump(),
    }


@app.post("/api/rewrite/start", response_model=StartRewriteResponse, tags=["仿写"])
async def start_rewrite(request: StartRewriteRequest):
    """
    开始仿写任务

    启动一个新的小说仿写任务，返回任务ID用于后续状态查询。
    """
    import uuid
    task_id = str(uuid.uuid4())[:8]

    # TODO: 实际启动仿写流水线
    # from backend.core.pipeline import NovelPipeline
    # pipeline = NovelPipeline(task_id=task_id, config=request)
    # await pipeline.run()

    return StartRewriteResponse(
        task_id=task_id,
        status="pending",
        message=f"仿写任务已创建，任务ID: {task_id}",
    )


@app.get("/api/rewrite/{task_id}/status", response_model=TaskStatusResponse, tags=["仿写"])
async def get_task_status(task_id: str):
    """查询仿写任务状态"""
    # TODO: 从数据库或内存中查询实际任务状态
    return TaskStatusResponse(
        task_id=task_id,
        status="pending",
        progress=0.0,
        current_chapter=0,
        total_chapters=0,
        estimated_cost=0.0,
        actual_cost=0.0,
    )


@app.post("/api/rewrite/{task_id}/pause", tags=["仿写"])
async def pause_task(task_id: str):
    """暂停仿写任务"""
    # TODO: 实现暂停逻辑
    return {"task_id": task_id, "status": "paused", "message": "任务已暂停"}


@app.post("/api/rewrite/{task_id}/resume", tags=["仿写"])
async def resume_task(task_id: str):
    """恢复仿写任务"""
    # TODO: 实现恢复逻辑
    return {"task_id": task_id, "status": "running", "message": "任务已恢复"}


@app.post("/api/export", tags=["导出"])
async def export_novel(request: ExportRequest):
    """导出小说"""
    # TODO: 实现导出逻辑
    return {
        "task_id": request.task_id,
        "format": request.format,
        "status": "pending",
        "message": "导出任务已提交",
    }


@app.get("/api/genres", tags=["配置"])
async def get_genres():
    """获取支持的小说类型列表"""
    config = get_config()
    return {"genres": config.novel.genres}


# ============================================================
# 启动入口
# ============================================================

def main():
    """命令行启动入口"""
    import uvicorn
    config = load_config()
    uvicorn.run(
        "backend.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
    )


if __name__ == "__main__":
    main()
