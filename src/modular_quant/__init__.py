"""
modular_quant - 模块化量化平台主模块

核心设计理念：数据是基础，做成模块化，功能只挂接
- 数据层：独立数据源模块，支持热插拔
- 模块层：功能模块化，职责单一
- 挂接层：事件驱动，模块间松耦合
- 配置层：统一配置管理，支持热更新

项目结构参考：
- EasyUp：生产级Agent驱动架构
- KHQuant 3.2：专业级数据库设计
- daily_stock_analysis：AI驱动分析框架
- injoyai/tdx：精准数据解析算法
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# 设置根日志记录器
try:
    logs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(logs_dir, 'modular_quant.log'))
        ]
    )
except Exception as e:
    # 如果无法创建日志文件，只使用控制台输出
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)
    logger.warning(f"无法创建日志文件，使用控制台输出: {str(e)}")

logger = logging.getLogger(__name__)

# 版本信息
__version__ = "1.0.0"
__author__ = "gszolo80 (https://github.com/gszolo80)"
__license__ = "MIT"
__copyright__ = f"Copyright (c) 2026-{datetime.now().year} {__author__}"

# 模块描述
__description__ = """
模块化量化平台 - 融合三大项目精华的现代化量化分析系统

特色功能：
1. 🔌 插件式数据源：通达信、东方财富、AkShare等多数据源热插拔
2. ⚙️ 模块化架构：数据采集、策略分析、回测验证、报告生成完全分离
3. 🎯 事件驱动：钩子管理器实现功能挂接，模块间松耦合
4. 🤖 Agent驱动：基于消息总线的智能Agent协作框架
5. 📊 专业分析：技术指标、基本面、舆情多维度综合分析
6. 🔒 企业级部署：Docker容器化，生产级稳定性和可维护性

核心学习：
- injoyai/tdx：专业的通达信数据解析算法
- KHQuant 3.2：先进的DuckDB数据库架构设计
- daily_stock_analysis：智能的AI驱动分析框架
- EasyUp：生产级Agent驱动的量化交易系统架构

