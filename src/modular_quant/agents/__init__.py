"""
Agent协调层 - 基于EasyUp的多Agent通信架构设计

设计原则：
1. 微服务化：每个Agent独立运行，职责单一
2. 事件驱动：Agent间通过消息总线通信
3. 容错机制：Agent异常不影响其他Agent运行
4. 水平扩展：支持多个同类Agent并行工作

架构参考：
- EasyUp的Agent驱动量化系统
- 微服务架构和事件驱动设计
- 企业级系统的高可用设计
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Coroutine
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
import threading
import queue
import json
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent状态枚举"""
    INITIALIZING = "initializing"   # 初始化中
    READY = "ready"                 # 就绪
    RUNNING = "running"             # 运行中
    STOPPING = "stopping"           # 停止中
    STOPPED = "stopped"             # 已停止
    ERROR = "error"                 # 错误状态


class AgentType(Enum):
    """Agent类型枚举"""
    DATA_COLLECTOR = "data_collector"   # 数据收集Agent
    DATA_PROCESSOR = "data_processor"   # 数据处理Agent
    STRATEGY_ANALYZER = "strategy_analyzer"  # 策略分析Agent
    RISK_MANAGER = "risk_manager"       # 风控管理Agent
    BACKTEST_ENGINE = "backtest_engine" # 回测引擎Agent
    REPORT_GENERATOR = "report_generator" # 报告生成Agent
    NOTIFICATION = "notification"       # 通知Agent
    SYSTEM_MONITOR = "system_monitor"   # 系统监控Agent
    CUSTOM = "custom"                   # 自定义Agent


