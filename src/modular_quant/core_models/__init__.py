"""
核心数据模型层 - 基于模块化架构蓝图设计

核心模型设计原则：
1. 数据标准化：所有模块使用统一的数据模型
2. 类型安全：完整类型注解，减少运行时错误
3. 可序列化：支持JSON、数据库等持久化
4. 验证机制：内置数据验证和完整性检查

实现参考：
- 学习KHQuant 3.2的数据分层架构
- 融合injoyai/tdx的数据验证机制
- 借鉴daily_stock_analysis的多维度分析模型
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class MarketType(Enum):
    """市场类型枚举"""
    SHANGHAI = "SH"  # 上海证券交易所
    SHENZHEN = "SZ"  # 深圳证券交易所
    BEIJING = "BJ"   # 北京证券交易所
    HK = "HK"        # 香港交易所
    US = "US"        # 美国交易所


class StockType(Enum):
    """股票类型枚举"""
    STOCK = "stock"          # 普通股票
    FUND = "fund"            # 基金
    BOND = "bond"            # 债券
    ETF = "etf"              # ETF
    INDEX = "index"          # 指数
    FUTURE = "future"        # 期货
    OPTION = "option"        # 期权


@dataclass
class BaseModel:
    """所有数据模型的基类"""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str):
        """从JSON字符串创建实例"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class StockInfo(BaseModel):
    """股票基本信息"""
    code: str                     # 股票代码
    name: str                     # 股票名称
    market: MarketType            # 市场类型
    stock_type: StockType         # 股票类型
    industry: Optional[str] = None  # 行业分类
    full_name: Optional[str] = None # 全称
    listing_date: Optional[date] = None  # 上市日期
    delisting_date: Optional[date] = None # 退市日期
    is_active: bool = True        # 是否活跃
    
    def validate(self) -> bool:
        """验证基本信息"""
        if not self.code or len(self.code) < 2:
            return False
            
        if not self.name or len(self.name.strip()) == 0:
            return False
            
        return True


@dataclass
class KLineData(BaseModel):
    """K线数据（日线/分钟线）"""
    stock_code: str               # 股票代码
    date: datetime                # 日期时间
    open: float                   # 开盘价
    high: float                   # 最高价
    low: float                    # 最低价
    close: float                  # 收盘价
    volume: int                   # 成交量（股数）
    amount: float                 # 成交金额（元）
    pre_close: Optional[float] = None  # 前收盘价
    change: Optional[float] = None     # 涨跌额
    change_pct: Optional[float] = None # 涨跌幅（%）
    turnover_rate: Optional[float] = None  # 换手率（%）
    
    def validate(self) -> bool:
        """验证K线数据有效性"""
        if not self.stock_code or len(self.stock_code) < 2:
            logger.error("股票代码无效")
            return False
            
        if not self.date:
            logger.error("日期无效")
            return False
            
        # 价格验证
        if self.open <= 0 or self.high <= 0 or self.low <= 0 or self.close <= 0:
            logger.warning(f"价格异常: O:{self.open} H:{self.high} L:{self.low} C:{self.close}")
            return False
            
        # 高低价关系验证
        if self.high < self.low:
            logger.error(f"高低价关系异常: H:{self.high} < L:{self.low}")
            return False
            
        if self.high < self.open or self.high < self.close:
            logger.error(f"最高价小于开盘或收盘价")
            return False
            
        if self.low > self.open or self.low > self.close:
            logger.error(f"最低价大于开盘或收盘价")
            return False
            
        # 成交量验证
        if self.volume < 0:
            logger.error("成交量不能为负")
            return False
            
        if self.amount < 0:
            logger.error("成交金额不能为负")
            return False
            
        return True
    
    def calculate_returns(self) -> Dict[str, float]:
        """计算收益率相关指标"""
        if self.pre_close is None or self.pre_close == 0:
            return {}
            
        change = self.close - self.pre_close
        change_pct = (change / self.pre_close) * 100
        
        return {
            "change": change,
            "change_pct": change_pct
        }