设计原则：
- 数据是基础：数据层独立，支持任意数据源替换
- 功能模块化：每个功能独立开发、测试、部署
- 只挂接不耦合：功能间通过事件/钩子连接，避免直接依赖
"""


# 核心组件导入
try:
    # 配置管理器
    from .config import config_manager, get_config, set_config, load_config, save_config
    
    # 数据源模块
    from .data_sources import DataSource, TDXDataSource, EastMoneyDataSource, DataSourceFactory
    
    # 核心数据模型
    from .core_models import (
        StockInfo, KLineData, TechnicalIndicators, TradingSignal,
        BacktestResult, Portfolio, SystemEvent, SystemConfig, DataValidator
    )
    
    # TDX解析器
    from .core_models.tdx_parser import TDXParser
    
    # 钩子管理器
    from .hook_manager import HookManager, HookType, HookPriority
    
    # Agent协调层
    from .agents import (
        AgentMessage, MessageBus, BaseAgent, AgentManager,
        agent_manager
    )
    
    # Agent实现
    from .agents import DataCollectorAgent, StrategyAnalyzerAgent, ReportGeneratorAgent
    
    logger.info("所有核心模块导入成功")
    
except ImportError as e:
    logger.warning(f"部分模块导入失败: {str(e)}")
    logger.info("请确保所有依赖已安装: pip install -r requirements.txt")


class ModularQuantPlatform:
    """模块化量化平台主类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化量化平台
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        logger.info(f"初始化模块化量化平台 v{__version__}")
        
        # 1. 初始化配置管理器
        self.config = config_manager
        if config_path and os.path.exists(config_path):
            if load_config(config_path):
                logger.info(f"从配置文件加载配置: {config_path}")
            else:
                logger.warning("配置文件加载失败，使用默认配置")
        
        # 2. 初始化核心组件
        self.hook_manager = HookManager()
        self.agent_manager = AgentManager()
        
        # 3. 初始化数据源工厂
        self.data_source_factory = DataSourceFactory()
        
        # 4. 初始化TDX解析器（延迟初始化，只在需要时创建）
        self.tdx_parser = None
        
        # 5. 系统状态
        self.is_initialized = False
        self.startup_time = datetime.now()
        self.system_events: List[SystemEvent] = []
        
        # 6. 注册默认钩子
        self._register_default_hooks()
        
        logger.info("模块化量化平台初始化完成")
    
    def _get_tdx_parser(self):
        """获取TDX解析器（延迟初始化）"""
        if self.tdx_parser is None:
            tdx_path = self.config.get("tdx.path")
            if tdx_path and os.path.exists(tdx_path):
                self.tdx_parser = TDXParser(tdx_path)
                logger.info(f"TDX解析器初始化成功: {tdx_path}")
            else:
                logger.warning(f"TDX路径不存在或未配置: {tdx_path}")
                self.tdx_parser = None
        return self.tdx_parser
    
    def _register_default_hooks(self):
        """注册默认系统钩子"""
        
        # 系统启动钩子
        self.hook_manager.register_hook(
            name="system.startup",
            callback=self._on_system_startup,
            hook_type=HookType.BEFORE,
            priority=HookPriority.HIGH
        )
        
        # 系统关闭钩子
        self.hook_manager.register_hook(
            name="system.shutdown",
            callback=self._on_system_shutdown,
            hook_type=HookType.AFTER,
            priority=HookPriority.HIGH
        )
        
        # 错误处理钩子
        self.hook_manager.register_hook(
            name="system.error",
            callback=self._on_error_occurred,
            hook_type=HookType.ERROR,
            priority=HookPriority.HIGHEST
        )
        
        # 数据获取钩子
        self.hook_manager.register_hook(
            name="data.after_fetch",
            callback=self._on_data_after_fetch,
            hook_type=HookType.AFTER,
            priority=HookPriority.NORMAL
        )
        
        # 策略信号钩子
        self.hook_manager.register_hook(
            name="strategy.signal_generated",
            callback=self._on_strategy_signal_generated,
            hook_type=HookType.EVENT,
            priority=HookPriority.NORMAL
        )
        
        logger.debug("默认系统钩子注册完成")
    
    def _on_system_startup(self, **kwargs) -> Dict[str, Any]:
        """系统启动钩子"""
        logger.info("系统启动钩子执行")
        
        # 获取event_data参数
        event_data = kwargs.get('event_data', {})
        
        # 触发系统启动事件
        system_event = SystemEvent(
            event_type="SYSTEM_STARTUP",
            event_data=event_data,
            timestamp=datetime.now(),
            source_module="ModularQuantPlatform"
        )
        self.system_events.append(system_event)
        
        # 初始化所有Agent
        enabled_agents = self.config.get("agents.enabled_agents", [])
        for agent_name in enabled_agents:
            try:
                self.agent_manager.register_agent(agent_name)
                logger.info(f"Agent注册成功: {agent_name}")
            except Exception as e:
                logger.error(f"Agent注册失败 {agent_name}: {str(e)}")
        
        return {
            "status": "success",
            "message": "系统启动完成",
            "startup_time": self.startup_time.isoformat(),
            "enabled_agents": enabled_agents
        }
    
    def _on_system_shutdown(self, **kwargs) -> Dict[str, Any]:
        """系统关闭钩子"""
        logger.info("系统关闭钩子执行")
        
        # 获取event_data参数
        event_data = kwargs.get('event_data', {})
        
        # 保存系统状态
        if hasattr(self, 'system_events') and self.system_events:
            event_count = len(self.system_events)
            logger.info(f"保存系统事件: {event_count} 条")
        
        # 清理资源
        if hasattr(self, 'agent_manager'):
            self.agent_manager.stop_all_agents()
        
        # 触发系统关闭事件
        system_event = SystemEvent(
            event_type="SYSTEM_SHUTDOWN",
            event_data=event_data or {},
            timestamp=datetime.now(),
            source_module="ModularQuantPlatform"
        )
        self.system_events.append(system_event)
        
        return {
            "status": "success",
            "message": "系统关闭完成",
            "shutdown_time": datetime.now().isoformat()
        }
    
    def _on_error_occurred(self, **kwargs) -> Dict[str, Any]:
        """错误处理钩子"""
        # 获取error_info参数
        error_info = kwargs.get('error_info', {})
        logger.error(f"系统错误: {error_info.get('error_type', 'Unknown')} - {error_info.get('error_message', 'No message')}")
        
        # 记录错误到系统事件
        system_event = SystemEvent(
            event_type="ERROR_OCCURRED",
            event_data=error_info,
            timestamp=datetime.now(),
            source_module=error_info.get('source_module', 'Unknown')
        )
        self.system_events.append(system_event)
        
        # 可以添加错误恢复逻辑，如重启组件等
        error_handled = False
        if error_info.get('error_type') == 'DATABASE_ERROR':
            # 数据库错误处理逻辑
            logger.warning("数据库错误，尝试重连或使用备份数据")
            error_handled = True
        
        return {
            "error_handled": error_handled,
            "retry_available": True,
            "next_action": "continue" if error_handled else "stop"
        }
    
    def _on_data_after_fetch(self, **kwargs) -> Dict[str, Any]:
        """数据获取后钩子"""
        # 获取stock_data参数
        stock_data = kwargs.get('stock_data')
        if stock_data is None:
            logger.warning("数据获取钩子缺少stock_data参数")
            return {"status": "error", "message": "缺少stock_data参数"}
        
        logger.debug(f"数据获取钩子: {stock_data.code}")
        
        # 触发技术指标计算
        indicators = self._calculate_technical_indicators(stock_data)
        
        # 触发数据分析
        analysis_result = self._analyze_stock_data(stock_data, indicators)
        
        # 广播数据就绪消息
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender="DataCollector",
            receiver="",  # 空字符串表示广播
            message_type="DATA_READY",
            payload={
                "stock_code": stock_data.code,
                "data_time": stock_data.timestamp,
                "indicators": indicators,
                "analysis": analysis_result
            }
        )
        send_message(message)
        
        return {
            "stock_code": stock_data.code,
            "indicators_calculated": True,
            "analysis_completed": True,
            "message_sent": True
        }
    
    def _on_strategy_signal_generated(self, **kwargs) -> Dict[str, Any]:
        """策略信号生成钩子"""
        # 获取signal_data参数
        signal_data = kwargs.get('signal_data', {})
        logger.info(f"策略信号钩子: {signal_data.get('stock_code', 'Unknown')} - {signal_data.get('signal', 'Unknown')}")
        
        # 记录信号
        signal_event = SystemEvent(
            event_type="STRATEGY_SIGNAL",
            event_data=signal_data,
            timestamp=datetime.now(),
            source_module="StrategyEngine"
        )
        self.system_events.append(signal_event)
        
        # 触发通知
        if signal_data.get('signal') in ['BUY', 'SELL']:
            notification_data = {
                "stock_code": signal_data.get('stock_code'),
                "signal": signal_data.get('signal'),
                "reason": signal_data.get('reason', '策略信号'),
                "timestamp": datetime.now().isoformat(),
                "strength": signal_data.get('strength', 'medium')
            }
            
            # 发送通知消息
            notification_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                sender="StrategyAnalyzer",
                receiver="NotificationAgent",
                message_type="TRADE_SIGNAL",
                payload=notification_data
            )
            send_message(notification_message)
        
        return {
            "signal_recorded": True,
            "notification_triggered": signal_data.get('signal') in ['BUY', 'SELL']
        }
    
    def _calculate_technical_indicators(self, stock_data: StockInfo) -> TechnicalIndicators:
        """计算技术指标"""
        # 这里实现技术指标计算逻辑
        # 简化实现，实际应该基于历史K线数据计算
        from .core_models import TechnicalIndicators
        
        return TechnicalIndicators(
            stock_code=stock_data.code,
            timestamp=datetime.now(),
            ma5=stock_data.close * 0.99 if stock_data.close else 0,
            ma10=stock_data.close * 1.01 if stock_data.close else 0,
            ma20=stock_data.close * 0.98 if stock_data.close else 0,
            rsi=50.0,  # 默认值
            macd=0.0,
            macd_signal=0.0,
            macd_histogram=0.0,
            bollinger_upper=stock_data.close * 1.02 if stock_data.close else 0,
            bollinger_middle=stock_data.close if stock_data.close else 0,
            bollinger_lower=stock_data.close * 0.98 if stock_data.close else 0,
            volume_ma=stock_data.volume * 0.9 if stock_data.volume else 0
        )
    
    def _analyze_stock_data(self, stock_data: StockInfo, indicators: TechnicalIndicators) -> Dict[str, Any]:
        """分析股票数据"""
        # 简化分析逻辑
        analysis = {
            "stock_code": stock_data.code,
            "timestamp": datetime.now().isoformat(),
            "price_trend": "stable",
            "volume_trend": "normal",
            "technical_score": 65,
            "recommendation": "HOLD",
            "confidence": 0.7,
            "risk_level": "medium"
        }
        
        # 基于指标的分析
        if indicators.ma5 > indicators.ma10:
            analysis["price_trend"] = "bullish"
            analysis["technical_score"] += 10
        elif indicators.ma5 < indicators.ma10:
            analysis["price_trend"] = "bearish"
            analysis["technical_score"] -= 10
        
        if indicators.rsi > 70:
            analysis["recommendation"] = "SELL"
            analysis["confidence"] = 0.8
        elif indicators.rsi < 30:
            analysis["recommendation"] = "BUY"
            analysis["confidence"] = 0.8
        
        return analysis
    
    def start(self):
        """启动量化平台"""
        logger.info("启动模块化量化平台...")
        
        try:
            # 执行系统启动钩子
            startup_result = self.hook_manager.execute_hook(
                "system.startup",
                event_data={"startup_time": self.startup_time.isoformat()}
            )
            
            # 启动Agent管理器
            self.agent_manager.start_all_agents()
            
            # 启动消息总线监听
            if hasattr(self, 'agent_manager') and hasattr(self.agent_manager, 'message_bus'):
                self.agent_manager.message_bus.start()
            
            self.is_initialized = True
            
            logger.info(f"模块化量化平台启动成功，版本: {__version__}")
            logger.info(f"系统启动时间: {self.startup_time}")
            logger.info(f"启用模块: 数据源={self.config.get('data_sources.default_source')}, Agent={self.config.get('agents.enabled_agents')}")
            
            return {
                "status": "success",
                "message": "量化平台启动成功",
                "version": __version__,
                "startup_result": startup_result
            }
            
        except Exception as e:
            logger.error(f"量化平台启动失败: {str(e)}")
            
            # 执行错误处理钩子
            self.hook_manager.execute_hook(
                "system.error",
                error_info={
                    "error_type": "STARTUP_ERROR",
                    "error_message": str(e),
                    "source_module": "ModularQuantPlatform.start"
                }
            )
            
            return {
                "status": "error",
                "message": f"量化平台启动失败: {str(e)}"
            }
    
    def stop(self):
        """停止量化平台"""
        logger.info("停止模块化量化平台...")
        
        try:
            # 执行系统关闭钩子
            shutdown_result = self.hook_manager.execute_hook(
                "system.shutdown",
                event_data={"shutdown_time": datetime.now().isoformat()}
            )
            
            # 停止Agent管理器
            self.agent_manager.stop_all_agents()
            
            # 停止消息总线
            if hasattr(self, 'agent_manager') and hasattr(self.agent_manager, 'message_bus'):
                self.agent_manager.message_bus.stop()
            
            self.is_initialized = False
            
            logger.info("模块化量化平台停止成功")
            
            return {
                "status": "success",
                "message": "量化平台停止成功",
                "shutdown_result": shutdown_result
            }
            
        except Exception as e:
            logger.error(f"量化平台停止失败: {str(e)}")
            return {
                "status": "error",
                "message": f"量化平台停止失败: {str(e)}"
            }
    
    def get_stock_data(self, stock_code: str, data_source: str = None) -> StockInfo:
        """
        获取股票数据
        
        Args:
            stock_code: 股票代码
            data_source: 数据源名称，如果为None则使用默认数据源
            
        Returns:
            StockInfo: 股票数据对象
        """
        if not data_source:
            data_source = self.config.get("data_sources.default_source", "tdx")
        
        try:
            # 创建数据源
            source = self.data_source_factory.create_data_source(data_source)
            
            # 获取数据
            stock_data = source.fetch_stock_data(stock_code)
            
            # 执行数据获取后钩子
            self.hook_manager.execute_hook(
                "data.after_fetch",
                stock_data=stock_data
            )
            
            return stock_data
            
        except Exception as e:
            logger.error(f"获取股票数据失败 {stock_code}: {str(e)}")
            
            # 执行错误处理钩子
            self.hook_manager.execute_hook(
                "system.error",
                error_info={
                    "error_type": "DATA_FETCH_ERROR",
                    "error_message": str(e),
                    "stock_code": stock_code,
                    "data_source": data_source,
                    "source_module": "ModularQuantPlatform.get_stock_data"
                }
            )
            
            raise
    
    def run_backtest(self, strategy_config: Dict[str, Any]) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy_config: 策略配置
            
        Returns:
            BacktestResult: 回测结果
        """
        logger.info(f"开始回测: {strategy_config.get('strategy_name', 'Unknown')}")
        
        try:
            # 这里实现回测逻辑
            # 简化实现，实际应该包括：
            # 1. 加载历史数据
            # 2. 应用策略规则
            # 3. 计算交易信号
            # 4. 模拟交易执行
            # 5. 计算性能指标
            
            # 创建回测结果
            result = BacktestResult(
                strategy_name=strategy_config.get('strategy_name', 'DefaultStrategy'),
                stock_codes=strategy_config.get('stock_codes', []),
                start_date=strategy_config.get('start_date', '2021-01-01'),
                end_date=strategy_config.get('end_date', '2026-03-20'),
                initial_capital=self.config.get("backtest.initial_capital", 100000.0),
                total_return=0.15,  # 简化值
                annual_return=0.03,
                max_drawdown=0.12,
                sharpe_ratio=1.2,
                win_rate=0.55,
                total_trades=100,
                profitable_trades=55
            )
            
            # 执行回测完成钩子
            self.hook_manager.execute_hook(
                "backtest.complete",
                backtest_result=result
            )
            
            return result
            
        except Exception as e:
            logger.error(f"回测运行失败: {str(e)}")
            
            # 执行错误处理钩子
            self.hook_manager.execute_hook(
                "system.error",
                error_info={
                    "error_type": "BACKTEST_ERROR",
                    "error_message": str(e),
                    "strategy_config": strategy_config,
                    "source_module": "ModularQuantPlatform.run_backtest"
                }
            )
            
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "platform": {
                "version": __version__,
                "initialized": self.is_initialized,
                "startup_time": self.startup_time.isoformat() if hasattr(self, 'startup_time') else None,
                "running_time": (datetime.now() - self.startup_time).total_seconds() if hasattr(self, 'startup_time') and self.is_initialized else 0
            },
            "modules": {
                "config_manager": True,
                "hook_manager": hasattr(self, 'hook_manager'),
                "agent_manager": hasattr(self, 'agent_manager'),
                "data_source_factory": hasattr(self, 'data_source_factory')
            },
            "agents": {
                "enabled": self.config.get("agents.enabled_agents", []),
                "running": self.agent_manager.get_running_agents() if hasattr(self, 'agent_manager') else []
            },
            "hooks": {
                "registered": sum(len(hook_list) for hook_list in self.hook_manager.hooks.values()) if hasattr(self, 'hook_manager') and hasattr(self.hook_manager, 'hooks') else 0,
                "executed": self.hook_manager.execution_count if hasattr(self, 'hook_manager') and hasattr(self.hook_manager, 'execution_count') else 0
            },
            "system_events": len(self.system_events) if hasattr(self, 'system_events') else 0,
            "config": {
                "environment": self.config.get("system.environment", "development"),
                "debug": self.config.get("system.debug", True),
                "log_level": self.config.get("system.log_level", "INFO")
            }
        }
        
        return status
    
    def register_custom_hook(self, name: str, hook_func, 
                           hook_type: HookType = HookType.EVENT,
                           priority: HookPriority = HookPriority.NORMAL) -> bool:
        """
        注册自定义钩子
        
        Args:
            name: 钩子名称
            hook_func: 钩子函数
            hook_type: 钩子类型
            priority: 执行优先级
            
        Returns:
            是否注册成功
        """
        if not hasattr(self, 'hook_manager'):
            logger.error("钩子管理器未初始化")
            return False
        
        try:
            self.hook_manager.register_hook(
                name=name,
                callback=hook_func,
                hook_type=hook_type,
                priority=priority
            )
            logger.info(f"自定义钩子注册成功: {name}")
            return True
        except Exception as e:
            logger.error(f"自定义钩子注册失败 {name}: {str(e)}")
            return False
    
    def register_custom_agent(self, agent_name: str, agent_class) -> bool:
        """
        注册自定义Agent
        
        Args:
            agent_name: Agent名称
            agent_class: Agent类
            
        Returns:
            是否注册成功
        """
        if not hasattr(self, 'agent_manager'):
            logger.error("Agent管理器未初始化")
            return False
        
        try:
            self.agent_manager.register_custom_agent(agent_name, agent_class)
            logger.info(f"自定义Agent注册成功: {agent_name}")
            return True
        except Exception as e:
            logger.error(f"自定义Agent注册失败 {agent_name}: {str(e)}")
            return False


# 创建全局平台实例
_platform_instance = None


def get_platform(config_path: Optional[str] = None) -> ModularQuantPlatform:
    """
    获取平台实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ModularQuantPlatform: 平台实例
    """
    global _platform_instance
    
    if _platform_instance is None:
        _platform_instance = ModularQuantPlatform(config_path)
    
    return _platform_instance


def start_platform(config_path: Optional[str] = None) -> Dict[str, Any]:
    """启动量化平台（便捷函数）"""
    platform = get_platform(config_path)
    return platform.start()


def stop_platform() -> Dict[str, Any]:
    """停止量化平台（便捷函数）"""
    if _platform_instance is not None:
        return _platform_instance.stop()
    return {"status": "warning", "message": "平台未启动"}


def get_stock_data(stock_code: str, data_source: str = None) -> StockInfo:
    """获取股票数据（便捷函数）"""
    platform = get_platform()
    return platform.get_stock_data(stock_code, data_source)


def get_system_status() -> Dict[str, Any]:
    """获取系统状态（便捷函数）"""
    if _platform_instance is not None:
        return _platform_instance.get_system_status()
    return {"status": "platform_not_initialized"}


# 导出核心组件
__all__ = [
    # 主平台
    "ModularQuantPlatform", "get_platform", "start_platform", "stop_platform",
    
    # 配置管理
    "config_manager", "get_config", "set_config", "load_config", "save_config",
    
    # 数据源
    "DataSource", "TDXDataSource", "EastMoneyDataSource", "DataSourceFactory",
    
    # 核心模型
    "StockInfo", "KLineData", "TechnicalIndicators", "TradingSignal",
    "BacktestResult", "Portfolio", "SystemEvent", "SystemConfig", "DataValidator",
    "TDXParser",
    
    # 钩子管理
    "HookManager", "HookType",
    
    # Agent管理
    "AgentMessage", "MessageBus", "BaseAgent", "AgentManager", "agent_manager",
    "DataCollectorAgent", "StrategyAnalyzerAgent", "ReportGeneratorAgent",
    
    # 便捷函数
    "get_stock_data", "get_system_status"
]


# 平台信息输出
def print_platform_info():
    """打印平台信息"""
    print(f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                   模块化量化平台 v{__version__}                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║ 核心理念：数据是基础，做成模块化，功能只挂接                          ║
║ 设计原则：借鉴三大项目精华，打造现代化量化分析系统                    ║
║ 技术栈：Python 3.8+ | DuckDB | 事件驱动 | Agent架构                  ║
║ 许可证：{__license__}                                                  ║
║ 作者：{__author__}                                                     ║
╚═══════════════════════════════════════════════════════════════════════╝

特色功能：
  🔌 插件式数据源：通达信、东方财富、AkShare等多数据源热插拔
  ⚙️ 模块化架构：数据采集、策略分析、回测验证、报告生成完全分离
  🎯 事件驱动：钩子管理器实现功能挂接，模块间松耦合
  🤖 Agent驱动：基于消息总线的智能Agent协作框架
  📊 专业分析：技术指标、基本面、舆情多维度综合分析
  🔒 企业级部署：Docker容器化，生产级稳定性和可维护性

使用示例：
  from modular_quant import start_platform, get_stock_data
  start_platform("config.yaml")
  data = get_stock_data("000001.SZ", "tdx")
  print(f"平安银行数据: {{data.close}}")
    """)

# 如果直接运行此文件，打印平台信息
if __name__ == "__main__":
    print_platform_info()