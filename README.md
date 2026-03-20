# Modular Quant - 模块化量化平台

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

## 🎯 核心理念

**"数据是基础，做成模块化，功能只挂接"**

这是一个基于现代化软件工程原则设计的模块化量化分析平台，融合了四大优秀项目的核心精华：

1. **injoyai/tdx** - 专业的通达信数据解析算法
2. **KHQuant 3.2** - 先进的DuckDB数据库架构设计  
3. **daily_stock_analysis** - 智能的AI驱动分析框架
4. **EasyUp** - 生产级Agent驱动的量化交易系统架构

## ✨ 特色功能

### 🔌 **插件式数据源**
- 通达信本地数据（高精度历史数据）
- 东方财富API（实时行情数据）
- AkShare（开源财经数据接口）
- 支持自定义数据源扩展

### ⚙️ **模块化架构**
- 数据采集、策略分析、回测验证、报告生成完全分离
- 每个模块独立开发、测试、部署
- 职责单一，高内聚低耦合

### 🎯 **事件驱动**
- 钩子管理器实现功能挂接
- 模块间通过事件总线通信
- 支持异步处理和实时响应

### 🤖 **Agent驱动**
- 基于消息总线的智能Agent协作框架
- DataCollectorAgent、StrategyAnalyzerAgent、ReportGeneratorAgent
- 支持自定义Agent扩展

### 📊 **专业分析**
- 技术指标计算（MA、RSI、MACD、布林带等）
- 多维度综合分析
- AI驱动决策建议

### 🔒 **企业级部署**
- Docker容器化支持
- 生产级稳定性和可维护性
- 完善的日志和监控系统

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/gszolo80/modular-quant.git
cd modular-quant

# 安装依赖
pip install -e .

# 或安装完整版本
pip install -e ".[full]"
```

### 基本使用

```python
from modular_quant import start_platform, get_stock_data

# 启动平台
platform = start_platform("config.yaml")

# 获取股票数据
data = get_stock_data("000001.SZ", "tdx")
print(f"平安银行收盘价: {data.close}")

# 获取系统状态
status = platform.get_system_status()
print(f"平台状态: {status}")
```

### 命令行使用

```bash
# 启动平台
mq start --config config.yaml

# 获取股票数据
mq get-data 000001.SZ --source tdx

# 查看系统状态
mq status

# 运行回测
mq backtest --strategy ma_cross --start 2023-01-01 --end 2024-01-01
```

## 📁 项目结构

```
modular_quant/
├── 📂 src/modular_quant/          # 源代码
│   ├── 📂 config/                 # 配置管理
│   │   └── __init__.py           # 配置管理器
│   ├── 📂 data_sources/          # 数据源模块
│   │   └── __init__.py           # 数据源抽象和实现
│   ├── 📂 core_models/           # 核心数据模型
│   │   ├── __init__.py           # 标准数据模型
│   │   └── tdx_parser.py         # TDX解析器
│   ├── 📂 hook_manager/          # 钩子管理
│   │   └── __init__.py           # 钩子管理器
│   ├── 📂 agents/                # Agent协调层
│   │   └── __init__.py           # Agent框架实现
│   ├── __init__.py               # 主平台模块
│   └── cli.py                    # 命令行接口
├── 📂 examples/                  # 示例代码
│   ├── basic_usage.py           # 基本使用示例
│   ├── custom_hook.py           # 自定义钩子示例
│   └── custom_agent.py          # 自定义Agent示例
├── 📂 tests/                     # 测试代码
├── 📂 docs/                      # 文档
├── 📄 pyproject.toml            # 现代Python项目配置
├── 📄 setup.py                  # 传统安装配置
├── 📄 requirements.txt          # 依赖列表
├── 📄 README.md                 # 项目说明
└── 📄 LICENSE                   # MIT许可证
```

## 🔧 核心模块详解

### 1. 配置管理器 (`config/`)
- 分层配置：系统级、模块级、实例级
- 动态更新：支持运行时配置热更新
- 环境感知：开发、测试、生产环境配置
- 验证机制：配置项类型和范围检查

### 2. 数据源模块 (`data_sources/`)
- 抽象数据源接口 (`DataSource`)
- 通达信数据源 (`TDXDataSource`)
- 东方财富API数据源 (`EastMoneyDataSource`)
- 工厂模式创建数据源 (`DataSourceFactory`)

### 3. 核心数据模型 (`core_models/`)
- 标准股票数据模型 (`StockData`, `KLineData`)
- 技术指标模型 (`TechnicalIndicators`)
- 交易信号模型 (`TradingSignal`)
- 回测结果模型 (`BacktestResult`)
- 专业TDX解析器 (`TDXParser`)

### 4. 钩子管理器 (`hook_manager/`)
- 钩子注册和执行机制
- 优先级控制（0-100）
- 同步/异步钩子支持
- 错误处理和重试机制

### 5. Agent协调层 (`agents/`)
- 消息总线 (`MessageBus`)
- Agent基类 (`AgentBase`)
- Agent管理器 (`AgentManager`)
- 预置Agent：数据收集、策略分析、报告生成

## 🔌 扩展指南

### 添加自定义数据源

```python
from modular_quant.data_sources import DataSource