@dataclass
class TechnicalIndicators(BaseModel):
    """技术指标数据"""
    stock_code: str
    date: datetime
    
    # 移动平均线
    ma5: Optional[float] = None   # 5日移动平均
    ma10: Optional[float] = None  # 10日移动平均
    ma20: Optional[float] = None  # 20日移动平均
    ma30: Optional[float] = None  # 30日移动平均
    ma60: Optional[float] = None  # 60日移动平均
    
    # MACD指标
    macd: Optional[float] = None        # MACD值
    macd_signal: Optional[float] = None # MACD信号线
    macd_hist: Optional[float] = None   # MACD柱状图
    
    # RSI指标
    rsi6: Optional[float] = None   # 6日RSI
    rsi12: Optional[float] = None  # 12日RSI
    rsi24: Optional[float] = None  # 24日RSI
    
    # BOLL指标
    boll_upper: Optional[float] = None  # 布林上轨
    boll_middle: Optional[float] = None # 布林中轨
    boll_lower: Optional[float] = None  # 布林下轨
    
    # KDJ指标
    kdj_k: Optional[float] = None  # K值
    kdj_d: Optional[float] = None  # D值
    kdj_j: Optional[float] = None  # J值
    
    # 成交量指标
    volume_ma5: Optional[int] = None    # 5日平均成交量
    volume_ma10: Optional[int] = None   # 10日平均成交量
    volume_ratio: Optional[float] = None # 成交量比率
    
    # 自定义指标
    custom_indicators: Dict[str, float] = field(default_factory=dict)
    
    def get_indicators_dict(self) -> Dict[str, float]:
        """获取所有技术指标（排除自定义指标）"""
        indicators = {}
        
        for field_name, field_value in self.__dict__.items():
            if field_name not in ['stock_code', 'date', 'custom_indicators']:
                if field_value is not None:
                    indicators[field_name] = field_value
        
        # 添加自定义指标
        indicators.update(self.custom_indicators)
        
        return indicators


@dataclass
class TradingSignal(BaseModel):
    """交易信号"""
    stock_code: str
    signal_date: datetime
    signal_type: str              # 信号类型：buy/sell/hold
    signal_strength: float        # 信号强度（0-1）
    strategy_name: str            # 策略名称
    confidence: float = 0.5       # 置信度（0-1）
    price: Optional[float] = None # 触发价格
    volume: Optional[int] = None  # 建议成交量
    reason: Optional[str] = None  # 信号原因
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def validate(self) -> bool:
        """验证交易信号"""
        if self.signal_type not in ['buy', 'sell', 'hold']:
            logger.error(f"无效的信号类型: {self.signal_type}")
            return False
            
        if not 0 <= self.signal_strength <= 1:
            logger.error(f"信号强度必须在0-1之间: {self.signal_strength}")
            return False
            
        if not 0 <= self.confidence <= 1:
            logger.error(f"置信度必须在0-1之间: {self.confidence}")
            return False
            
        return True


@dataclass
class BacktestResult(BaseModel):
    """回测结果"""
    strategy_name: str            # 策略名称
    stock_code: str               # 股票代码
    start_date: datetime          # 回测开始日期
    end_date: datetime            # 回测结束日期
    initial_capital: float        # 初始资金
    final_capital: float          # 最终资金
    total_return: float           # 总收益率
    annual_return: float          # 年化收益率
    max_drawdown: float           # 最大回撤
    sharpe_ratio: float           # 夏普比率
    win_rate: float               # 胜率
    profit_factor: float          # 盈利因子
    total_trades: int             # 总交易次数
    winning_trades: int           # 盈利交易次数
    losing_trades: int            # 亏损交易次数
    avg_profit: float             # 平均盈利
    avg_loss: float               # 平均亏损
    
    # 交易记录
    trades: List[Dict[str, Any]] = field(default_factory=list)
    
    # 净值曲线
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    
    # 配置参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_summary(self) -> Dict[str, Any]:
        """计算回测结果摘要"""
        return {
            "strategy_name": self.strategy_name,
            "stock_code": self.stock_code,
            "period": f"{self.start_date.date()} - {self.end_date.date()}",
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": f"{self.total_return:.2%}",
            "annual_return": f"{self.annual_return:.2%}",
            "max_drawdown": f"{self.max_drawdown:.2%}",
            "sharpe_ratio": f"{self.sharpe_ratio:.2f}",
            "win_rate": f"{self.win_rate:.2%}",
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades
        }


