"""
通达信数据解析器 - 基于injoyai/tdx算法实现

算法特点：
1. 二进制格式解析：准确解析通达信的.day文件格式
2. 时间编码：采用通达信特有的时间编码算法
3. 相对价格：采用通达信的相对价格编码方式
4. 数据验证：内置严格的数据验证机制

核心算法来源：https://github.com/injoyai/tdx
Python实现基于：/Users/huangjing/.openclaw/workspace/tdx_parser_final.py
"""

import struct
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class TDXParser:
    """通达信数据解析器"""
    
    # 通达信文件扩展名
    FILE_EXTENSIONS = {
        'day': '.day',      # 日线数据
        'lc1': '.lc1',      # 1分钟数据
        'lc5': '.lc5',      # 5分钟数据
    }
    
    # 通达信股票代码前缀映射
    MARKET_PREFIXES = {
        'sh': 'sh',  # 上海
        'sz': 'sz',  # 深圳
        'bj': 'bj',  # 北京
    }
    
    def __init__(self, tdx_path: str):
        """
        初始化通达信解析器
        
        Args:
            tdx_path: 通达信数据目录路径，如 /Volumes/[C] Windows 10/new_tdx64/
        """
        self.tdx_path = Path(tdx_path)
        self._validate_tdx_path()
        
        logger.info(f"通达信解析器初始化成功: {tdx_path}")
    
    def _validate_tdx_path(self):
        """验证通达信路径有效性"""
        if not self.tdx_path.exists():
            raise FileNotFoundError(f"通达信路径不存在: {self.tdx_path}")
        
        # 检查常见通达信目录结构
        required_dirs = ['vipdoc', 'T0002']
        found_dirs = []
        
        for item in self.tdx_path.iterdir():
            if item.is_dir() and item.name.lower() in [d.lower() for d in required_dirs]:
                found_dirs.append(item.name)
        
        if len(found_dirs) == 0:
            logger.warning(f"未找到标准的通达信目录结构，路径可能不完整: {self.tdx_path}")
    
    def _get_stock_file_path(self, stock_code: str, data_type: str = 'day') -> Optional[Path]:
        """
        获取股票数据文件路径
        
        Args:
            stock_code: 股票代码，如 "000001"
            data_type: 数据类型，如 "day", "lc1", "lc5"
            
        Returns:
            文件路径或None
        """
        if data_type not in self.FILE_EXTENSIONS:
            logger.error(f"不支持的数据类型: {data_type}")
            return None
        
        # 提取市场前缀
        if stock_code.startswith('sh'):
            market = 'sh'
            code = stock_code[2:]  # 去掉sh前缀
            subdir = 'sh'  # 上海市场
        elif stock_code.startswith('sz'):
            market = 'sz'
            code = stock_code[2:]  # 去掉sz前缀
            subdir = 'sz'  # 深圳市场
        elif stock_code.startswith('bj'):
            market = 'bj'
            code = stock_code[2:]  # 去掉bj前缀
            subdir = 'bj'  # 北京市场
        else:
            # 默认根据代码长度判断
            if stock_code.startswith('6'):
                market = 'sh'
                subdir = 'sh'
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                market = 'sz'
                subdir = 'sz'
            elif stock_code.startswith('8') or stock_code.startswith('4'):
                market = 'bj'
                subdir = 'bj'
            else:
                logger.error(f"无法识别股票代码的市场: {stock_code}")
                return None
            
            code = stock_code
        
        # 构建文件路径
        # 通达信标准路径：vipdoc/{market}/lday/{market}{code}.day
        file_name = f"{market}{code}{self.FILE_EXTENSIONS[data_type]}"
        
        # 尝试多个可能的路径
        possible_paths = [
            self.tdx_path / 'vipdoc' / subdir / 'lday' / file_name,  # 标准路径
            self.tdx_path / 'vipdoc' / subdir / 'lday' / f"{stock_code}{self.FILE_EXTENSIONS[data_type]}",
            self.tdx_path / 'vipdoc' / 'sh' / 'lday' / file_name,    # 备用路径
            self.tdx_path / 'vipdoc' / 'sz' / 'lday' / file_name,    # 备用路径
            self.tdx_path / file_name,                              # 直接路径
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.debug(f"找到股票数据文件: {path}")
                return path
        
        logger.error(f"未找到股票数据文件: {stock_code} ({data_type})")
        logger.debug(f"搜索路径: {possible_paths}")
        return None
    
    def _decode_tdx_date(self, date_int: int) -> datetime:
        """
        解码通达信日期格式
        
        Args:
            date_int: 通达信编码的日期整数
            
        Returns:
            datetime对象
        """
        # 通达信日期编码算法
        year = (date_int >> 16) & 0xFFFF
        month = (date_int >> 8) & 0xFF
        day = date_int & 0xFF
        
        # 年份处理（通达信可能使用偏移）
        if year < 100:
            year += 2000  # 假设是2000年之后的年份
            
        return datetime(year, month, day)
    
    def _decode_tdx_price(self, price_int: int, base_price: float = 0.0) -> float:
        """
        解码通达信价格（相对价格编码）
        
        Args:
            price_int: 通达信编码的价格整数
            base_price: 基准价格
            
        Returns:
            实际价格
        """
        # 通达信使用相对价格编码
        # 实际价格 = 基准价格 + (编码价格 / 100.0)
        return base_price + (price_int / 100.0)
    
    def parse_stock_data(self, stock_code: str, start_date: str = None, end_date: str = None, 
                         data_type: str = 'day') -> List[Dict[str, Any]]:
        """
        解析股票数据
        
        Args:
            stock_code: 股票代码，如 "000001" 或 "sz000001"
            start_date: 开始日期，格式 "YYYY-MM-DD"
            end_date: 结束日期，格式 "YYYY-MM-DD"
            data_type: 数据类型，"day", "lc1", "lc5"
            
        Returns:
            股票数据列表
        """
        # 获取文件路径
        file_path = self._get_stock_file_path(stock_code, data_type)
        if not file_path:
            return []
        
        try:
            with open(file_path, 'rb') as f:
                file_size = os.path.getsize(file_path)
                
                # 计算记录数量（通达信日线数据每条记录32字节）
                if data_type == 'day':
                    record_size = 32
                    num_records = file_size // record_size
                    
                    if file_size % record_size != 0:
                        logger.warning(f"文件大小不是记录大小的整数倍: {file_size} % {record_size} = {file_size % record_size}")
                    
                    logger.info(f"解析通达信日线数据: {stock_code}, 记录数: {num_records}")
                    
                    # 读取所有记录
                    records = []
                    base_price = 0.0
                    
                    for i in range(num_records):
                        # 读取32字节记录
                        record_data = f.read(record_size)
                        if len(record_data) < record_size:
                            break
                        
                        # 解析记录
                        record = self._parse_day_record(record_data, base_price)
                        if record:
                            records.append(record)
                            # 更新基准价格（使用当前收盘价）
                            base_price = record['close']
                    
                    # 过滤日期范围
                    if start_date or end_date:
                        records = self._filter_by_date_range(records, start_date, end_date)
                    
                    logger.info(f"解析完成: {stock_code}, 有效记录数: {len(records)}")
                    return records
                    
                else:
                    logger.warning(f"暂不支持的数据类型解析: {data_type}")
                    return []
                    
        except Exception as e:
            logger.error(f"解析股票数据失败: {stock_code} - {str(e)}")
            return []
    
    def _parse_day_record(self, record_data: bytes, base_price: float) -> Optional[Dict[str, Any]]:
        """
        解析日线记录
        
        Args:
            record_data: 32字节记录数据
            base_price: 基准价格
            
        Returns:
            解析后的数据字典
        """
        try:
            # 通达信日线数据格式（32字节）：
            # 0-3: 日期 (int32)
            # 4-7: 开盘价 (int32)
            # 8-11: 最高价 (int32)
            # 12-15: 最低价 (int32)
            # 16-19: 收盘价 (int32)
            # 20-23: 成交额 (float)
            # 24-27: 成交量 (int32)
            # 28-31: 预留 (通常为0)
            
            if len(record_data) < 32:
                logger.warning(f"记录数据不足32字节: {len(record_data)}")
                return None
            
            # 解包数据
            date_int, open_int, high_int, low_int, close_int, amount, volume, _ = struct.unpack('<IIIIIfII', record_data)
            
            # 解码日期
            date = self._decode_tdx_date(date_int)
            
            # 解码价格（使用相对价格编码）
            open_price = self._decode_tdx_price(open_int, base_price)
            high_price = self._decode_tdx_price(high_int, base_price)
            low_price = self._decode_tdx_price(low_int, base_price)
            close_price = self._decode_tdx_price(close_int, base_price)
            
            # 成交额和成交量（通达信成交额单位是万元，需要转换为元）
            amount_yuan = amount * 10000
            
            # 数据验证
            if not self._validate_price_data(open_price, high_price, low_price, close_price):
                logger.warning(f"价格数据验证失败: O:{open_price} H:{high_price} L:{low_price} C:{close_price}")
                return None
            
            # 构建结果
            return {
                'date': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'amount': amount_yuan,
                'volume': volume,
                'pre_close': base_price if base_price > 0 else None,
                'change': close_price - base_price if base_price > 0 else None,
                'change_pct': ((close_price - base_price) / base_price * 100) if base_price > 0 else None
            }
            
        except struct.error as e:
            logger.error(f"解包记录数据失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"解析记录失败: {str(e)}")
            return None
    
    def _validate_price_data(self, open_price: float, high_price: float, 
                            low_price: float, close_price: float) -> bool:
        """验证价格数据合理性"""
        # 价格必须为正数
        if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
            return False
        
        # 高低价关系
        if high_price < low_price:
            return False
        
        # 价格应在合理范围内（假设股票价格在0.01-10000元之间）
        if not (0.01 <= open_price <= 10000 and 
                0.01 <= high_price <= 10000 and 
                0.01 <= low_price <= 10000 and 
                0.01 <= close_price <= 10000):
            logger.warning(f"价格超出合理范围: O:{open_price} H:{high_price} L:{low_price} C:{close_price}")
            # 这里只是警告，不返回False，因为确实有高价股
        
        return True
    
    def _filter_by_date_range(self, records: List[Dict[str, Any]], 
                              start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """按日期范围过滤记录"""
        filtered_records = []
        
        # 转换日期字符串
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        for record in records:
            record_date = record['date']
            
            # 检查是否在日期范围内
            if start_dt and record_date < start_dt:
                continue
            if end_dt and record_date > end_dt:
                continue
                
            filtered_records.append(record)
        
        return filtered_records
    
    def test_connection(self) -> bool:
        """测试通达信数据连接"""
        try:
            # 检查路径是否存在
            if not self.tdx_path.exists():
                logger.error(f"通达信路径不存在: {self.tdx_path}")
                return False
            
            # 尝试读取一个已知的股票文件（例如平安银行）
            test_stock = "000001"
            file_path = self._get_stock_file_path(test_stock, 'day')
            
            if file_path and file_path.exists():
                logger.info(f"通达信连接测试成功: {file_path}")
                return True
            else:
                logger.warning(f"未找到测试股票文件: {test_stock}")
                
                # 尝试列出目录查看有什么文件
                day_dir = self.tdx_path / 'vipdoc' / 'sh' / 'lday'
                if day_dir.exists():
                    files = list(day_dir.glob("*.day"))
                    if files:
                        logger.info(f"找到通达信日线文件: {len(files)}个")
                        return True
                    else:
                        logger.warning(f"通达信目录存在但无.day文件: {day_dir}")
                        return False
                else:
                    logger.warning(f"标准通达信目录不存在: {day_dir}")
                    return False
                    
        except Exception as e:
            logger.error(f"通达信连接测试失败: {str(e)}")
            return False
    
    def get_stock_list(self, market: str = None) -> List[str]:
        """
        获取股票列表
        
        Args:
            market: 市场类型，"sh", "sz", "bj"，为None时返回所有
            
        Returns:
            股票代码列表
        """
        stock_list = []
        
        # 确定要扫描的市场
        markets_to_scan = ['sh', 'sz', 'bj'] if market is None else [market]
        
        for market_code in markets_to_scan:
            # 构建目录路径
            day_dir = self.tdx_path / 'vipdoc' / market_code / 'lday'
            
            if day_dir.exists():
                # 扫描.day文件
                for file_path in day_dir.glob("*.day"):
                    file_name = file_path.stem  # 去除扩展名
                    
                    # 提取股票代码（文件格式如: sh000001.day）
                    if len(file_name) >= 8:  # 市场代码(2) + 股票代码(6)
                        stock_code = file_name[2:]  # 去掉市场前缀
                        stock_list.append(f"{market_code}{stock_code}")
        
        logger.info(f"获取股票列表: 共{len(stock_list)}只股票")
        return stock_list
    
    def get_data_info(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票数据信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            数据信息字典
        """
        info = {
            'stock_code': stock_code,
            'available_data_types': [],
            'record_counts': {},
            'date_ranges': {}
        }
        
        # 检查各种数据类型
        for data_type in self.FILE_EXTENSIONS.keys():
            file_path = self._get_stock_file_path(stock_code, data_type)
            
            if file_path and file_path.exists():
                info['available_data_types'].append(data_type)
                
                # 获取记录数量
                try:
                    file_size = os.path.getsize(file_path)
                    
                    if data_type == 'day':
                        record_size = 32
                    elif data_type == 'lc1':
                        record_size = 32  # 假设和日线相同
                    elif data_type == 'lc5':
                        record_size = 32  # 假设和日线相同
                    else:
                        record_size = 32
                    
                    num_records = file_size // record_size
                    info['record_counts'][data_type] = num_records
                    
                    # 获取日期范围（需要解析文件）
                    if data_type == 'day' and num_records > 0:
                        date_range = self._get_date_range(file_path, data_type)
                        if date_range:
                            info['date_ranges'][data_type] = date_range
                            
                except Exception as e:
                    logger.error(f"获取数据信息失败: {stock_code} {data_type} - {str(e)}")
        
        return info
    
    def _get_date_range(self, file_path: Path, data_type: str) -> Optional[Dict[str, str]]:
        """获取日期范围"""
        try:
            with open(file_path, 'rb') as f:
                file_size = os.path.getsize(file_path)
                
                if data_type == 'day':
                    record_size = 32
                    num_records = file_size // record_size
                    
                    if num_records == 0:
                        return None
                    
                    # 读取第一条记录
                    f.seek(0)
                    first_record = f.read(record_size)
                    
                    # 读取最后一条记录
                    f.seek((num_records - 1) * record_size)
                    last_record = f.read(record_size)
                    
                    # 解析日期
                    first_date_int = struct.unpack('<I', first_record[0:4])[0]
                    last_date_int = struct.unpack('<I', last_record[0:4])[0]
                    
                    first_date = self._decode_tdx_date(first_date_int)
                    last_date = self._decode_tdx_date(last_date_int)
                    
                    return {
                        'start_date': first_date.strftime('%Y-%m-%d'),
                        'end_date': last_date.strftime('%Y-%m-%d')
                    }
                    
        except Exception as e:
            logger.error(f"获取日期范围失败: {file_path} - {str(e)}")
            return None
        
        return None