class MyCustomDataSource(DataSource):
    """自定义数据源实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    def fetch_stock_data(self, stock_code: str) -> StockData:
        # 实现数据获取逻辑
        pass
    
    def validate_connection(self) -> bool:
        # 验证连接状态
        pass

# 注册数据源
from modular_quant.data_sources import DataSourceFactory
DataSourceFactory.register_data_source("custom", MyCustomDataSource)
```

### 添加自定义钩子

```python
from modular_quant import get_platform, HookType

def my_custom_hook(stock_data: StockData) -> Dict[str, Any]:
    """自定义数据获取后钩子"""
    print(f"数据获取: {stock_data.code}")
    return {"processed": True}

# 注册钩子
platform = get_platform()
platform.register_custom_hook(HookType.DATA_AFTER_FETCH, my_custom_hook, priority=50)
```

### 添加自定义Agent

```python
from modular_quant.agents import AgentBase, Message

class MyCustomAgent(AgentBase):
    """自定义Agent实现"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
    def process_message(self, message: Message) -> Optional[Message]:
        # 处理消息逻辑
        pass
    
    def on_start(self):
        # Agent启动逻辑
        pass
    
    def on_stop(self):
        # Agent停止逻辑
        pass

# 注册Agent
from modular_quant import get_platform
platform = get_platform()
platform.register_custom_agent("custom_agent", MyCustomAgent)
```

## 📊 配置示例

### config.yaml
```yaml
# 系统配置
system:
  name: "Modular Quant Platform"
  version: "1.0.0"
  environment: "development"  # development/testing/production
  debug: true
  log_level: "INFO"

# 数据源配置
data_sources:
  default_source: "tdx"
  tdx_path: "/Volumes/[C] Windows 10/new_tdx64/"
  eastmoney_api_key: ""
  cache_enabled: true
  cache_ttl: 3600

# 数据库配置
database:
  engine: "duckdb"
  path: "stocks.duckdb"
  memory_limit: "4GB"
  threads: 4

# 回测配置
backtest:
  initial_capital: 100000.0
  commission_rate: 0.0003
  slippage: 0.001
  default_strategies:
    - "ma_cross"
    - "macd"
    - "rsi"

# Agent配置
agents:
  enabled_agents:
    - "data_collector"
    - "strategy_analyzer"
    - "report_generator"
  heartbeat_interval: 30
  message_timeout: 60
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试模块
pytest tests/test_data_sources.py

# 运行测试并生成覆盖率报告
pytest --cov=modular_quant

# 运行集成测试
pytest -m integration
```

## 📈 性能优化

### 数据库优化
- 使用DuckDB进行高性能数据查询
- 列式存储和向量化计算
- 内存管理和缓存策略

### 并发处理
- 异步钩子执行
- Agent并行处理
- 线程池和连接池

### 内存管理
- 数据分块加载
- 缓存机制
- 垃圾回收优化

## 🤝 贡献指南

我们欢迎所有形式的贡献！请参考以下步骤：

1. **Fork 项目**
2. **创建功能分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **开启 Pull Request**

### 开发规范
- 代码风格遵循 Black 和 isort
- 类型注解使用 mypy 检查
- 所有新功能需附带测试
- 文档字符串遵循 Google 风格

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

### 参考项目
- **[injoyai/tdx](https://github.com/injoyai/tdx)** - 专业的通达信数据解析算法
- **[KHQuant 3.2](https://github.com/khquant/khquant)** - 先进的DuckDB数据库架构设计
- **[daily_stock_analysis](https://github.com/daily_stock_analysis)** - 智能的AI驱动分析框架
- **[EasyUp](https://github.com/easyup)** - 生产级Agent驱动的量化交易系统架构

### 设计原则
- **数据是基础**：数据层独立，支持任意数据源替换
- **功能模块化**：每个功能独立开发、测试、部署
- **只挂接不耦合**：功能间通过事件/钩子连接，避免直接依赖

## 📞 联系与支持

- **GitHub Issues**: [报告问题或请求功能](https://github.com/gszolo80/modular-quant/issues)
- **作者邮箱**: 7004830@qq.com
- **GitHub**: [gszolo80](https://github.com/gszolo80)

## 🚀 路线图

### v1.0.0 (当前版本)
- [x] 基础模块化架构
- [x] 数据源抽象层
- [x] 钩子管理系统
- [x] Agent协调框架
- [x] 基础回测功能

### v1.1.0 (规划中)
- [ ] Web界面开发
- [ ] 更多技术指标
- [ ] AI分析集成
- [ ] 分布式部署支持

### v2.0.0 (规划中)
- [ ] 实盘交易接口
- [ ] 风险管理模块
- [ ] 社区策略市场
- [ ] 云服务平台

---

**♑ 黄金一言，价值万两。万两出击，必中黄金 ♑**

*站在巨人肩膀上，我们会做得更好！*