"""
钩子管理器 - 模块化架构的核心挂接机制

设计原则：
1. 松耦合：功能模块间通过钩子连接，不直接调用
2. 插件式：新功能只需注册钩子，无需修改核心代码
3. 优先级：支持钩子执行优先级管理
4. 事件驱动：基于事件触发钩子执行

架构参考：
- EasyUp的Agent间通信机制
- 现代Web框架的中间件/钩子设计
- 消息总线和事件系统融合
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Coroutine
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
import inspect

logger = logging.getLogger(__name__)


class HookPriority(Enum):
    """钩子执行优先级"""
    HIGHEST = 1000   # 最高优先级，最先执行
    HIGH = 750       # 高优先级
    NORMAL = 500     # 正常优先级（默认）
    LOW = 250        # 低优先级
    LOWEST = 0       # 最低优先级，最后执行


class HookType(Enum):
    """钩子类型"""
    BEFORE = "before"    # 前置钩子，在执行前触发
    AFTER = "after"      # 后置钩子，在执行后触发
    AROUND = "around"    # 环绕钩子，在执行前后都触发
    ERROR = "error"      # 错误处理钩子
    EVENT = "event"      # 事件钩子


@dataclass
class HookInfo:
    """钩子信息"""
    hook_id: str                    # 钩子ID
    name: str                       # 钩子名称
    callback: Callable              # 回调函数
    priority: HookPriority          # 执行优先级
    hook_type: HookType             # 钩子类型
    enabled: bool = True            # 是否启用
    description: Optional[str] = None  # 钩子描述
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def __str__(self) -> str:
        return f"HookInfo({self.name}, priority={self.priority.value}, type={self.hook_type.value})"


@dataclass
class HookContext:
    """钩子执行上下文"""
    hook_name: str                  # 钩子名称
    hook_id: str                    # 钩子ID
    start_time: datetime            # 开始时间
    end_time: Optional[datetime] = None  # 结束时间
    execution_time: Optional[float] = None  # 执行时间（秒）
    success: Optional[bool] = None  # 是否成功
    error: Optional[Exception] = None  # 错误信息
    return_value: Any = None        # 返回值
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def complete(self, success: bool = True, error: Optional[Exception] = None, 
                return_value: Any = None):
        """完成钩子执行"""
        self.end_time = datetime.now()
        self.execution_time = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error = error
        self.return_value = return_value


@dataclass
class HookExecutionResult:
    """钩子执行结果"""
    hook_id: str                    # 钩子ID
    hook_name: str                  # 钩子名称
    success: bool                   # 是否成功
    execution_time: float           # 执行时间
    return_value: Any               # 返回值
    error: Optional[str] = None     # 错误信息
    context: Optional[HookContext] = None  # 执行上下文


class HookManager:
    """钩子管理器（核心挂接机制）"""
    
    def __init__(self, name: str = "default"):
        """
        初始化钩子管理器
        
        Args:
            name: 管理器名称
        """
        self.name = name
        self.hooks: Dict[str, List[HookInfo]] = {}  # 钩子名称 -> 钩子列表
        self.execution_history: List[HookExecutionResult] = []
        self.hook_contexts: Dict[str, HookContext] = {}
        
        # 注册的钩子类型
        self._register_default_hooks()
        
        logger.info(f"钩子管理器初始化: {name}")
    
    def _register_default_hooks(self):
        """注册默认钩子"""
        # 系统启动钩子
        self.register_hook(
            name="system.startup",
            callback=self._log_startup,
            hook_type=HookType.BEFORE,
            priority=HookPriority.HIGHEST,
            description="系统启动钩子"
        )
        
        # 系统关闭钩子
        self.register_hook(
            name="system.shutdown",
            callback=self._log_shutdown,
            hook_type=HookType.AFTER,
            priority=HookPriority.LOWEST,
            description="系统关闭钩子"
        )
    
    def _log_startup(self, **kwargs):
        """系统启动日志"""
        logger.info(f"系统启动 - 钩子管理器: {self.name}")
    
    def _log_shutdown(self, **kwargs):
        """系统关闭日志"""
        logger.info(f"系统关闭 - 钩子管理器: {self.name}")
    
    def register_hook(self, name: str, callback: Callable, 
                     hook_type: HookType = HookType.EVENT,
                     priority: HookPriority = HookPriority.NORMAL,
                     enabled: bool = True,
                     description: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        注册钩子
        
        Args:
            name: 钩子名称
            callback: 回调函数
            hook_type: 钩子类型
            priority: 执行优先级
            enabled: 是否启用
            description: 钩子描述
            metadata: 元数据
            
        Returns:
            钩子ID
        """
        hook_id = str(uuid.uuid4())
        
        hook_info = HookInfo(
            hook_id=hook_id,
            name=name,
            callback=callback,
            priority=priority,
            hook_type=hook_type,
            enabled=enabled,
            description=description,
            metadata=metadata or {}
        )
        
        # 添加到钩子列表
        if name not in self.hooks:
            self.hooks[name] = []
        
        self.hooks[name].append(hook_info)
        
        # 按优先级排序（优先级高的先执行）
        self.hooks[name].sort(key=lambda x: x.priority.value, reverse=True)
        
        logger.debug(f"注册钩子: {name} (id={hook_id}, type={hook_type.value}, priority={priority.value})")
        
        return hook_id
    
    def unregister_hook(self, hook_id: str) -> bool:
        """
        取消注册钩子
        
        Args:
            hook_id: 钩子ID
            
        Returns:
            是否成功取消
        """
        for hook_name, hook_list in self.hooks.items():
            for i, hook_info in enumerate(hook_list):
                if hook_info.hook_id == hook_id:
                    del hook_list[i]
                    logger.debug(f"取消注册钩子: {hook_name} (id={hook_id})")
                    
                    # 如果钩子列表为空，删除整个键
                    if not hook_list:
                        del self.hooks[hook_name]
                    
                    return True
        
        logger.warning(f"未找到钩子: {hook_id}")
        return False
    
    def enable_hook(self, hook_id: str) -> bool:
        """启用钩子"""
        return self._set_hook_enabled(hook_id, True)
    
    def disable_hook(self, hook_id: str) -> bool:
        """禁用钩子"""
        return self._set_hook_enabled(hook_id, False)
    
    def _set_hook_enabled(self, hook_id: str, enabled: bool) -> bool:
        """设置钩子启用状态"""
        for hook_list in self.hooks.values():
            for hook_info in hook_list:
                if hook_info.hook_id == hook_id:
                    old_state = hook_info.enabled
                    hook_info.enabled = enabled
                    
                    state_text = "启用" if enabled else "禁用"
                    logger.debug(f"{state_text}钩子: {hook_info.name} (id={hook_id}, 旧状态: {old_state})")
                    return True
        
        logger.warning(f"未找到钩子: {hook_id}")
        return False
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[HookExecutionResult]:
        """
        执行钩子（同步）
        
        Args:
            hook_name: 钩子名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            执行结果列表
        """
        return self._execute_hooks(hook_name, False, *args, **kwargs)
    
    async def execute_hook_async(self, hook_name: str, *args, **kwargs) -> List[HookExecutionResult]:
        """
        执行钩子（异步）
        
        Args:
            hook_name: 钩子名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            执行结果列表
        """
        return await self._execute_hooks(hook_name, True, *args, **kwargs)
    
    def _execute_hooks(self, hook_name: str, is_async: bool, *args, **kwargs) -> Union[List[HookExecutionResult], Coroutine]:
        """
        执行钩子的内部方法
        
        Args:
            hook_name: 钩子名称
            is_async: 是否异步执行
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            执行结果列表或协程
        """
        if hook_name not in self.hooks:
            logger.debug(f"未注册的钩子: {hook_name}")
            return [] if not is_async else asyncio.sleep(0, result=[])
        
        hook_list = self.hooks[hook_name]
        enabled_hooks = [h for h in hook_list if h.enabled]
        
        if not enabled_hooks:
            logger.debug(f"钩子已注册但未启用: {hook_name}")
            return [] if not is_async else asyncio.sleep(0, result=[])
        
        logger.debug(f"执行钩子: {hook_name} (共{len(enabled_hooks)}个)")
        
        if is_async:
            return self._execute_hooks_async_internal(hook_name, enabled_hooks, *args, **kwargs)
        else:
            return self._execute_hooks_sync_internal(hook_name, enabled_hooks, *args, **kwargs)
    
    def _execute_hooks_sync_internal(self, hook_name: str, hook_list: List[HookInfo], 
                                    *args, **kwargs) -> List[HookExecutionResult]:
        """同步执行钩子的内部实现"""
        results = []
        
        for hook_info in hook_list:
            hook_id = hook_info.hook_id
            
            # 创建执行上下文
            context = HookContext(
                hook_name=hook_name,
                hook_id=hook_id,
                start_time=datetime.now()
            )
            self.hook_contexts[hook_id] = context
            
            try:
                # 执行钩子
                return_value = hook_info.callback(*args, **kwargs)
                
                # 记录成功结果
                context.complete(success=True, return_value=return_value)
                
                result = HookExecutionResult(
                    hook_id=hook_id,
                    hook_name=hook_name,
                    success=True,
                    execution_time=context.execution_time,
                    return_value=return_value,
                    context=context
                )
                
                results.append(result)
                
                logger.debug(f"钩子执行成功: {hook_name} (id={hook_id}, 时间={context.execution_time:.3f}s)")
                
            except Exception as e:
                # 记录失败结果
                context.complete(success=False, error=e)
                
                result = HookExecutionResult(
                    hook_id=hook_id,
                    hook_name=hook_name,
                    success=False,
                    execution_time=context.execution_time or 0,
                    return_value=None,
                    error=str(e),
                    context=context
                )
                
                results.append(result)
                
                logger.error(f"钩子执行失败: {hook_name} (id={hook_id}) - {str(e)}")
                
                # 触发错误钩子
                self.execute_hook("hook.error", hook_info=hook_info, error=e, args=args, kwargs=kwargs)
        
        return results
    
    async def _execute_hooks_async_internal(self, hook_name: str, hook_list: List[HookInfo], 
                                           *args, **kwargs) -> List[HookExecutionResult]:
        """异步执行钩子的内部实现"""
        results = []
        
        for hook_info in hook_list:
            hook_id = hook_info.hook_id
            
            # 创建执行上下文
            context = HookContext(
                hook_name=hook_name,
                hook_id=hook_id,
                start_time=datetime.now()
            )
            self.hook_contexts[hook_id] = context
            
            try:
                # 检查回调函数是否为协程
                if inspect.iscoroutinefunction(hook_info.callback):
                    return_value = await hook_info.callback(*args, **kwargs)
                else:
                    # 同步函数在异步环境中执行
                    return_value = hook_info.callback(*args, **kwargs)
                
                # 记录成功结果
                context.complete(success=True, return_value=return_value)
                
                result = HookExecutionResult(
                    hook_id=hook_id,
                    hook_name=hook_name,
                    success=True,
                    execution_time=context.execution_time,
                    return_value=return_value,
                    context=context
                )
                
                results.append(result)
                
                logger.debug(f"钩子异步执行成功: {hook_name} (id={hook_id}, 时间={context.execution_time:.3f}s)")
                
            except Exception as e:
                # 记录失败结果
                context.complete(success=False, error=e)
                
                result = HookExecutionResult(
                    hook_id=hook_id,
                    hook_name=hook_name,
                    success=False,
                    execution_time=context.execution_time or 0,
                    return_value=None,
                    error=str(e),
                    context=context
                )
                
                results.append(result)
                
                logger.error(f"钩子异步执行失败: {hook_name} (id={hook_id}) - {str(e)}")
                
                # 触发错误钩子
                await self.execute_hook_async("hook.error", hook_info=hook_info, error=e, args=args, kwargs=kwargs)
        
        return results
    
    def register_hook_decorator(self, name: str, 
                               hook_type: HookType = HookType.EVENT,
                               priority: HookPriority = HookPriority.NORMAL,
                               enabled: bool = True,
                               description: Optional[str] = None):
        """
        钩子装饰器
        
        Args:
            name: 钩子名称
            hook_type: 钩子类型
            priority: 执行优先级
            enabled: 是否启用
            description: 钩子描述
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            self.register_hook(
                name=name,
                callback=func,
                hook_type=hook_type,
                priority=priority,
                enabled=enabled,
                description=description
            )
            return func
        
        return decorator
    
    def get_hook_info(self, hook_name: str) -> List[HookInfo]:
        """获取钩子信息"""
        return self.hooks.get(hook_name, [])
    
    def get_all_hooks(self) -> Dict[str, List[HookInfo]]:
        """获取所有钩子"""
        return self.hooks.copy()
    
    def clear_hooks(self, hook_name: str = None):
        """清除钩子"""
        if hook_name is None:
            # 清除所有钩子
            self.hooks.clear()
            logger.info("清除所有钩子")
        elif hook_name in self.hooks:
            # 清除特定钩子
            del self.hooks[hook_name]
            logger.info(f"清除钩子: {hook_name}")
        else:
            logger.warning(f"未找到钩子: {hook_name}")
    
    def get_execution_history(self, limit: int = 100) -> List[HookExecutionResult]:
        """获取执行历史"""
        return self.execution_history[-limit:] if self.execution_history else []
    
    def get_hook_stats(self) -> Dict[str, Any]:
        """获取钩子统计信息"""
        total_hooks = sum(len(hook_list) for hook_list in self.hooks.values())
        enabled_hooks = sum(len([h for h in hook_list if h.enabled]) for hook_list in self.hooks.values())
        
        # 按类型统计
        type_stats = {}
        for hook_list in self.hooks.values():
            for hook_info in hook_list:
                hook_type = hook_info.hook_type.value
                type_stats[hook_type] = type_stats.get(hook_type, 0) + 1
        
        return {
            "total_hooks": total_hooks,
            "enabled_hooks": enabled_hooks,
            "disabled_hooks": total_hooks - enabled_hooks,
            "hook_types": len(self.hooks),
            "type_distribution": type_stats,
            "execution_count": len(self.execution_history)
        }


class HookRegistry:
    """钩子注册表（全局单例）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.hook_managers: Dict[str, HookManager] = {}
            self.default_manager_name = "global"
            self._initialized = True
            
            # 创建默认钩子管理器
            self.get_manager(self.default_manager_name)
    
    def get_manager(self, name: str = None) -> HookManager:
        """
        获取钩子管理器
        
        Args:
            name: 管理器名称，为None时返回默认管理器
            
        Returns:
            钩子管理器实例
        """
        if name is None:
            name = self.default_manager_name
        
        if name not in self.hook_managers:
            self.hook_managers[name] = HookManager(name)
        
        return self.hook_managers[name]
    
    def register_hook(self, name: str, callback: Callable, 
                     manager_name: str = None, **kwargs) -> str:
        """
        注册钩子（便捷方法）
        
        Args:
            name: 钩子名称
            callback: 回调函数
            manager_name: 管理器名称
            **kwargs: 传递给register_hook的其他参数
            
        Returns:
            钩子ID
        """
        manager = self.get_manager(manager_name)
        return manager.register_hook(name, callback, **kwargs)
    
    def execute_hook(self, name: str, manager_name: str = None, *args, **kwargs) -> List[HookExecutionResult]:
        """
        执行钩子（便捷方法）
        
        Args:
            name: 钩子名称
            manager_name: 管理器名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            执行结果列表
        """
        manager = self.get_manager(manager_name)
        return manager.execute_hook(name, *args, **kwargs)
    
    async def execute_hook_async(self, name: str, manager_name: str = None, *args, **kwargs) -> List[HookExecutionResult]:
        """
        异步执行钩子（便捷方法）
        
        Args:
            name: 钩子名称
            manager_name: 管理器名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            执行结果列表
        """
        manager = self.get_manager(manager_name)
        return await manager.execute_hook_async(name, *args, **kwargs)


# 创建全局钩子注册表实例
hook_registry = HookRegistry()


# 便捷装饰器函数
def hook(name: str, manager_name: str = None, **kwargs):
    """
    钩子装饰器（全局）
    
    Args:
        name: 钩子名称
        manager_name: 管理器名称
        **kwargs: 传递给register_hook的其他参数
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        hook_registry.register_hook(name, func, manager_name, **kwargs)
        return func
    
    return decorator