@dataclass
class AgentConfig:
    """Agent配置"""
    agent_id: str                     # Agent ID
    agent_name: str                   # Agent名称
    agent_type: AgentType             # Agent类型
    enabled: bool = True              # 是否启用
    priority: int = 50                # 优先级（0-100）
    health_check_interval: int = 30   # 健康检查间隔（秒）
    max_retries: int = 3              # 最大重试次数
    retry_delay: int = 5              # 重试延迟（秒）
    timeout: int = 60                 # 操作超时时间（秒）
    resource_limits: Dict[str, Any] = field(default_factory=dict)  # 资源限制
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class AgentMessage:
    """Agent间消息"""
    message_id: str                    # 消息ID
    sender: str                       # 发送者Agent ID
    receiver: str                     # 接收者Agent ID
    message_type: str                 # 消息类型
    timestamp: datetime = field(default_factory=datetime.now)
    payload: Dict[str, Any] = field(default_factory=dict)  # 消息负载
    correlation_id: Optional[str] = None  # 关联ID（用于请求-响应）
    priority: int = 50                # 消息优先级（0-100）
    ttl: int = 3600                   # 消息存活时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
            "ttl": self.ttl,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建"""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            sender=data["sender"],
            receiver=data["receiver"],
            message_type=data["message_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id"),
            priority=data.get("priority", 50),
            ttl=data.get("ttl", 3600),
            metadata=data.get("metadata", {})
        )


class MessageBus:
    """消息总线（Agent间通信核心）"""
    
    def __init__(self, name: str = "default"):
        """
        初始化消息总线
        
        Args:
            name: 总线名称
        """
        self.name = name
        self.queues: Dict[str, queue.PriorityQueue] = {}  # Agent ID -> 消息队列
        self.subscribers: Dict[str, List[str]] = {}  # 消息类型 -> 订阅者列表
        self.routing_table: Dict[str, str] = {}  # Agent ID -> 队列名称
        self.dead_letter_queue = queue.Queue()  # 死信队列
        
        # 线程池和锁
        self._lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix=f"msg_bus_{name}")
        
        # 统计信息
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "active_queues": 0,
            "active_subscribers": 0
        }
        
        logger.info(f"消息总线初始化: {name}")
    
    def start(self):
        """启动消息总线"""
        logger.info(f"消息总线启动: {self.name}")
        # 消息总线在初始化时已自动启动，这里只是记录日志
        return True
    
    def stop(self):
        """停止消息总线"""
        logger.info(f"消息总线停止: {self.name}")
        # 清理资源
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        logger.info(f"消息总线已停止: {self.name}")
        return True
    
    def register_agent(self, agent_id: str, queue_size: int = 1000) -> bool:
        """
        注册Agent到消息总线
        
        Args:
            agent_id: Agent ID
            queue_size: 消息队列大小
            
        Returns:
            是否注册成功
        """
        with self._lock:
            if agent_id in self.queues:
                logger.warning(f"Agent已注册: {agent_id}")
                return False
            
            # 创建优先级队列
            self.queues[agent_id] = queue.PriorityQueue(maxsize=queue_size)
            self.routing_table[agent_id] = agent_id
            
            self.stats["active_queues"] += 1
            logger.debug(f"Agent注册成功: {agent_id}")
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """取消注册Agent"""
        with self._lock:
            if agent_id not in self.queues:
                logger.warning(f"Agent未注册: {agent_id}")
                return False
            
            # 从订阅者列表中移除
            for msg_type in list(self.subscribers.keys()):
                if agent_id in self.subscribers[msg_type]:
                    self.subscribers[msg_type].remove(agent_id)
                    if not self.subscribers[msg_type]:
                        del self.subscribers[msg_type]
            
            # 清空队列并移除
            try:
                while not self.queues[agent_id].empty():
                    self.queues[agent_id].get_nowait()
            except queue.Empty:
                pass
            
            del self.queues[agent_id]
            del self.routing_table[agent_id]
            
            self.stats["active_queues"] -= 1
            logger.debug(f"Agent取消注册: {agent_id}")
            return True
    
    def subscribe(self, agent_id: str, message_types: Union[str, List[str]]) -> bool:
        """
        Agent订阅消息类型
        
        Args:
            agent_id: Agent ID
            message_types: 消息类型或类型列表
            
        Returns:
            是否订阅成功
        """
        with self._lock:
            if agent_id not in self.queues:
                logger.error(f"Agent未注册，无法订阅: {agent_id}")
                return False
            
            if isinstance(message_types, str):
                message_types = [message_types]
            
            for msg_type in message_types:
                if msg_type not in self.subscribers:
                    self.subscribers[msg_type] = []
                
                if agent_id not in self.subscribers[msg_type]:
                    self.subscribers[msg_type].append(agent_id)
                    self.stats["active_subscribers"] += 1
                    logger.debug(f"Agent订阅消息类型: {agent_id} -> {msg_type}")
            
            return True
    
    def unsubscribe(self, agent_id: str, message_types: Union[str, List[str]]) -> bool:
        """取消订阅消息类型"""
        with self._lock:
            if isinstance(message_types, str):
                message_types = [message_types]
            
            for msg_type in message_types:
                if msg_type in self.subscribers and agent_id in self.subscribers[msg_type]:
                    self.subscribers[msg_type].remove(agent_id)
                    self.stats["active_subscribers"] -= 1
                    
                    # 如果该消息类型没有订阅者了，删除条目
                    if not self.subscribers[msg_type]:
                        del self.subscribers[msg_type]
                    
                    logger.debug(f"Agent取消订阅: {agent_id} -> {msg_type}")
            
            return True
    
    def publish(self, message: AgentMessage) -> bool:
        """
        发布消息到消息总线
        
        Args:
            message: Agent消息
            
        Returns:
            是否发布成功
        """
        try:
            with self._lock:
                # 查找订阅者
                receivers = []
                
                # 如果有指定接收者，直接发送给该接收者
                if message.receiver:
                    if message.receiver in self.queues:
                        receivers.append(message.receiver)
                    else:
                        logger.error(f"接收者未注册: {message.receiver}")
                        return False
                else:
                    # 广播给所有订阅该消息类型的Agent
                    if message.message_type in self.subscribers:
                        receivers = self.subscribers[message.message_type].copy()
                    else:
                        logger.debug(f"无订阅者，消息被丢弃: {message.message_type}")
                        return False
                
                # 发送消息给所有接收者
                sent_count = 0
                for receiver_id in receivers:
                    if receiver_id in self.queues:
                        try:
                            # 使用优先级队列，优先级高的消息先处理
                            # 优先级反转：priority值越小优先级越高
                            priority = 100 - message.priority if 0 <= message.priority <= 100 else 50
                            self.queues[receiver_id].put((priority, message.message_id, message), timeout=1)
                            sent_count += 1
                        except queue.Full:
                            logger.warning(f"Agent消息队列已满，消息被丢弃: {receiver_id}")
                            self._send_to_dead_letter(message, "queue_full")
                
                self.stats["messages_sent"] += sent_count
                
                if sent_count > 0:
                    logger.debug(f"消息发布成功: {message.message_type} -> {sent_count}个接收者")
                    return True
                else:
                    logger.warning(f"消息无接收者: {message.message_type}")
                    return False
                    
        except Exception as e:
            logger.error(f"发布消息失败: {str(e)}")
            self.stats["messages_failed"] += 1
            self._send_to_dead_letter(message, str(e))
            return False
    
    def request_response(self, request_msg: AgentMessage, timeout: int = 30) -> Optional[AgentMessage]:
        """
        发送请求并等待响应
        
        Args:
            request_msg: 请求消息
            timeout: 超时时间（秒）
            
        Returns:
            响应消息或None
        """
        if not request_msg.correlation_id:
            request_msg.correlation_id = str(uuid.uuid4())
        
        # 创建响应队列
        response_queue = queue.Queue()
        
        # 订阅响应消息
        response_type = f"{request_msg.message_type}.response"
        response_filter = {"correlation_id": request_msg.correlation_id}
        
        # 临时订阅响应
        temp_subscriber_id = f"temp_{request_msg.correlation_id}"
        self.register_agent(temp_subscriber_id, queue_size=10)
        self.subscribe(temp_subscriber_id, response_type)
        
        try:
            # 发送请求
            if not self.publish(request_msg):
                return None
            
            # 等待响应
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < timeout:
                try:
                    # 检查响应队列
                    _, _, message = self.queues[temp_subscriber_id].get(timeout=1)
                    
                    # 检查消息类型和关联ID
                    if (message.message_type == response_type and 
                        message.correlation_id == request_msg.correlation_id):
                        
                        logger.debug(f"收到响应: {request_msg.message_type}")
                        return message
                    
                except queue.Empty:
                    continue
                
            logger.warning(f"请求超时: {request_msg.message_type}")
            return None
            
        finally:
            # 清理临时订阅
            self.unsubscribe(temp_subscriber_id, response_type)
            self.unregister_agent(temp_subscriber_id)
    
    def receive(self, agent_id: str, timeout: int = 1) -> Optional[AgentMessage]:
        """
        接收消息（阻塞模式）
        
        Args:
            agent_id: Agent ID
            timeout: 超时时间（秒）
            
        Returns:
            消息或None（超时）
        """
        if agent_id not in self.queues:
            logger.error(f"Agent未注册: {agent_id}")
            return None
        
        try:
            # 从优先级队列获取消息
            _, _, message = self.queues[agent_id].get(timeout=timeout)
            
            self.stats["messages_received"] += 1
            logger.debug(f"Agent收到消息: {agent_id} -> {message.message_type}")
            
            return message
            
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"接收消息失败: {agent_id} - {str(e)}")
            return None
    
    def receive_non_blocking(self, agent_id: str) -> Optional[AgentMessage]:
        """非阻塞接收消息"""
        if agent_id not in self.queues:
            return None
        
        try:
            _, _, message = self.queues[agent_id].get_nowait()
            
            self.stats["messages_received"] += 1
            logger.debug(f"Agent收到消息(非阻塞): {agent_id} -> {message.message_type}")
            
            return message
            
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"非阻塞接收消息失败: {agent_id} - {str(e)}")
            return None
    
    def _send_to_dead_letter(self, message: AgentMessage, reason: str):
        """发送消息到死信队列"""
        try:
            dead_message = {
                "original_message": message.to_dict(),
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            self.dead_letter_queue.put(dead_message)
            logger.warning(f"消息发送到死信队列: {message.message_type} - {reason}")
        except Exception as e:
            logger.error(f"发送到死信队列失败: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self.stats.copy()
            
            # 添加队列信息
            stats["queue_sizes"] = {}
            for agent_id, q in self.queues.items():
                stats["queue_sizes"][agent_id] = q.qsize()
            
            stats["subscriber_counts"] = {}
            for msg_type, subscribers in self.subscribers.items():
                stats["subscriber_counts"][msg_type] = len(subscribers)
            
            return stats
    
    def clear_stats(self):
        """清除统计信息"""
        with self._lock:
            self.stats = {
                "messages_sent": 0,
                "messages_received": 0,
                "messages_failed": 0,
                "active_queues": 0,
                "active_subscribers": 0
            }
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        with self._lock:
            return {
                "name": self.name,
                "status": "healthy",
                "active_agents": len(self.queues),
                "active_subscriptions": len(self.subscribers),
                "total_queued_messages": sum(q.qsize() for q in self.queues.values()),
                "dead_letter_count": self.dead_letter_queue.qsize(),
                "timestamp": datetime.now().isoformat()
            }


class BaseAgent:
    """Agent基类"""
    
    def __init__(self, agent_id: str, agent_name: str, agent_type: AgentType, 
                 message_bus: MessageBus, config: Optional[Dict[str, Any]] = None):
        """
        初始化Agent
        
        Args:
            agent_id: Agent ID
            agent_name: Agent名称
            agent_type: Agent类型
            message_bus: 消息总线实例
            config: 配置字典
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.message_bus = message_bus
        self.config = config or {}
        
        # 状态管理
        self.status = AgentStatus.INITIALIZING
        self.last_heartbeat = datetime.now()
        self.error_count = 0
        self.message_count = 0
        
        # 钩子管理器引用
        self.hook_manager = None
        
        # 线程和事件
        self._running = False
        self._stop_event = threading.Event()
        self._thread = None
        
        # 注册到消息总线
        self._register_to_bus()
        
        logger.info(f"Agent初始化: {self.agent_name} ({self.agent_id})")
    
    def _register_to_bus(self):
        """注册到消息总线"""
        try:
            self.message_bus.register_agent(self.agent_id)
            logger.debug(f"Agent注册到消息总线: {self.agent_id}")
        except Exception as e:
            logger.error(f"注册到消息总线失败: {self.agent_id} - {str(e)}")
            raise
    
    def set_hook_manager(self, hook_manager):
        """设置钩子管理器"""
        self.hook_manager = hook_manager
        logger.debug(f"Agent设置钩子管理器: {self.agent_id}")
    
    def initialize(self) -> bool:
        """
        初始化Agent（子类必须实现）
        
        Returns:
            是否初始化成功
        """
        try:
            # 触发初始化开始钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.initializing", agent=self)
            
            # 执行实际初始化（子类实现）
            success = self._initialize_internal()
            
            if success:
                self.status = AgentStatus.READY
                logger.info(f"Agent初始化成功: {self.agent_name}")
                
                # 触发初始化完成钩子
                if self.hook_manager:
                    self.hook_manager.execute_hook("agent.initialized", agent=self)
            else:
                self.status = AgentStatus.ERROR
                logger.error(f"Agent初始化失败: {self.agent_name}")
            
            return success
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Agent初始化异常: {self.agent_name} - {str(e)}")
            return False
    
    def _initialize_internal(self) -> bool:
        """内部初始化方法（子类实现）"""
        raise NotImplementedError("子类必须实现_initialize_internal方法")
    
    def start(self) -> bool:
        """
        启动Agent
        
        Returns:
            是否启动成功
        """
        if self.status != AgentStatus.READY:
            logger.error(f"Agent状态不正确，无法启动: {self.agent_name} ({self.status})")
            return False
        
        try:
            # 触发启动开始钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.starting", agent=self)
            
            # 重置停止事件
            self._stop_event.clear()
            
            # 创建并启动线程
            self._thread = threading.Thread(
                target=self._run_loop,
                name=f"Agent_{self.agent_id}",
                daemon=True
            )
            self._thread.start()
            
            self.status = AgentStatus.RUNNING
            logger.info(f"Agent启动成功: {self.agent_name}")
            
            # 触发启动完成钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.started", agent=self)
            
            return True
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Agent启动失败: {self.agent_name} - {str(e)}")
            return False
    
    def stop(self, timeout: int = 10) -> bool:
        """
        停止Agent
        
        Args:
            timeout: 停止超时时间（秒）
            
        Returns:
            是否停止成功
        """
        if self.status != AgentStatus.RUNNING:
            logger.warning(f"Agent未运行，无需停止: {self.agent_name}")
            return True
        
        try:
            # 触发停止开始钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.stopping", agent=self)
            
            self.status = AgentStatus.STOPPING
            logger.info(f"开始停止Agent: {self.agent_name}")
            
            # 设置停止事件
            self._stop_event.set()
            
            # 等待线程结束
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                
                if self._thread.is_alive():
                    logger.warning(f"Agent停止超时: {self.agent_name}")
                    self._thread = None
            
            self.status = AgentStatus.STOPPED
            logger.info(f"Agent停止成功: {self.agent_name}")
            
            # 触发停止完成钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.stopped", agent=self)
            
            return True
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Agent停止失败: {self.agent_name} - {str(e)}")
            return False
    
    def _run_loop(self):
        """Agent运行循环"""
        logger.info(f"Agent运行循环开始: {self.agent_name}")
        
        try:
            # 触发运行循环开始钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.loop_started", agent=self)
            
            while not self._stop_event.is_set():
                try:
                    # 处理消息
                    self._process_messages()
                    
                    # 执行主循环任务
                    self._run_internal()
                    
                    # 发送心跳
                    self._send_heartbeat()
                    
                    # 短暂休眠避免CPU占用过高
                    self._stop_event.wait(timeout=0.1)
                    
                except Exception as e:
                    logger.error(f"Agent运行循环异常: {self.agent_name} - {str(e)}")
                    self.error_count += 1
                    
                    # 错误过多时停止Agent
                    if self.error_count > self.config.get("max_retries", 3):
                        logger.error(f"Agent错误过多，自动停止: {self.agent_name}")
                        break
            
            # 触发运行循环结束钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.loop_ended", agent=self)
            
            logger.info(f"Agent运行循环结束: {self.agent_name}")
            
        except Exception as e:
            logger.error(f"Agent运行循环崩溃: {self.agent_name} - {str(e)}")
            self.status = AgentStatus.ERROR
    
    def _process_messages(self):
        """处理消息"""
        try:
            # 非阻塞接收消息
            message = self.message_bus.receive_non_blocking(self.agent_id)
            
            while message:
                self.message_count += 1
                
                # 触发消息接收钩子
                if self.hook_manager:
                    self.hook_manager.execute_hook("agent.message_received", 
                                                   agent=self, message=message)
                
                # 处理消息
                self._handle_message(message)
                
                # 继续接收下一条消息
                message = self.message_bus.receive_non_blocking(self.agent_id)
                
        except Exception as e:
            logger.error(f"处理消息失败: {self.agent_name} - {str(e)}")
    
    def _run_internal(self):
        """内部运行逻辑（子类实现）"""
        raise NotImplementedError("子类必须实现_run_internal方法")
    
    def _handle_message(self, message: AgentMessage):
        """
        处理消息（子类实现）
        
        Args:
            message: 接收到的消息
        """
        raise NotImplementedError("子类必须实现_handle_message方法")
    
    def send_message(self, receiver: str, message_type: str, payload: Dict[str, Any], 
                    correlation_id: Optional[str] = None, priority: int = 50) -> bool:
        """
        发送消息
        
        Args:
            receiver: 接收者Agent ID
            message_type: 消息类型
            payload: 消息负载
            correlation_id: 关联ID
            priority: 消息优先级
            
        Returns:
            是否发送成功
        """
        try:
            message = AgentMessage(
                message_id=str(uuid.uuid4()),
                sender=self.agent_id,
                receiver=receiver,
                message_type=message_type,
                payload=payload,
                correlation_id=correlation_id,
                priority=priority
            )
            
            # 触发消息发送钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.message_sending", 
                                               agent=self, message=message)
            
            success = self.message_bus.publish(message)
            
            if success:
                logger.debug(f"Agent发送消息成功: {self.agent_name} -> {receiver} ({message_type})")
            else:
                logger.warning(f"Agent发送消息失败: {self.agent_name} -> {receiver} ({message_type})")
            
            return success
            
        except Exception as e:
            logger.error(f"发送消息异常: {self.agent_name} - {str(e)}")
            return False
    
    def broadcast_message(self, message_type: str, payload: Dict[str, Any], 
                         correlation_id: Optional[str] = None, priority: int = 50) -> bool:
        """
        广播消息（不指定接收者）
        
        Args:
            message_type: 消息类型
            payload: 消息负载
            correlation_id: 关联ID
            priority: 消息优先级
            
        Returns:
            是否发送成功
        """
        try:
            message = AgentMessage(
                message_id=str(uuid.uuid4()),
                sender=self.agent_id,
                receiver="",  # 空接收者表示广播
                message_type=message_type,
                payload=payload,
                correlation_id=correlation_id,
                priority=priority
            )
            
            # 触发消息发送钩子
            if self.hook_manager:
                self.hook_manager.execute_hook("agent.message_broadcasting", 
                                               agent=self, message=message)
            
            success = self.message_bus.publish(message)
            
            if success:
                logger.debug(f"Agent广播消息成功: {self.agent_name} ({message_type})")
            else:
                logger.warning(f"Agent广播消息失败: {self.agent_name} ({message_type})")
            
            return success
            
        except Exception as e:
            logger.error(f"广播消息异常: {self.agent_name} - {str(e)}")
            return False
    
    def _send_heartbeat(self):
        """发送心跳"""
        current_time = datetime.now()
        
        # 每30秒发送一次心跳
        if (current_time - self.last_heartbeat).total_seconds() >= 30:
            self.last_heartbeat = current_time
            
            heartbeat_msg = {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "agent_type": self.agent_type.value,
                "status": self.status.value,
                "message_count": self.message_count,
                "error_count": self.error_count,
                "timestamp": current_time.isoformat()
            }
            
            self.broadcast_message("system.heartbeat", heartbeat_msg)
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "thread_alive": self._thread.is_alive() if self._thread else False
        }


