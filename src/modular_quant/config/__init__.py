"""
配置管理器 - 模块化架构的统一配置管理

设计原则：
1. 分层配置：系统级、模块级、实例级配置
2. 动态更新：支持运行时配置热更新
3. 环境感知：支持不同环境（开发、测试、生产）
4. 验证机制：配置项类型验证和范围检查

实现参考：
- 现代应用框架的配置管理最佳实践
- Docker容器的环境变量配置
- 企业级系统的配置管理方案
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
import copy
import threading
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """配置源枚举"""
    DEFAULT = "default"      # 默认配置
    ENV_VAR = "env_var"      # 环境变量
    FILE = "file"            # 配置文件
    DATABASE = "database"    # 数据库
    API = "api"              # API接口
    RUNTIME = "runtime"      # 运行时设置


@dataclass
class ConfigItem:
    """配置项"""
    key: str                     # 配置键
    value: Any                   # 配置值
    source: ConfigSource         # 配置源
    data_type: str               # 数据类型
    description: Optional[str] = None  # 描述
    required: bool = False       # 是否必需
    default_value: Any = None    # 默认值
    validation_rules: Dict[str, Any] = field(default_factory=dict)  # 验证规则
    last_updated: datetime = field(default_factory=datetime.now)  # 最后更新时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def validate(self) -> List[str]:
        """验证配置项"""
        errors = []
        
        # 检查必需项
        if self.required and self.value is None:
            errors.append(f"配置项必需: {self.key}")
            return errors
        
        # 类型检查
        if self.data_type == "int":
            if not isinstance(self.value, int):
                errors.append(f"配置项类型错误: {self.key} 应为 int, 实际为 {type(self.value)}")
        
        elif self.data_type == "float":
            if not isinstance(self.value, (int, float)):
                errors.append(f"配置项类型错误: {self.key} 应为 float, 实际为 {type(self.value)}")
        
        elif self.data_type == "str":
            if not isinstance(self.value, str):
                errors.append(f"配置项类型错误: {self.key} 应为 str, 实际为 {type(self.value)}")
        
        elif self.data_type == "bool":
            if not isinstance(self.value, bool):
                errors.append(f"配置项类型错误: {self.key} 应为 bool, 实际为 {type(self.value)}")
        
        elif self.data_type == "list":
            if not isinstance(self.value, list):
                errors.append(f"配置项类型错误: {self.key} 应为 list, 实际为 {type(self.value)}")
        
        elif self.data_type == "dict":
            if not isinstance(self.value, dict):
                errors.append(f"配置项类型错误: {self.key} 应为 dict, 实际为 {type(self.value)}")
        
        # 范围检查
        if "min" in self.validation_rules and self.value is not None:
            if self.data_type in ["int", "float"]:
                if self.value < self.validation_rules["min"]:
                    errors.append(f"配置项值太小: {self.key} >= {self.validation_rules['min']}")
        
        if "max" in self.validation_rules and self.value is not None:
            if self.data_type in ["int", "float"]:
                if self.value > self.validation_rules["max"]:
                    errors.append(f"配置项值太大: {self.key} <= {self.validation_rules['max']}")
        
        # 枚举值检查
        if "enum" in self.validation_rules and self.value is not None:
            if self.value not in self.validation_rules["enum"]:
                errors.append(f"配置项值无效: {self.key} 应为 {self.validation_rules['enum']} 之一")
        
        # 正则表达式检查
        if "regex" in self.validation_rules and self.value is not None and self.data_type == "str":
            import re
            if not re.match(self.validation_rules["regex"], self.value):
                errors.append(f"配置项格式错误: {self.key} 不符合正则表达式 {self.validation_rules['regex']}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source.value,
            "data_type": self.data_type,
            "description": self.description,
            "required": self.required,
            "default_value": self.default_value,
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ConfigSection:
    """配置节"""
    name: str                     # 配置节名称
    items: Dict[str, ConfigItem] = field(default_factory=dict)  # 配置项
    description: Optional[str] = None  # 描述
    version: str = "1.0.0"        # 版本
    last_updated: datetime = field(default_factory=datetime.now)  # 最后更新时间
    
    def add_item(self, item: ConfigItem) -> bool:
        """添加配置项"""
        if item.key in self.items:
            logger.warning(f"配置项已存在: {self.name}.{item.key}")
            return False
        
        self.items[item.key] = item
        self.last_updated = datetime.now()
        return True
    
    def update_item(self, key: str, value: Any, source: ConfigSource = ConfigSource.RUNTIME) -> bool:
        """更新配置项"""
        if key not in self.items:
            logger.error(f"配置项不存在: {self.name}.{key}")
            return False
        
        item = self.items[key]
        item.value = value
        item.source = source
        item.last_updated = datetime.now()
        
        # 验证新值
        errors = item.validate()
        if errors:
            logger.error(f"配置项验证失败: {self.name}.{key} - {errors}")
            return False
        
        self.last_updated = datetime.now()
        logger.debug(f"配置项更新成功: {self.name}.{key}")
        return True
    
    def get_item(self, key: str, default: Any = None) -> Any:
        """获取配置项值"""
        if key in self.items:
            return self.items[key].value
        return default
    
    def validate_section(self) -> Dict[str, List[str]]:
        """验证配置节"""
        errors = {}
        
        for key, item in self.items.items():
            item_errors = item.validate()
            if item_errors:
                errors[key] = item_errors
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
            "items": {k: v.to_dict() for k, v in self.items.items()}
        }


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.sections: Dict[str, ConfigSection] = {}
            self.config_path: Optional[Path] = None
            self.watch_interval: int = 30  # 配置文件监视间隔（秒）
            self._lock = threading.RLock()
            self._config_watcher = None
            self._config_changed_callbacks: List[Callable] = []
            
            # 加载默认配置
            self._load_default_config()
            
            # 加载环境配置
            self._load_env_config()
            
            self._initialized = True
            logger.info("配置管理器初始化完成")
    
    def _load_default_config(self):
        """加载默认配置"""
        # 系统配置
        system_section = ConfigSection("system", description="系统配置")
        
        system_section.add_item(ConfigItem(
            key="name",
            value="Modular Quant Platform",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="系统名称",
            required=True
        ))
        
        system_section.add_item(ConfigItem(
            key="version",
            value="1.0.0",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="系统版本",
            required=True
        ))
        
        system_section.add_item(ConfigItem(
            key="environment",
            value="development",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="运行环境",
            validation_rules={"enum": ["development", "testing", "production"]}
        ))
        
        system_section.add_item(ConfigItem(
            key="debug",
            value=True,
            source=ConfigSource.DEFAULT,
            data_type="bool",
            description="调试模式"
        ))
        
        system_section.add_item(ConfigItem(
            key="log_level",
            value="INFO",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="日志级别",
            validation_rules={"enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
        ))
        
        # 数据源配置
        data_source_section = ConfigSection("data_sources", description="数据源配置")
        
        data_source_section.add_item(ConfigItem(
            key="default_source",
            value="tdx",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="默认数据源",
            validation_rules={"enum": ["tdx", "eastmoney", "akshare"]}
        ))
        
        data_source_section.add_item(ConfigItem(
            key="tdx_path",
            value="/Volumes/[C] Windows 10/new_tdx64/",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="通达信数据路径",
            required=False
        ))
        
        data_source_section.add_item(ConfigItem(
            key="eastmoney_api_key",
            value="",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="东方财富API密钥",
            required=False
        ))
        
        data_source_section.add_item(ConfigItem(
            key="cache_enabled",
            value=True,
            source=ConfigSource.DEFAULT,
            data_type="bool",
            description="启用缓存"
        ))
        
        data_source_section.add_item(ConfigItem(
            key="cache_ttl",
            value=3600,
            source=ConfigSource.DEFAULT,
            data_type="int",
            description="缓存存活时间（秒）",
            validation_rules={"min": 60, "max": 86400}
        ))
        
        # 数据库配置
        database_section = ConfigSection("database", description="数据库配置")
        
        database_section.add_item(ConfigItem(
            key="engine",
            value="duckdb",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="数据库引擎",
            validation_rules={"enum": ["duckdb", "sqlite", "postgresql"]}
        ))
        
        database_section.add_item(ConfigItem(
            key="path",
            value="stocks.duckdb",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="数据库文件路径"
        ))
        
        database_section.add_item(ConfigItem(
            key="memory_limit",
            value="4GB",
            source=ConfigSource.DEFAULT,
            data_type="str",
            description="内存限制"
        ))
        
        database_section.add_item(ConfigItem(
            key="threads",
            value=4,
            source=ConfigSource.DEFAULT,
            data_type="int",
            description="线程数",
            validation_rules={"min": 1, "max": 16}
        ))
        
        # 回测配置
        backtest_section = ConfigSection("backtest", description="回测配置")
        
        backtest_section.add_item(ConfigItem(
            key="initial_capital",
            value=100000.0,
            source=ConfigSource.DEFAULT,
            data_type="float",
            description="初始资金",
            validation_rules={"min": 1000.0, "max": 10000000.0}
        ))
        
        backtest_section.add_item(ConfigItem(
            key="commission_rate",
            value=0.0003,
            source=ConfigSource.DEFAULT,
            data_type="float",
            description="佣金费率",
            validation_rules={"min": 0.0, "max": 0.01}
        ))
        
        backtest_section.add_item(ConfigItem(
            key="slippage",
            value=0.001,
            source=ConfigSource.DEFAULT,
            data_type="float",
            description="滑点",
            validation_rules={"min": 0.0, "max": 0.05}
        ))
        
        backtest_section.add_item(ConfigItem(
            key="default_strategies",
            value=["ma_cross", "macd", "rsi"],
            source=ConfigSource.DEFAULT,
            data_type="list",
            description="默认策略列表"
        ))
        
        # Agent配置
        agent_section = ConfigSection("agents", description="Agent配置")
        
        agent_section.add_item(ConfigItem(
            key="enabled_agents",
            value=["data_collector", "strategy_analyzer", "report_generator"],
            source=ConfigSource.DEFAULT,
            data_type="list",
            description="启用的Agent列表"
        ))
        
        agent_section.add_item(ConfigItem(
            key="heartbeat_interval",
            value=30,
            source=ConfigSource.DEFAULT,
            data_type="int",
            description="心跳间隔（秒）",
            validation_rules={"min": 10, "max": 300}
        ))
        
        agent_section.add_item(ConfigItem(
            key="message_timeout",
            value=60,
            source=ConfigSource.DEFAULT,
            data_type="int",
            description="消息超时时间（秒）",
            validation_rules={"min": 10, "max": 300}
        ))
        
        # 添加所有配置节
        self.sections = {
            "system": system_section,
            "data_sources": data_source_section,
            "database": database_section,
            "backtest": backtest_section,
            "agents": agent_section
        }
        
        logger.info("默认配置加载完成")
    
    def _load_env_config(self):
        """从环境变量加载配置"""
        env_mappings = {
            # 系统配置
            "QUANT_ENVIRONMENT": ("system", "environment"),
            "QUANT_DEBUG": ("system", "debug"),
            "QUANT_LOG_LEVEL": ("system", "log_level"),
            
            # 数据源配置
            "QUANT_TDX_PATH": ("data_sources", "tdx_path"),
            "QUANT_EASTMONEY_API_KEY": ("data_sources", "eastmoney_api_key"),
            "QUANT_CACHE_ENABLED": ("data_sources", "cache_enabled"),
            
            # 数据库配置
            "QUANT_DB_PATH": ("database", "path"),
            "QUANT_DB_MEMORY_LIMIT": ("database", "memory_limit"),
            "QUANT_DB_THREADS": ("database", "threads"),
            
            # 回测配置
            "QUANT_INITIAL_CAPITAL": ("backtest", "initial_capital"),
            "QUANT_COMMISSION_RATE": ("backtest", "commission_rate"),
        }
        
        for env_var, (section_name, key) in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # 类型转换
                if section_name in self.sections and key in self.sections[section_name].items:
                    item = self.sections[section_name].items[key]
                    
                    if item.data_type == "bool":
                        value = value.lower() in ["true", "1", "yes", "y"]
                    elif item.data_type == "int":
                        try:
                            value = int(value)
                        except ValueError:
                            logger.warning(f"环境变量类型转换失败: {env_var}={value} -> int")
                            continue
                    elif item.data_type == "float":
                        try:
                            value = float(value)
                        except ValueError:
                            logger.warning(f"环境变量类型转换失败: {env_var}={value} -> float")
                            continue
                    elif item.data_type == "list":
                        value = [v.strip() for v in value.split(",")]
                    
                    # 更新配置项
                    self.sections[section_name].update_item(key, value, ConfigSource.ENV_VAR)
                    logger.debug(f"从环境变量加载配置: {section_name}.{key} = {value}")
    
    def load_from_file(self, config_path: Union[str, Path]) -> bool:
        """
        从配置文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            是否加载成功
        """
        try:
            config_path = Path(config_path)
            
            if not config_path.exists():
                logger.error(f"配置文件不存在: {config_path}")
                return False
            
            # 根据扩展名选择解析器
            if config_path.suffix.lower() in ['.json']:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            elif config_path.suffix.lower() in ['.yaml', '.yml']:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                logger.error(f"不支持的配置文件格式: {config_path.suffix}")
                return False
            
            # 更新配置
            with self._lock:
                for section_name, section_data in config_data.items():
                    if section_name in self.sections:
                        section = self.sections[section_name]
                        
                        if isinstance(section_data, dict):
                            for key, value in section_data.items():
                                if key in section.items:
                                    section.update_item(key, value, ConfigSource.FILE)
            
            self.config_path = config_path
            logger.info(f"从文件加载配置成功: {config_path}")
            
            # 开始监视配置文件变化
            self._start_config_watcher()
            
            return True
            
        except Exception as e:
            logger.error(f"从文件加载配置失败: {str(e)}")
            return False
    
    def save_to_file(self, config_path: Union[str, Path] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径，为None时使用当前配置文件路径
            
        Returns:
            是否保存成功
        """
        try:
            if config_path is None:
                if self.config_path is None:
                    logger.error("未指定配置文件路径")
                    return False
                config_path = self.config_path
            else:
                config_path = Path(config_path)
            
            # 准备配置数据
            config_data = {}
            with self._lock:
                for section_name, section in self.sections.items():
                    section_data = {}
                    for key, item in section.items.items():
                        section_data[key] = item.value
                    config_data[section_name] = section_data
            
            # 根据扩展名选择格式
            if config_path.suffix.lower() in ['.json']:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            elif config_path.suffix.lower() in ['.yaml', '.yml']:
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
            else:
                logger.error(f"不支持的配置文件格式: {config_path.suffix}")
                return False
            
            logger.info(f"配置保存成功: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置到文件失败: {str(e)}")
            return False
    
    def _start_config_watcher(self):
        """启动配置文件监视器"""
        if self.config_path is None:
            return
        
        def watch_config_file():
            """监视配置文件变化"""
            last_mtime = self.config_path.stat().st_mtime
            
            while True:
                try:
                    current_mtime = self.config_path.stat().st_mtime
                    
                    if current_mtime != last_mtime:
                        logger.info(f"配置文件发生变化: {self.config_path}")
                        last_mtime = current_mtime
                        
                        # 重新加载配置
                        if self.load_from_file(self.config_path):
                            # 触发配置变化回调
                            self._notify_config_changed()
                    
                    threading.Event().wait(self.watch_interval)
                    
                except Exception as e:
                    logger.error(f"配置文件监视失败: {str(e)}")
                    break
        
        if self._config_watcher is None or not self._config_watcher.is_alive():
            self._config_watcher = threading.Thread(
                target=watch_config_file,
                name="ConfigWatcher",
                daemon=True
            )
            self._config_watcher.start()
            logger.debug("配置文件监视器启动")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，格式: "section.key" 或 "section.subsection.key"
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            # 解析键路径
            parts = key_path.split('.')
            
            if len(parts) < 2:
                logger.error(f"无效的配置键路径: {key_path}")
                return default
            
            section_name = parts[0]
            key = parts[-1]
            
            if section_name not in self.sections:
                logger.warning(f"配置节不存在: {section_name}")
                return default
            
            return self.sections[section_name].get_item(key, default)
            
        except Exception as e:
            logger.error(f"获取配置失败: {key_path} - {str(e)}")
            return default
    
    def set(self, key_path: str, value: Any, source: ConfigSource = ConfigSource.RUNTIME) -> bool:
        """
        设置配置值
        
        Args:
            key_path: 配置键路径
            value: 配置值
            source: 配置源
            
        Returns:
            是否设置成功
        """
        try:
            # 解析键路径
            parts = key_path.split('.')
            
            if len(parts) < 2:
                logger.error(f"无效的配置键路径: {key_path}")
                return False
            
            section_name = parts[0]
            key = parts[-1]
            
            if section_name not in self.sections:
                logger.error(f"配置节不存在: {section_name}")
                return False
            
            with self._lock:
                success = self.sections[section_name].update_item(key, value, source)
                
                if success:
                    logger.debug(f"配置设置成功: {key_path} = {value}")
                    self._notify_config_changed()
                
                return success
            
        except Exception as e:
            logger.error(f"设置配置失败: {key_path} - {str(e)}")
            return False
    
    def register_config_changed_callback(self, callback: Callable[[str, Any], None]):
        """
        注册配置变化回调
        
        Args:
            callback: 回调函数，接收 (key_path, new_value) 参数
        """
        if callback not in self._config_changed_callbacks:
            self._config_changed_callbacks.append(callback)
            logger.debug(f"注册配置变化回调: {callback.__name__}")
    
    def unregister_config_changed_callback(self, callback: Callable):
        """取消注册配置变化回调"""
        if callback in self._config_changed_callbacks:
            self._config_changed_callbacks.remove(callback)
            logger.debug(f"取消注册配置变化回调: {callback.__name__}")
    
    def _notify_config_changed(self):
        """通知配置变化"""
        for callback in self._config_changed_callbacks:
            try:
                # 这里可以传递更多信息，如变化的配置项
                callback("config_changed", {})
            except Exception as e:
                logger.error(f"配置变化回调执行失败: {str(e)}")
    
    def validate_all(self) -> Dict[str, Dict[str, List[str]]]:
        """
        验证所有配置
        
        Returns:
            验证错误字典
        """
        errors = {}
        
        with self._lock:
            for section_name, section in self.sections.items():
                section_errors = section.validate_section()
                if section_errors:
                    errors[section_name] = section_errors
        
        return errors
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        config = {}
        
        with self._lock:
            for section_name, section in self.sections.items():
                config[section_name] = {}
                for key, item in section.items.items():
                    config[section_name][key] = {
                        "value": item.value,
                        "source": item.source.value,
                        "data_type": item.data_type,
                        "description": item.description,
                        "last_updated": item.last_updated.isoformat()
                    }
        
        return config
    
    def reload(self) -> bool:
        """重新加载配置"""
        if self.config_path is None:
            logger.error("未指定配置文件路径，无法重新加载")
            return False
        
        logger.info("重新加载配置")
        return self.load_from_file(self.config_path)
    
    def reset_to_defaults(self, section_name: str = None):
        """
        重置为默认值
        
        Args:
            section_name: 配置节名称，为None时重置所有配置
        """
        with self._lock:
            if section_name is None:
                # 重置所有配置
                self._load_default_config()
                self._load_env_config()
                logger.info("所有配置已重置为默认值")
            elif section_name in self.sections:
                # 重置指定配置节
                # 这里需要重新创建默认配置节
                self._load_default_config()  # 重新加载默认配置
                self._load_env_config()  # 重新加载环境配置
                logger.info(f"配置节已重置为默认值: {section_name}")
            else:
                logger.error(f"配置节不存在: {section_name}")
    
    def create_section(self, section_name: str, description: str = None) -> bool:
        """
        创建新的配置节
        
        Args:
            section_name: 配置节名称
            description: 描述
            
        Returns:
            是否创建成功
        """
        with self._lock:
            if section_name in self.sections:
                logger.warning(f"配置节已存在: {section_name}")
                return False
            
            self.sections[section_name] = ConfigSection(
                name=section_name,
                description=description
            )
            
            logger.info(f"创建配置节: {section_name}")
            return True
    
    def delete_section(self, section_name: str) -> bool:
        """删除配置节"""
        with self._lock:
            if section_name not in self.sections:
                logger.warning(f"配置节不存在: {section_name}")
                return False
            
            del self.sections[section_name]
            logger.info(f"删除配置节: {section_name}")
            return True


# 创建全局配置管理器实例
config_manager = ConfigManager()


# 便捷函数
def get_config(key_path: str, default: Any = None) -> Any:
    """获取配置值（便捷函数）"""
    return config_manager.get(key_path, default)

def set_config(key_path: str, value: Any, source: ConfigSource = ConfigSource.RUNTIME) -> bool:
    """设置配置值（便捷函数）"""
    return config_manager.set(key_path, value, source)

def load_config(config_path: Union[str, Path]) -> bool:
    """从文件加载配置（便捷函数）"""
    return config_manager.load_from_file(config_path)

def save_config(config_path: Union[str, Path] = None) -> bool:
    """保存配置到文件（便捷函数）"""
    return config_manager.save_to_file(config_path)