@dataclass
class Portfolio(BaseModel):
    """投资组合"""
    portfolio_id: str             # 组合ID
    name: str                     # 组合名称
    description: Optional[str] = None  # 组合描述
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 持仓
    holdings: List[Dict[str, Any]] = field(default_factory=list)
    
    # 资金情况
    cash: float = 0.0            # 现金
    total_value: float = 0.0     # 总价值
    profit_loss: float = 0.0     # 盈亏
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """计算组合统计信息"""
        total_holdings_value = sum(h.get('market_value', 0) for h in self.holdings)
        
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "total_value": self.total_value,
            "cash": self.cash,
            "holdings_value": total_holdings_value,
            "holdings_count": len(self.holdings),
            "profit_loss": self.profit_loss,
            "profit_loss_pct": (self.profit_loss / self.total_value) * 100 if self.total_value > 0 else 0
        }


@dataclass
class SystemEvent(BaseModel):
    """系统事件（用于模块间通信）"""
    event_id: str                 # 事件ID
    event_type: str               # 事件类型
    source: str                   # 事件源
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)  # 事件数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_message(self) -> Dict[str, Any]:
        """转换为消息格式（用于消息总线）"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata
        }


# 全局配置
@dataclass
class SystemConfig(BaseModel):
    """系统全局配置"""
    # 数据源配置
    data_sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 数据库配置
    database: Dict[str, Any] = field(default_factory=dict)
    
    # 回测配置
    backtest: Dict[str, Any] = field(default_factory=dict)
    
    # 策略配置
    strategies: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 通知配置
    notifications: Dict[str, Any] = field(default_factory=dict)
    
    # 系统参数
    system_params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load_from_file(cls, config_path: str):
        """从配置文件加载"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return cls.from_dict(config_data)
        except Exception as e:
            logger.error(f"加载配置文件失败: {config_path} - {str(e)}")
            return cls()
    
    def save_to_file(self, config_path: str):
        """保存到配置文件"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {config_path} - {str(e)}")
            return False


# 数据验证器
class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_kline_data(kline_data: KLineData) -> List[str]:
        """验证K线数据并返回错误列表"""
        errors = []
        
        if not kline_data.stock_code or len(kline_data.stock_code) < 2:
            errors.append("股票代码无效")
            
        if not kline_data.date:
            errors.append("日期无效")
            
        # 价格逻辑验证
        if kline_data.open <= 0:
            errors.append(f"开盘价必须大于0: {kline_data.open}")
            
        if kline_data.high < kline_data.open:
            errors.append(f"最高价小于开盘价: {kline_data.high} < {kline_data.open}")
            
        if kline_data.low > kline_data.open:
            errors.append(f"最低价大于开盘价: {kline_data.low} > {kline_data.open}")
            
        if kline_data.high < kline_data.close:
            errors.append(f"最高价小于收盘价: {kline_data.high} < {kline_data.close}")
            
        if kline_data.low > kline_data.close:
            errors.append(f"最低价大于收盘价: {kline_data.low} > {kline_data.close}")
            
        if kline_data.volume < 0:
            errors.append(f"成交量不能为负: {kline_data.volume}")
            
        if kline_data.amount < 0:
            errors.append(f"成交金额不能为负: {kline_data.amount}")
            
        return errors
    
    @staticmethod
    def validate_stock_info(stock_info: StockInfo) -> List[str]:
        """验证股票信息"""
        errors = []
        
        if not stock_info.code:
            errors.append("股票代码不能为空")
            
        if not stock_info.name or len(stock_info.name.strip()) == 0:
            errors.append("股票名称不能为空")
            
        return errors


# 工厂函数
def create_stock_info(
    code: str,
    name: str,
    market: Union[MarketType, str],
    stock_type: Union[StockType, str] = StockType.STOCK,
    **kwargs
) -> StockInfo:
    """创建股票信息实例"""
    # 转换市场类型
    if isinstance(market, str):
        market = MarketType(market)
    
    # 转换股票类型
    if isinstance(stock_type, str):
        stock_type = StockType(stock_type)
    
    return StockInfo(
        code=code,
        name=name,
        market=market,
        stock_type=stock_type,
        **kwargs
    )