class AgentManager:
    """Agent管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.agents: Dict[str, BaseAgent] = {}
            self.message_bus = MessageBus("global")
            self.hook_manager = None
            self._initialized = True
            
            logger.info("Agent管理器初始化完成")
    
    def set_hook_manager(self, hook_manager):
        """设置钩子管理器"""
        self.hook_manager = hook_manager
        
        # 为所有已注册的Agent设置钩子管理器
        for agent in self.agents.values():
            agent.set_hook_manager(hook_manager)
    
    def register_agent(self, agent: BaseAgent) -> bool:
        """
        注册Agent
        
        Args:
            agent: Agent实例
            
        Returns:
            是否注册成功
        """
        if agent.agent_id in self.agents:
            logger.warning(f"Agent已注册: {agent.agent_id}")
            return False
        
        # 设置钩子管理器
        if self.hook_manager:
            agent.set_hook_manager(self.hook_manager)
        
        self.agents[agent.agent_id] = agent
        logger.info(f"Agent注册成功: {agent.agent_name} ({agent.agent_id})")
        
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        取消注册Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否取消成功
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent未注册: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        # 停止Agent
        if agent.status == AgentStatus.RUNNING:
            agent.stop()
        
        # 从消息总线取消注册
        self.message_bus.unregister_agent(agent_id)
        
        # 从管理器中移除
        del self.agents[agent_id]
        
        logger.info(f"Agent取消注册: {agent_id}")
        return True
    
    def start_agent(self, agent_id: str) -> bool:
        """启动Agent"""
        if agent_id not in self.agents:
            logger.error(f"Agent未注册: {agent_id}")
            return False
        
        return self.agents[agent_id].start()
    
    def stop_agent(self, agent_id: str, timeout: int = 10) -> bool:
        """停止Agent"""
        if agent_id not in self.agents:
            logger.error(f"Agent未注册: {agent_id}")
            return False
        
        return self.agents[agent_id].stop(timeout)
    
    def get_running_agents(self) -> List[str]:
        """获取运行中的Agent列表"""
        running_agents = []
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'status') and agent.status == AgentStatus.RUNNING:
                running_agents.append(agent_id)
        return running_agents
    
    def start_all_agents(self) -> Dict[str, bool]:
        """启动所有Agent"""
        results = {}
        
        for agent_id, agent in self.agents.items():
            if agent.status == AgentStatus.READY:
                results[agent_id] = agent.start()
            else:
                results[agent_id] = False
                logger.warning(f"Agent状态不正确，无法启动: {agent_id} ({agent.status})")
        
        return results
    
    def stop_all_agents(self, timeout: int = 10) -> Dict[str, bool]:
        """停止所有Agent"""
        results = {}
        
        for agent_id, agent in self.agents.items():
            if agent.status == AgentStatus.RUNNING:
                results[agent_id] = agent.stop(timeout)
            else:
                results[agent_id] = True
        
        return results
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取Agent"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """获取所有Agent"""
        return self.agents.copy()
    
    def get_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """获取所有Agent状态"""
        statuses = {}
        
        for agent_id, agent in self.agents.items():
            statuses[agent_id] = agent.get_status_info()
        
        return statuses
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        agent_statuses = self.get_agent_statuses()
        
        # 统计不同状态的Agent数量
        status_counts = {}
        for status_info in agent_statuses.values():
            status = status_info["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 消息总线统计
        bus_stats = self.message_bus.get_stats()
        
        return {
            "total_agents": len(self.agents),
            "status_distribution": status_counts,
            "running_agents": status_counts.get(AgentStatus.RUNNING.value, 0),
            "error_agents": status_counts.get(AgentStatus.ERROR.value, 0),
            "message_bus_stats": bus_stats,
            "timestamp": datetime.now().isoformat()
        }


# 创建全局Agent管理器实例
agent_manager = AgentManager()

# 导出核心类
__all__ = [
    'AgentStatus',
    'AgentType',
    'AgentConfig',
    'AgentMessage',
    'MessageBus',
    'BaseAgent',
    'AgentManager',
    'agent_manager'
]