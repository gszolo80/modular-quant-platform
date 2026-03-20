#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基本使用示例 - 模块化量化平台

这个示例展示了如何使用模块化量化平台的核心功能
基于"数据是基础，做成模块化，功能只挂接"的设计原则
"""

import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from modular_quant import (
    start_platform, stop_platform, get_platform,
    get_stock_data, get_system_status
)
from modular_quant.config import load_config, save_config
from modular_quant.hook_manager import HookManager, HookType
from modular_quant.agents import Message, send_message


def example_1_basic_platform():
    """示例1：基本平台使用"""
    print("\n" + "="*60)
    print("示例1：基本平台使用")
    print("="*60)
    
    try:
        # 1. 启动平台
        print("1. 启动模块化量化平台...")
        result = start_platform()
        
        if result.get('status') == 'success':
            print(f"   ✅ 平台启动成功，版本: {result.get('version', '1.0.0')}")
        else:
            print(f"   ❌ 平台启动失败: {result.get('message')}")
            return
        
        # 2. 获取平台实例
        platform = get_platform()
        
        # 3. 查看系统状态
        print("\n2. 查看系统状态...")
        status = platform.get_system_status()
        
        print(f"   版本: {status['platform']['version']}")
        print(f"   状态: {'运行中' if status['platform']['initialized'] else '已停止'}")
        print(f"   运行环境: {status['config']['environment']}")
        print(f"   日志级别: {status['config']['log_level']}")
        
        # 4. 获取股票数据
        print("\n3. 获取股票数据...")
        try:
            # 尝试获取平安银行数据
            stock_data = platform.get_stock_data("000001.SZ", "tdx")
            print(f"   ✅ 数据获取成功: {stock_data.code}")
            print(f"   股票名称: {stock_data.name or '未知'}")
            print(f"   收盘价: {stock_data.close or '未知'}")
            print(f"   成交量: {stock_data.volume:,}" if stock_data.volume else "   成交量: 未知")
            print(f"   数据源: {stock_data.data_source}")
        except Exception as e:
            print(f"   ⚠️  数据获取失败（模拟数据）: {str(e)}")
            print("   ℹ️  实际环境中需要配置正确的数据源路径")
        
        # 5. 查看配置
        print("\n4. 查看当前配置...")
        config = platform.config.get_all_config()
        print(f"   配置节数量: {len(config)}")
        print(f"   当前数据源: {platform.config.get('data_sources.default_source', '未配置')}")
        print(f"   回测初始资金: ¥{platform.config.get('backtest.initial_capital', 0):,.2f}")
        
        # 6. 停止平台
        print("\n5. 停止平台...")
        stop_result = platform.stop()
        
        if stop_result.get('status') == 'success':
            print("   ✅ 平台停止成功")
        else:
            print(f"   ❌ 平台停止失败: {stop_result.get('message')}")
            
        return True
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        return False


def example_2_custom_hooks():
    """示例2：自定义钩子"""
    print("\n" + "="*60)
    print("示例2：自定义钩子")
    print("="*60)
    
    try:
        # 1. 启动平台
        print("1. 启动平台...")
        platform = get_platform()
        platform.start()
        
        # 2. 定义自定义钩子函数
        def on_data_fetched(stock_data):
            """自定义数据获取钩子"""
            print(f"   🔔 自定义钩子: 数据获取完成 - {stock_data.code}")
            if stock_data.close:
                print(f"      收盘价: ¥{stock_data.close:.2f}")
            return {"processed": True, "hook_type": "custom"}
        
        def on_system_error(error_info):
            """自定义错误处理钩子"""
            print(f"   🔔 自定义钩子: 系统错误 - {error_info.get('error_type', 'Unknown')}")
            print(f"      错误信息: {error_info.get('error_message', 'No message')}")
            return {"handled": True, "recovery_action": "log_only"}
        
        # 3. 注册自定义钩子
        print("\n2. 注册自定义钩子...")
        
        # 注册数据获取后钩子
        platform.register_custom_hook(HookType.DATA_AFTER_FETCH, on_data_fetched, priority=75)
        print("   ✅ 注册数据获取钩子")
        
        # 注册错误处理钩子
        platform.register_custom_hook(HookType.ERROR_OCCURRED, on_system_error, priority=60)
        print("   ✅ 注册错误处理钩子")
        
        # 4. 触发钩子执行
        print("\n3. 触发钩子执行...")
        
        # 模拟数据获取（会触发钩子）
        print("   模拟数据获取操作...")
        try:
            # 创建模拟股票数据
            from modular_quant.core_models import StockData
            from datetime import datetime
            
            mock_data = StockData(
                code="000001.SZ",
                name="平安银行",
                timestamp=datetime.now(),
                open=10.5,
                close=10.8,
                high=11.0,
                low=10.3,
                volume=10000000,
                amount=108000000,
                turnover_rate=0.015,
                data_source="mock"
            )
            
            # 执行数据获取钩子
            hook_results = platform.hook_manager.execute(
                hook_type=HookType.DATA_AFTER_FETCH,
                stock_data=mock_data
            )
            
            print(f"   钩子执行结果: {len(hook_results)} 个钩子被执行")
            
        except Exception as e:
            print(f"   钩子执行测试失败: {str(e)}")
        
        # 5. 查看钩子状态
        print("\n4. 查看钩子状态...")
        if hasattr(platform, 'hook_manager') and hasattr(platform.hook_manager, 'hooks'):
            hook_count = sum(len(hook_list) for hook_list in platform.hook_manager.hooks.values())
            print(f"   已注册钩子数量: {hook_count}")
        
        # 6. 清理
        print("\n5. 清理...")
        platform.stop()
        print("   ✅ 平台停止完成")
        
        return True
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        return False


def example_3_agent_communication():
    """示例3：Agent通信"""
    print("\n" + "="*60)
    print("示例3：Agent通信")
    print("="*60)
    
    try:
        # 1. 启动平台
        print("1. 启动平台并启用Agent...")
        
        # 修改配置，启用Agent
        from modular_quant.config import set_config
        set_config("agents.enabled_agents", ["data_collector", "strategy_analyzer"])
        
        platform = get_platform()
        platform.start()
        
        # 2. 查看Agent状态
        print("\n2. 查看Agent状态...")
        status = platform.get_system_status()
        agents = status.get('agents', {})
        
        print(f"   已启用Agent: {', '.join(agents.get('enabled', []))}")
        print(f"   运行中Agent: {', '.join(agents.get('running', []))}")
        
        # 3. 发送测试消息
        print("\n3. 发送测试消息...")
        
        # 创建测试消息
        test_message = Message(
            sender="ExampleScript",
            receiver="DataCollectorAgent",
            message_type="TEST_MESSAGE",
            content={
                "test_id": "example_001",
                "timestamp": "2026-03-21T01:00:00",
                "data": "This is a test message"
            }
        )
        
        # 发送消息
        try:
            response = send_message(test_message)
            if response:
                print(f"   ✅ 消息发送成功，收到响应")
                print(f"      响应类型: {response.message_type}")
                print(f"      发送者: {response.sender}")
            else:
                print("   ⚠️  消息发送成功，但未收到响应")
        except Exception as e:
            print(f"   ⚠️  消息发送失败（可能Agent未运行）: {str(e)}")
        
        # 4. Agent统计信息
        print("\n4. Agent统计信息...")
        if hasattr(platform, 'agent_manager'):
            stats = platform.agent_manager.get_stats()
            print(f"   消息处理总数: {stats.get('total_messages_processed', 0)}")
            print(f"   平均处理时间: {stats.get('avg_processing_time', 0):.3f}秒")
            print(f"   活跃Agent数量: {stats.get('active_agents', 0)}")
        
        # 5. 停止平台
        print("\n5. 停止平台...")
        platform.stop()
        print("   ✅ 平台停止完成")
        
        return True
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        return False


def example_4_config_management():
    """示例4：配置管理"""
    print("\n" + "="*60)
    print("示例4：配置管理")
    print("="*60)
    
    try:
        # 1. 获取配置管理器
        print("1. 配置管理操作...")
        from modular_quant.config import config_manager
        
        # 2. 获取配置值
        print("\n2. 获取配置值...")
        
        env = config_manager.get("system.environment", "development")
        debug = config_manager.get("system.debug", False)
        log_level = config_manager.get("system.log_level", "INFO")
        
        print(f"   运行环境: {env}")
        print(f"   调试模式: {debug}")
        print(f"   日志级别: {log_level}")
        
        # 3. 动态修改配置
        print("\n3. 动态修改配置...")
        
        # 修改日志级别
        old_level = log_level
        new_level = "DEBUG" if log_level != "DEBUG" else "INFO"
        
        success = config_manager.set("system.log_level", new_level)
        if success:
            print(f"   ✅ 配置修改成功: system.log_level = {old_level} -> {new_level}")
        else:
            print(f"   ❌ 配置修改失败")
        
        # 验证修改
        current_level = config_manager.get("system.log_level")
        print(f"   当前日志级别: {current_level}")
        
        # 4. 创建新配置节
        print("\n4. 创建自定义配置节...")
        
        # 检查是否已存在
        if "custom" not in config_manager.sections:
            config_manager.create_section("custom", "自定义配置节")
            print("   ✅ 创建配置节: custom")
            
            # 添加自定义配置项
            from modular_quant.config import ConfigItem, ConfigSource
            from enum import Enum
            
            # 临时定义ConfigSource
            class TempConfigSource(Enum):
                DEFAULT = "default"
                RUNTIME = "runtime"
            
            custom_item = ConfigItem(
                key="example_setting",
                value="custom_value",
                source=TempConfigSource.DEFAULT,
                data_type="str",
                description="示例自定义配置"
            )
            
            config_manager.sections["custom"].add_item(custom_item)
            print("   ✅ 添加自定义配置项: custom.example_setting")
        
        # 5. 导出配置
        print("\n5. 导出配置...")
        
        # 获取所有配置
        all_config = config_manager.get_all_config()
        config_sections = len(all_config)
        total_items = sum(len(section.get('items', {})) for section in all_config.values())
        
        print(f"   配置节数量: {config_sections}")
        print(f"   配置项总数: {total_items}")
        
        # 6. 验证配置
        print("\n6. 验证配置...")
        validation_errors = config_manager.validate_all()
        
        if validation_errors:
            print(f"   ⚠️  配置验证发现 {len(validation_errors)} 个错误")
            for section, errors in validation_errors.items():
                print(f"      {section}: {len(errors)} 个错误")
        else:
            print("   ✅ 所有配置验证通过")
        
        return True
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        return False


def example_5_backtest_simulation():
    """示例5：回测模拟"""
    print("\n" + "="*60)
    print("示例5：回测模拟")
    print("="*60)
    
    try:
        # 1. 启动平台
        print("1. 启动平台...")
        platform = get_platform()
        platform.start()
        
        # 2. 准备回测策略配置
        print("\n2. 准备回测策略...")
        
        strategy_config = {
            "strategy_name": "MA_Cross_Example",
            "stock_codes": ["000001.SZ", "000002.SZ"],
            "start_date": "2025-01-01",
            "end_date": "2026-01-01",
            "parameters": {
                "short_period": 5,
                "long_period": 20,
                "commission_rate": 0.0003,
                "slippage": 0.001
            }
        }
        
        print(f"   策略名称: {strategy_config['strategy_name']}")
        print(f"   股票列表: {', '.join(strategy_config['stock_codes'])}")
        print(f"   时间范围: {strategy_config['start_date']} 到 {strategy_config['end_date']}")
        print(f"   初始资金: ¥{platform.config.get('backtest.initial_capital', 100000):,.2f}")
        
        # 3. 运行回测
        print("\n3. 运行回测...")
        try:
            result = platform.run_backtest(strategy_config)
            
            print("   ✅ 回测执行成功")
            print(f"   策略名称: {result.strategy_name}")
            print(f"   总收益率: {result.total_return:.2%}")
            print(f"   年化收益率: {result.annual_return:.2%}")
            print(f"   最大回撤: {result.max_drawdown:.2%}")
            print(f"   夏普比率: {result.sharpe_ratio:.2f}")
            print(f"   胜率: {result.win_rate:.2%}")
            print(f"   总交易次数: {result.total_trades}")
            print(f"   盈利交易次数: {result.profitable_trades}")
            
            # 显示性能指标
            if result.performance_metrics:
                print(f"   其他指标: {len(result.performance_metrics)} 个")
                
        except Exception as e:
            print(f"   ⚠️  回测执行失败（模拟）: {str(e)}")
            print("   ℹ️  实际回测需要真实的历史数据")
        
        # 4. 停止平台
        print("\n4. 停止平台...")
        platform.stop()
        print("   ✅ 平台停止完成")
        
        return True
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        return False


def main():
    """主函数 - 运行所有示例"""
    print("="*70)
    print("模块化量化平台 - 基本使用示例")
    print("基于设计原则: 数据是基础，做成模块化，功能只挂接")
    print("="*70)
    
    # 记录开始时间
    import time
    start_time = time.time()
    
    # 运行所有示例
    examples = [
        ("基本平台使用", example_1_basic_platform),
        ("自定义钩子", example_2_custom_hooks),
        ("Agent通信", example_3_agent_communication),
        ("配置管理", example_4_config_management),
        ("回测模拟", example_5_backtest_simulation)
    ]
    
    results = []
    
    for name, func in examples:
        print(f"\n🚀 开始示例: {name}")
        success = func()
        results.append((name, success))
    
    # 显示总结
    print("\n" + "="*70)
    print("示例执行总结")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    failed = total - passed
    
    print(f"总示例数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    
    # 显示详细结果
    for i, (name, success) in enumerate(results, 1):
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{i}. {name}: {status}")
    
    # 计算总耗时
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f}秒")
    
    # 平台信息
    print("\n" + "="*70)
    print("平台信息")
    print("="*70)
    
    from modular_quant import __version__, __description__, __author__
    
    print(f"版本: {__version__}")
    print(f"作者: {__author__}")
    
    # 显示简短描述
    desc_lines = __description__.strip().split('\n')
    for line in desc_lines[:3]:
        if line.strip():
            print(line.strip())
    
    print("\n" + "="*70)
    print("🎉 示例执行完成！")
    print("="*70)
    
    if failed == 0:
        print("\n所有示例均执行成功！模块化量化平台功能正常。")
        print("您可以开始使用平台进行量化分析了！")
    else:
        print(f"\n有 {failed} 个示例执行失败，请检查相关配置。")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n程序执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)