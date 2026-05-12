"""
任务调度器

负责任务的调度、暂停、恢复和状态管理。
"""

import asyncio
import logging
from typing import Any, Callable, Optional

from backend.models.enums import TaskStatus
from backend.models.schemas import TaskState

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        """初始化任务调度器"""
        self._tasks: dict[str, TaskState] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._pause_events: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def create_task(
        self,
        task_id: str,
        total_chapters: int = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> TaskState:
        """
        创建新任务。

        Args:
            task_id: 任务ID
            total_chapters: 总章数
            metadata: 元数据

        Returns:
            TaskState: 任务状态
        """
        async with self._lock:
            state = TaskState(
                task_id=task_id,
                status=TaskStatus.PENDING,
                total_chapters=total_chapters,
            )
            self._tasks[task_id] = state
            self._cancel_events[task_id] = asyncio.Event()
            self._pause_events[task_id] = asyncio.Event()
            self._pause_events[task_id].set()  # 默认不暂停

            logger.info(f"任务创建: {task_id}")
            return state

    async def start_task(
        self,
        task_id: str,
        worker: Callable,
        **kwargs: Any,
    ) -> None:
        """
        启动任务。

        Args:
            task_id: 任务ID
            worker: 工作函数（async callable）
            **kwargs: 传递给工作函数的参数
        """
        if task_id not in self._tasks:
            raise ValueError(f"任务不存在: {task_id}")

        state = self._tasks[task_id]
        state.status = TaskStatus.GENERATING

        try:
            await worker(
                task_state=state,
                cancel_event=self._cancel_events[task_id],
                pause_event=self._pause_events[task_id],
                **kwargs,
            )
            if state.status != TaskStatus.CANCELLED:
                state.status = TaskStatus.COMPLETED
                logger.info(f"任务完成: {task_id}")
        except Exception as e:
            state.status = TaskStatus.FAILED
            state.error_message = str(e)
            logger.error(f"任务失败: {task_id}, 错误: {e}")

    async def pause_task(self, task_id: str) -> bool:
        """
        暂停任务。

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功暂停
        """
        if task_id not in self._tasks:
            return False

        state = self._tasks[task_id]
        if state.status != TaskStatus.GENERATING:
            return False

        state.status = TaskStatus.PAUSED
        self._pause_events[task_id].clear()
        logger.info(f"任务暂停: {task_id}")
        return True

    async def resume_task(self, task_id: str) -> bool:
        """
        恢复任务。

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功恢复
        """
        if task_id not in self._tasks:
            return False

        state = self._tasks[task_id]
        if state.status != TaskStatus.PAUSED:
            return False

        state.status = TaskStatus.GENERATING
        self._pause_events[task_id].set()
        logger.info(f"任务恢复: {task_id}")
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务。

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        if task_id not in self._tasks:
            return False

        state = self._tasks[task_id]
        state.status = TaskStatus.CANCELLED
        self._cancel_events[task_id].set()
        self._pause_events[task_id].set()  # 解除暂停以允许退出
        logger.info(f"任务取消: {task_id}")
        return True

    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskState]:
        """列出所有任务"""
        return list(self._tasks.values())

    async def wait_for_resume(self, task_id: str, timeout: float = 1.0) -> bool:
        """
        等待任务恢复（用于工作函数中检测暂停）。

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Returns:
            bool: True表示已恢复，False表示已取消
        """
        if task_id not in self._pause_events:
            return False

        # 检查是否已取消
        if self._cancel_events[task_id].is_set():
            return False

        try:
            await asyncio.wait_for(
                self._pause_events[task_id].wait(),
                timeout=timeout,
            )
            return not self._cancel_events[task_id].is_set()
        except asyncio.TimeoutError:
            return True  # 超时但未取消，继续检查

    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否已取消"""
        if task_id not in self._cancel_events:
            return False
        return self._cancel_events[task_id].is_set()

    async def cleanup_task(self, task_id: str) -> None:
        """清理已完成的任务"""
        async with self._lock:
            self._tasks.pop(task_id, None)
            self._cancel_events.pop(task_id, None)
            self._pause_events.pop(task_id, None)
            logger.info(f"任务清理: {task_id}")
