"""
数据源抽象层 - 基于模块化架构蓝图设计

数据源模块设计原则：
1. 插件式设计：每个数据源独立实现标准接口
2. 松耦合：通过接口与核心系统通信
3. 可替换：随时切换不同数据源，不影响其他模块
4. 统一接口：所有数据源返回标准化的数据模型

实现参考：
- injoyai/tdx算法的Python实现
- 学习EasyUp的多数据源融合思路
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class StockData:
    """统一股票数据模型（所有数据源必须遵守）"""
    stock_code: str
    date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    amount: float
    source: str  # 数据源标识
    raw_data: Optional[Dict[str, Any]] = None  # 原始数据（可选）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "stock_code": self.stock_code,
            "date": self.date.isoformat(),
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "close_price": self.close_price,
            "volume": self.volume,
            "amount": self.amount,
            "source": self.source
        }

    def validate(self) -> bool:
        """验证数据有效性"""
        if not self.stock_code or len(self.stock_code) < 2:
            return False
        
        if not self.date:
            return False
            
        if self.open_price <= 0 or self.high_price <= 0 or self.low_price <= 0 or self.close_price <= 0:
            logger.warning(f"股票{self.stock_code}价格异常: O:{self.open_price} H:{self.high_price} L:{self.low_price} C:{self.close_price}")
            return False
            
        if self.high_price < self.low_price:
            logger.error(f"股票{self.stock_code}高低价异常: H:{self.high_price} < L:{self.low_price}")
            return False
            
        return True


class DataSource(ABC):
    """数据源抽象基类（所有数据源必须实现）"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"DataSource.{name}")
        self._initialized = False
        
    @abstractmethod
    def initialize(self) -> bool:
        """初始化数据源"""
        pass
    
    @abstractmethod
    def fetch_daily_data(self, stock_code: str, start_date: str, end_date: str) -> List[StockData]:
        """获取日线数据（核心方法）"""
        pass
    
    @abstractmethod
    def fetch_realtime_data(self, stock_code: str) -> Optional[StockData]:
        """获取实时数据（可选实现）"""
        pass
    
    @abstractmethod
    def get_source_info(self) -> Dict[str, Any]:
        """获取数据源信息"""
        pass
    
    def validate_data(self, data_list: List[StockData]) -> bool:
        """批量验证数据"""
        valid_count = 0
        for data in data_list:
            if data.validate():
                valid_count += 1
            else:
                self.logger.warning(f"数据验证失败: {data.stock_code} {data.date}")
        
        total = len(data_list)
        success_rate = valid_count / total if total > 0 else 0
        
        if success_rate < 0.8:
            self.logger.error(f"数据质量过低: {success_rate:.2%} ({valid_count}/{total})")
            return False
            
        return True
    
    def __str__(self) -> str:
        return f"DataSource(name={self.name})"


