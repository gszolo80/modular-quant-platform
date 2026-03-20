#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模块化量化平台命令行接口

提供便捷的命令行操作，支持平台启动、数据获取、回测运行等功能
"""

import click
import yaml
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# 导入平台模块
from . import (
    start_platform, stop_platform, get_platform, 
    get_stock_data, get_system_status, ModularQuantPlatform
)
from .config import load_config, save_config, get_config, set_config


@click.group()
@click.version_option()
def cli():
    """模块化量化平台 - 数据是基础，做成模块化，功能只挂接"""
    pass


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='配置文件路径')
@click.option('--env', '-e', type=click.Choice(['dev', 'test', 'prod']), 
              default='dev', help='运行环境')
def start(config: Optional[str], env: str):
    """启动量化平台"""
    try:
        # 如果指定了配置文件，先加载
        if config:
            load_config(config)
        
        # 设置环境
        set_config('system.environment', 'development' if env == 'dev' else 
                  'testing' if env == 'test' else 'production')
        
        # 启动平台
        result = start_platform(config)
        
        if result.get('status') == 'success':
            click.echo(click.style('✅ 量化平台启动成功', fg='green'))
            click.echo(f"版本: {result.get('version', '1.0.0')}")
            
            # 显示系统状态
            status = get_system_status()
            click.echo(f"运行环境: {status.get('config', {}).get('environment', 'unknown')}")
            click.echo(f"日志级别: {status.get('config', {}).get('log_level', 'INFO')}")
        else:
            click.echo(click.style('❌ 量化平台启动失败', fg='red'))
            click.echo(f"错误: {result.get('message', '未知错误')}")
            
    except Exception as e:
        click.echo(click.style(f'❌ 启动失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
def stop():
    """停止量化平台"""
    try:
        result = stop_platform()
        
        if result.get('status') == 'success':
            click.echo(click.style('✅ 量化平台停止成功', fg='green'))
        else:
            click.echo(click.style('❌ 量化平台停止失败', fg='red'))
            click.echo(f"错误: {result.get('message', '未知错误')}")
            
    except Exception as e:
        click.echo(click.style(f'❌ 停止失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
def status():
    """查看系统状态"""
    try:
        status_info = get_system_status()
        
        if status_info.get('status') == 'platform_not_initialized':
            click.echo(click.style('⚠️  量化平台未启动', fg='yellow'))
            return
        
        # 平台基本信息
        platform_info = status_info.get('platform', {})
        click.echo(click.style('📊 系统状态信息', fg='cyan', bold=True))
        click.echo(f"版本: {platform_info.get('version', '未知')}")
        click.echo(f"状态: {click.style('运行中', fg='green') if platform_info.get('initialized') else click.style('已停止', fg='red')}")
        
        if platform_info.get('initialized'):
            click.echo(f"启动时间: {platform_info.get('startup_time', '未知')}")
            click.echo(f"运行时长: {platform_info.get('running_time', 0):.0f} 秒")
        
        # 模块状态
        modules = status_info.get('modules', {})
        click.echo(click.style('\n📦 模块状态', fg='cyan', bold=True))
        for module_name, module_status in modules.items():
            status_text = click.style('✅ 正常', fg='green') if module_status else click.style('❌ 异常', fg='red')
            click.echo(f"  {module_name}: {status_text}")
        
        # Agent状态
        agents = status_info.get('agents', {})
        click.echo(click.style('\n🤖 Agent状态', fg='cyan', bold=True))
        click.echo(f"  已启用: {', '.join(agents.get('enabled', []))}")
        click.echo(f"  运行中: {', '.join(agents.get('running', []))}")
        
        # 钩子状态
        hooks = status_info.get('hooks', {})
        click.echo(click.style('\n🎯 钩子状态', fg='cyan', bold=True))
        click.echo(f"  已注册: {hooks.get('registered', 0)} 个")
        click.echo(f"  已执行: {hooks.get('executed', 0)} 次")
        
        # 系统事件
        events_count = status_info.get('system_events', 0)
        click.echo(click.style('\n📝 系统事件', fg='cyan', bold=True))
        click.echo(f"  事件总数: {events_count}")
        
        # 配置信息
        config = status_info.get('config', {})
        click.echo(click.style('\n⚙️  配置信息', fg='cyan', bold=True))
        click.echo(f"  环境: {config.get('environment', '未知')}")
        click.echo(f"  调试模式: {'开启' if config.get('debug') else '关闭'}")
        click.echo(f"  日志级别: {config.get('log_level', 'INFO')}")
        
    except Exception as e:
        click.echo(click.style(f'❌ 获取状态失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
@click.argument('stock_code')
@click.option('--source', '-s', type=click.Choice(['tdx', 'eastmoney']), 
              default='tdx', help='数据源')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'simple']), 
              default='simple', help='输出格式')
def get_data(stock_code: str, source: str, output: str):
    """获取股票数据"""
    try:
        click.echo(f"正在获取 {stock_code} 的数据...")
        
        # 获取数据
        stock_data = get_stock_data(stock_code, source)
        
        if output == 'json':
            # JSON格式输出
            data_dict = {
                'stock_code': stock_data.code,
                'stock_name': stock_data.name,
                'timestamp': stock_data.timestamp.isoformat() if stock_data.timestamp else None,
                'open': stock_data.open,
                'close': stock_data.close,
                'high': stock_data.high,
                'low': stock_data.low,
                'volume': stock_data.volume,
                'amount': stock_data.amount,
                'turnover_rate': stock_data.turnover_rate,
                'data_source': stock_data.data_source
            }
            click.echo(json.dumps(data_dict, indent=2, ensure_ascii=False))
            
        elif output == 'table':
            # 表格格式输出
            from rich.console import Console
            from rich.table import Table
            
            console = Console()
            table = Table(title=f"{stock_code} 股票数据")
            
            table.add_column("字段", style="cyan")
            table.add_column("值", style="green")
            
            table.add_row("股票代码", stock_data.code)
            table.add_row("股票名称", stock_data.name or "未知")
            table.add_row("数据时间", stock_data.timestamp.isoformat() if stock_data.timestamp else "未知")
            table.add_row("开盘价", f"{stock_data.open:.2f}" if stock_data.open else "未知")
            table.add_row("收盘价", f"{stock_data.close:.2f}" if stock_data.close else "未知")
            table.add_row("最高价", f"{stock_data.high:.2f}" if stock_data.high else "未知")
            table.add_row("最低价", f"{stock_data.low:.2f}" if stock_data.low else "未知")
            table.add_row("成交量", f"{stock_data.volume:,}" if stock_data.volume else "未知")
            table.add_row("成交额", f"{stock_data.amount:,}" if stock_data.amount else "未知")
            table.add_row("换手率", f"{stock_data.turnover_rate:.2%}" if stock_data.turnover_rate else "未知")
            table.add_row("数据源", stock_data.data_source or "未知")
            
            console.print(table)
            
        else:
            # 简单格式输出
            click.echo(click.style(f"\n📊 {stock_code} 股票数据", fg='cyan', bold=True))
            click.echo(f"股票名称: {stock_data.name or '未知'}")
            click.echo(f"数据时间: {stock_data.timestamp.isoformat() if stock_data.timestamp else '未知'}")
            click.echo(f"开盘价: {stock_data.open:.2f}" if stock_data.open else "开盘价: 未知")
            click.echo(f"收盘价: {stock_data.close:.2f}" if stock_data.close else "收盘价: 未知")
            click.echo(f"最高价: {stock_data.high:.2f}" if stock_data.high else "最高价: 未知")
            click.echo(f"最低价: {stock_data.low:.2f}" if stock_data.low else "最低价: 未知")
            click.echo(f"成交量: {stock_data.volume:,}" if stock_data.volume else "成交量: 未知")
            click.echo(f"成交额: {stock_data.amount:,}" if stock_data.amount else "成交额: 未知")
            click.echo(f"换手率: {stock_data.turnover_rate:.2%}" if stock_data.turnover_rate else "换手率: 未知")
            click.echo(f"数据源: {stock_data.data_source or '未知'}")
            
    except Exception as e:
        click.echo(click.style(f'❌ 获取数据失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--strategy', '-s', required=True, help='策略名称')
@click.option('--start', '-S', required=True, help='开始日期 (YYYY-MM-DD)')
@click.option('--end', '-E', required=True, help='结束日期 (YYYY-MM-DD)')
@click.option('--stocks', '-t', multiple=True, help='股票代码列表')
@click.option('--output', '-o', type=click.Choice(['json', 'simple']), 
              default='simple', help='输出格式')
def backtest(strategy: str, start: str, end: str, stocks: list, output: str):
    """运行回测"""
    try:
        if not stocks:
            stocks = ['000001.SZ']  # 默认使用平安银行
        
        click.echo(f"开始回测策略: {strategy}")
        click.echo(f"时间范围: {start} 到 {end}")
        click.echo(f"股票列表: {', '.join(stocks)}")
        
        # 准备策略配置
        strategy_config = {
            'strategy_name': strategy,
            'stock_codes': list(stocks),
            'start_date': start,
            'end_date': end,
            'parameters': {}
        }
        
        # 获取平台实例
        platform = get_platform()
        
        # 运行回测
        result = platform.run_backtest(strategy_config)
        
        if output == 'json':
            # JSON格式输出
            result_dict = {
                'strategy_name': result.strategy_name,
                'stock_codes': result.stock_codes,
                'start_date': result.start_date,
                'end_date': result.end_date,
                'initial_capital': result.initial_capital,
                'total_return': result.total_return,
                'annual_return': result.annual_return,
                'max_drawdown': result.max_drawdown,
                'sharpe_ratio': result.sharpe_ratio,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'profitable_trades': result.profitable_trades,
                'performance_metrics': result.performance_metrics
            }
            click.echo(json.dumps(result_dict, indent=2, ensure_ascii=False))
            
        else:
            # 简单格式输出
            click.echo(click.style(f"\n📈 回测结果 - {strategy}", fg='cyan', bold=True))
            click.echo(f"时间范围: {result.start_date} 到 {result.end_date}")
            click.echo(f"股票: {', '.join(result.stock_codes)}")
            click.echo(f"初始资金: ¥{result.initial_capital:,.2f}")
            click.echo(f"总收益率: {result.total_return:.2%}")
            click.echo(f"年化收益率: {result.annual_return:.2%}")
            click.echo(f"最大回撤: {result.max_drawdown:.2%}")
            click.echo(f"夏普比率: {result.sharpe_ratio:.2f}")
            click.echo(f"胜率: {result.win_rate:.2%}")
            click.echo(f"总交易次数: {result.total_trades}")
            click.echo(f"盈利交易次数: {result.profitable_trades}")
            
    except Exception as e:
        click.echo(click.style(f'❌ 回测失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', type=click.Choice(['yaml', 'json']), 
              default='yaml', help='输出格式')
def config(output: str):
    """查看当前配置"""
    try:
        # 获取平台实例
        platform = get_platform()
        
        # 获取所有配置
        all_config = platform.config.get_all_config()
        
        if output == 'json':
            click.echo(json.dumps(all_config, indent=2, ensure_ascii=False))
        else:
            # YAML格式输出
            click.echo(yaml.dump(all_config, allow_unicode=True, default_flow_style=False))
            
    except Exception as e:
        click.echo(click.style(f'❌ 获取配置失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
@click.argument('key_path')
@click.argument('value')
@click.option('--section', '-s', help='配置节名称（如果key_path不包含节名）')
def set_config_value(key_path: str, value: str, section: Optional[str]):
    """设置配置值"""
    try:
        # 处理key_path
        if section and '.' not in key_path:
            full_key = f"{section}.{key_path}"
        else:
            full_key = key_path
        
        # 类型推断和转换
        if value.lower() in ['true', 'false']:
            typed_value = value.lower() == 'true'
        elif value.isdigit():
            typed_value = int(value)
        elif '.' in value and value.replace('.', '', 1).isdigit():
            typed_value = float(value)
        else:
            typed_value = value
        
        # 设置配置
        success = set_config(full_key, typed_value)
        
        if success:
            click.echo(click.style(f'✅ 配置设置成功: {full_key} = {typed_value}', fg='green'))
        else:
            click.echo(click.style(f'❌ 配置设置失败: {full_key}', fg='red'))
            
    except Exception as e:
        click.echo(click.style(f'❌ 设置配置失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
def events():
    """查看系统事件"""
    try:
        # 获取平台实例
        platform = get_platform()
        
        if not hasattr(platform, 'system_events') or not platform.system_events:
            click.echo(click.style('暂无系统事件', fg='yellow'))
            return
        
        click.echo(click.style(f'📝 系统事件 (共 {len(platform.system_events)} 条)', fg='cyan', bold=True))
        
        for i, event in enumerate(platform.system_events[-10:], 1):  # 显示最近10条
            click.echo(f"\n{i}. [{event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]")
            click.echo(f"   类型: {event.event_type}")
            click.echo(f"   来源: {event.source_module}")
            
            if event.event_data:
                click.echo(f"   数据: {json.dumps(event.event_data, ensure_ascii=False)}")
                
    except Exception as e:
        click.echo(click.style(f'❌ 获取系统事件失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
def agents():
    """管理Agent"""
    try:
        # 获取平台实例
        platform = get_platform()
        
        if not hasattr(platform, 'agent_manager'):
            click.echo(click.style('Agent管理器未初始化', fg='yellow'))
            return
        
        agent_manager = platform.agent_manager
        
        click.echo(click.style('🤖 Agent管理', fg='cyan', bold=True))
        
        # 显示Agent状态
        running_agents = agent_manager.get_running_agents()
        all_agents = agent_manager.registered_agents.keys()
        
        click.echo(f"已注册Agent: {', '.join(all_agents)}")
        click.echo(f"运行中Agent: {', '.join(running_agents) if running_agents else '无'}")
        
        # 显示Agent统计
        stats = agent_manager.get_stats()
        click.echo(f"消息处理总数: {stats.get('total_messages_processed', 0)}")
        click.echo(f"平均处理时间: {stats.get('avg_processing_time', 0):.3f}秒")
        
    except Exception as e:
        click.echo(click.style(f'❌ 管理Agent失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--file', '-f', type=click.Path(), help='导出文件路径')
def export_config(file: Optional[str]):
    """导出当前配置到文件"""
    try:
        # 获取平台实例
        platform = get_platform()
        
        # 获取所有配置
        all_config = platform.config.get_all_config()
        
        # 准备导出数据
        export_data = {}
        for section_name, section_data in all_config.items():
            export_data[section_name] = {}
            for key, item_info in section_data.items():
                export_data[section_name][key] = item_info['value']
        
        if file:
            # 导出到文件
            file_path = Path(file)
            
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(export_data, f, allow_unicode=True, default_flow_style=False)
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                click.echo(click.style(f'❌ 不支持的文件格式: {file_path.suffix}', fg='red'))
                sys.exit(1)
            
            click.echo(click.style(f'✅ 配置已导出到: {file_path}', fg='green'))
        else:
            # 输出到控制台
            click.echo(yaml.dump(export_data, allow_unicode=True, default_flow_style=False))
            
    except Exception as e:
        click.echo(click.style(f'❌ 导出配置失败: {str(e)}', fg='red'))
        sys.exit(1)


@cli.command()
def version():
    """显示版本信息"""
    from . import __version__, __description__, __author__, __license__
    
    click.echo(click.style(f'模块化量化平台 v{__version__}', fg='cyan', bold=True))
    click.echo(f"作者: {__author__}")
    click.echo(f"许可证: {__license__}")
    click.echo()
    
    # 显示简短描述
    description_lines = __description__.strip().split('\n')
    for line in description_lines[:5]:  # 只显示前5行
        if line.strip():
            click.echo(line.strip())
    
    click.echo()
    click.echo("核心理念: 数据是基础，做成模块化，功能只挂接")


def main():
    """命令行入口函数"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo(click.style('\n👋 操作已取消', fg='yellow'))
        sys.exit(0)
    except Exception as e:
        click.echo(click.style(f'\n❌ 发生错误: {str(e)}', fg='red'))
        sys.exit(1)


if __name__ == '__main__':
    main()