class TDXDataSource(DataSource):
    """通达信数据源（基于injoyai/tdx算法）"""
    
    def __init__(self, tdx_path: str):
        super().__init__("TDX", {"tdx_path": tdx_path})
        self.tdx_path = tdx_path
        self.parser = None  # 延迟初始化
        
    def initialize(self) -> bool:
        """初始化TDX数据源"""
        try:
            # 动态导入TDX解析器（避免循环导入）
            from ..core_models.tdx_parser import TDXParser
            self.parser = TDXParser(self.tdx_path)
            
            # 测试连接
            if not self.parser.test_connection():
                self.logger.error("TDX数据路径连接失败")
                return False
                
            self._initialized = True
            self.logger.info(f"TDX数据源初始化成功: {self.tdx_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"TDX数据源初始化失败: {str(e)}")
            return False
    
    def fetch_daily_data(self, stock_code: str, start_date: str, end_date: str) -> List[StockData]:
        """获取通达信日线数据"""
        if not self._initialized or not self.parser:
            self.logger.error("TDX数据源未初始化")
            return []
            
        try:
            raw_data_list = self.parser.parse_stock_data(stock_code, start_date, end_date)
            stock_data_list = []
            
            for raw_data in raw_data_list:
                stock_data = StockData(
                    stock_code=stock_code,
                    date=raw_data.get("date"),
                    open_price=raw_data.get("open", 0.0),
                    high_price=raw_data.get("high", 0.0),
                    low_price=raw_data.get("low", 0.0),
                    close_price=raw_data.get("close", 0.0),
                    volume=raw_data.get("volume", 0),
                    amount=raw_data.get("amount", 0.0),
                    source=self.name,
                    raw_data=raw_data
                )
                
                if stock_data.validate():
                    stock_data_list.append(stock_data)
                else:
                    self.logger.warning(f"数据验证失败已跳过: {stock_code} {raw_data.get('date')}")
            
            self.logger.info(f"获取通达信数据完成: {stock_code} {len(stock_data_list)}条")
            return stock_data_list
            
        except Exception as e:
            self.logger.error(f"获取通达信数据失败: {stock_code} - {str(e)}")
            return []
    
    def fetch_realtime_data(self, stock_code: str) -> Optional[StockData]:
        """TDX数据源不支持实时数据"""
        self.logger.warning("TDX数据源不支持实时数据获取")
        return None
    
    def get_source_info(self) -> Dict[str, Any]:
        """获取TDX数据源信息"""
        return {
            "name": self.name,
            "type": "local_file",
            "path": self.tdx_path,
            "initialized": self._initialized,
            "supports_realtime": False,
            "description": "通达信本地数据文件解析"
        }


class EastMoneyDataSource(DataSource):
    """东方财富API数据源"""
    
    def __init__(self, api_key: str = None, cache_enabled: bool = True):
        super().__init__("EastMoney", {"api_key": api_key, "cache_enabled": cache_enabled})
        self.api_key = api_key
        self.cache_enabled = cache_enabled
        self.cache = {}  # 简单内存缓存
        self.rate_limiter = {}  # 简单的API限流器
        
    def initialize(self) -> bool:
        """初始化东方财富API数据源"""
        try:
            # 测试API连接
            if self.api_key:
                self.logger.info("使用API Key连接东方财富API")
            else:
                self.logger.info("使用公开API连接东方财富")
                
            self._initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"东方财富API初始化失败: {str(e)}")
            return False
    
    def fetch_daily_data(self, stock_code: str, start_date: str, end_date: str) -> List[StockData]:
        """获取东方财富日线数据"""
        if not self._initialized:
            self.logger.error("东方财富数据源未初始化")
            return []
            
        # 检查缓存
        cache_key = f"{stock_code}_{start_date}_{end_date}"
        if self.cache_enabled and cache_key in self.cache:
            self.logger.debug(f"从缓存获取数据: {cache_key}")
            return self.cache[cache_key]
        
        try:
            # 这里应该调用实际的API
            # 暂时返回模拟数据
            self.logger.warning("东方财富API未实现，返回模拟数据")
            
            # 模拟数据
            stock_data_list = []
            from datetime import datetime, timedelta
            import random
            
            current_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            
            while current_date <= end_date_obj:
                stock_data = StockData(
                    stock_code=stock_code,
                    date=current_date,
                    open_price=10.0 + random.uniform(-1, 1),
                    high_price=11.0 + random.uniform(-1, 1),
                    low_price=9.0 + random.uniform(-1, 1),
                    close_price=10.5 + random.uniform(-1, 1),
                    volume=int(1000000 * random.uniform(0.8, 1.2)),
                    amount=10000000.0 * random.uniform(0.8, 1.2),
                    source=self.name
                )
                
                if stock_data.validate():
                    stock_data_list.append(stock_data)
                    
                current_date += timedelta(days=1)
            
            # 缓存数据
            if self.cache_enabled:
                self.cache[cache_key] = stock_data_list
            
            self.logger.info(f"获取东方财富数据完成: {stock_code} {len(stock_data_list)}条")
            return stock_data_list
            
        except Exception as e:
            self.logger.error(f"获取东方财富数据失败: {stock_code} - {str(e)}")
            return []
    
    def fetch_realtime_data(self, stock_code: str) -> Optional[StockData]:
        """获取东方财富实时数据"""
        try:
            # 这里应该调用实时API
            self.logger.warning("东方财富实时API未实现，返回模拟数据")
            
            from datetime import datetime
            import random
            
            return StockData(
                stock_code=stock_code,
                date=datetime.now(),
                open_price=10.0 + random.uniform(-0.5, 0.5),
                high_price=10.5 + random.uniform(-0.5, 0.5),
                low_price=9.5 + random.uniform(-0.5, 0.5),
                close_price=10.2 + random.uniform(-0.5, 0.5),
                volume=int(500000 * random.uniform(0.9, 1.1)),
                amount=5000000.0 * random.uniform(0.9, 1.1),
                source=self.name
            )
            
        except Exception as e:
            self.logger.error(f"获取实时数据失败: {stock_code} - {str(e)}")
            return None
    
    def get_source_info(self) -> Dict[str, Any]:
        """获取东方财富数据源信息"""
        return {
            "name": self.name,
            "type": "api",
            "has_api_key": bool(self.api_key),
            "cache_enabled": self.cache_enabled,
            "initialized": self._initialized,
            "supports_realtime": True,
            "description": "东方财富API数据接口"
        }


class DataSourceFactory:
    """数据源工厂（创建和管理数据源）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.data_sources = {}
            self.default_source = None
            self._initialized = True
    
    def register_source(self, source_name: str, source_class) -> bool:
        """注册数据源类"""
        if not issubclass(source_class, DataSource):
            raise TypeError(f"{source_class} 必须是DataSource的子类")
        
        self.data_sources[source_name] = source_class
        return True
    
    def create_source(self, source_name: str, **kwargs) -> Optional[DataSource]:
        """创建数据源实例"""
        if source_name not in self.data_sources:
            logging.error(f"未知的数据源: {source_name}")
            return None
        
        try:
            source_class = self.data_sources[source_name]
            instance = source_class(**kwargs)
            
            # 初始化数据源
            if instance.initialize():
                logging.info(f"数据源创建成功: {source_name}")
                return instance
            else:
                logging.error(f"数据源初始化失败: {source_name}")
                return None
                
        except Exception as e:
            logging.error(f"创建数据源失败: {source_name} - {str(e)}")
            return None
    
    def set_default_source(self, source_name: str):
        """设置默认数据源"""
        if source_name in self.data_sources:
            self.default_source = source_name
            logging.info(f"设置默认数据源: {source_name}")
        else:
            logging.error(f"无法设置未知数据源为默认: {source_name}")
    
    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        return list(self.data_sources.keys())


# 创建全局工厂实例
data_source_factory = DataSourceFactory()

# 注册内置数据源
data_source_factory.register_source("tdx", TDXDataSource)
data_source_factory.register_source("eastmoney", EastMoneyDataSource)

# 设置TDX为默认数据源
data_source_factory.set_default_source("tdx")


def get_data_source(source_name: str = None, **kwargs) -> Optional[DataSource]:
    """
    获取数据源实例（便捷函数）
    
    Args:
        source_name: 数据源名称，如"tdx"、"eastmoney"
        **kwargs: 传递给数据源构造函数的参数
        
    Returns:
        DataSource实例或None
    """
    if source_name is None:
        source_name = data_source_factory.default_source
    
    return data_source_factory.create_source(source_name, **kwargs)