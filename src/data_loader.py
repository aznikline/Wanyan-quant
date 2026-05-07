import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Tuple
import hashlib
import json

# 可选数据源支持
# 延迟导入，避免强依赖

def import_akshare():
    """延迟导入Akshare"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        return None

def import_tushare():
    """延迟导入Tushare"""
    try:
        import tushare as ts
        return ts
    except ImportError:
        return None


class DataSource:
    """数据源枚举"""
    SIMULATED = "simulated"
    AKSHARE = "akshare"
    TUSHARE = "tushare"


class DataLoader:
    """行情数据加载器 - 支持本地缓存、多数据源"""
    
    def __init__(self, cache_dir: str = "data", data_source: str = DataSource.SIMULATED, tushare_token: str = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_dir_parquet = self.cache_dir / "parquet"
        self.cache_dir_parquet.mkdir(exist_ok=True)
        
        self.data_source = data_source
        self.tushare_token = tushare_token
        
        # 预设热门标的
        self.preset_symbols = {
            "沪深300": "000300.SH",
            "上证指数": "000001.SH",
            "深证成指": "399001.SZ",
            "创业板指": "399006.SZ",
            "中证500": "000905.SH",
            "上证50": "000016.SH",
            "科创50": "000688.SH",
            "贵州茅台": "600519.SH",
            "宁德时代": "300750.SZ",
            "比亚迪": "002594.SZ",
            "腾讯控股": "0700.HK",
            "阿里巴巴": "BABA",
        }
    
    def set_data_source(self, data_source: str):
        """切换数据源"""
        self.data_source = data_source
    
    def set_tushare_token(self, token: str):
        """设置Tushare Token"""
        self.tushare_token = token
    
    def get_available_data_sources(self) -> list:
        """获取可用的数据源"""
        sources = [(DataSource.SIMULATED, "模拟数据")]
        
        ak = import_akshare()
        if ak:
            sources.append((DataSource.AKSHARE, "Akshare 免费开源数据"))
        
        ts = import_tushare()
        if ts:
            sources.append((DataSource.TUSHARE, "Tushare 专业数据（需Token）"))
        
        return sources
    
    def check_data_source_available(self, data_source: str) -> Tuple[bool, str]:
        """检查数据源是否可用"""
        if data_source == DataSource.SIMULATED:
            return True, ""
        
        if data_source == DataSource.AKSHARE:
            ak = import_akshare()
            if ak:
                return True, ""
            return False, "缺少 akshare 依赖，请执行: pip install akshare"
        
        if data_source == DataSource.TUSHARE:
            ts = import_tushare()
            if not ts:
                return False, "缺少 tushare 依赖，请执行: pip install tushare"
            if not self.tushare_token:
                return False, "请设置 Tushare Token"
            return True, ""
        
        return False, "未知数据源"
    
    def load_from_akshare(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从Akshare加载数据"""
        ak = import_akshare()
        if not ak:
            raise ImportError("请先安装 akshare: pip install akshare")
        
        # 转换日期格式
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        
        # 根据symbol判断是指数还是股票
        symbol_code = symbol.split('.')[0]
        
        try:
            # 尝试作为指数加载
            df = ak.stock_zh_index_daily(symbol=symbol_code)
        except:
            try:
                # 尝试作为个股加载
                df = ak.stock_zh_a_hist(symbol=symbol_code, period="daily", 
                                       start_date=start, end_date=end_date, adjust="qfq")
                # 重命名列以匹配标准格式
                df = df.rename(columns={
                    "日期": "date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume"
                })
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            except:
                raise ValueError(f"无法加载 {symbol} 的数据，请检查代码是否正确")
        
        df = df.sort_index()
        df = df.loc[start_date:end_date]
        
        return df[['open', 'high', 'low', 'close', 'volume']].round(2)
    
    def load_from_tushare(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从Tushare加载数据"""
        ts = import_tushare()
        if not ts:
            raise ImportError("请先安装 tushare: pip install tushare")
        
        if not self.tushare_token:
            raise ValueError("请先设置 Tushare Token")
        
        ts.set_token(self.tushare_token)
        pro = ts.pro_api()
        
        # 转换日期格式
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        
        # 转换symbol格式
        ts_code = symbol
        
        df = pro.daily(ts_code=ts_code, start_date=start, end_date=end_date)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date")
        df = df.sort_index()
        
        # 重命名列
        df = df.rename(columns={
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "vol": "volume"
        })
        
        return df[['open', 'high', 'low', 'close', 'volume']].round(2)
    
    def get_cache_key(self, symbol: str, start_date: str, end_date: str) -> str:
        """生成缓存key"""
        key_str = f"{symbol}_{start_date}_{end_date}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def load_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        cache_file = self.cache_dir_parquet / f"{cache_key}.parquet"
        if cache_file.exists():
            return pd.read_parquet(cache_file)
        return None
    
    def save_to_cache(self, cache_key: str, data: pd.DataFrame):
        """保存数据到缓存"""
        cache_file = self.cache_dir_parquet / f"{cache_key}.parquet"
        data.to_parquet(cache_file)
    
    def generate_sample_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成示例数据 - 用于演示和本地测试"""
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        n = len(dates)
        
        # 生成模拟价格数据（带趋势 + 随机游走）
        np.random.seed(hash(symbol) % 10000)
        
        # 基础趋势
        base_trend = np.linspace(100, 150, n)
        
        # 随机游走
        returns = np.random.normal(0.0005, 0.02, n)
        price_walk = 100 * (1 + returns).cumprod()
        
        # 组合价格
        close = 0.3 * base_trend + 0.7 * price_walk
        
        # 生成OHLC
        open_prices = close * (1 + np.random.normal(0, 0.005, n))
        high = np.maximum(open_prices, close) * (1 + np.random.uniform(0, 0.02, n))
        low = np.minimum(open_prices, close) * (1 - np.random.uniform(0, 0.02, n))
        volume = np.random.randint(1000000, 10000000, n)
        
        data = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
        
        return data.round(2)
    
    def load_data(self, symbol: str, start_date: str, end_date: str, use_cache: bool = True, data_source: str = None) -> pd.DataFrame:
        """加载行情数据
        
        Args:
            symbol: 标的代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            use_cache: 是否使用缓存
            data_source: 数据源，不传则使用初始化时设置的
        """
        source = data_source or self.data_source
        cache_key = self.get_cache_key(f"{source}_{symbol}", start_date, end_date)
        
        # 尝试从缓存加载
        if use_cache:
            cached = self.load_from_cache(cache_key)
            if cached is not None:
                return cached
        
        # 根据数据源加载
        if source == DataSource.SIMULATED:
            data = self.generate_sample_data(symbol, start_date, end_date)
        elif source == DataSource.AKSHARE:
            data = self.load_from_akshare(symbol, start_date, end_date)
        elif source == DataSource.TUSHARE:
            data = self.load_from_tushare(symbol, start_date, end_date)
        else:
            raise ValueError(f"不支持的数据源: {source}")
        
        # 保存到缓存
        if use_cache:
            self.save_to_cache(cache_key, data)
        
        return data
    
    def get_symbol_name(self, symbol: str) -> str:
        """获取标的名称"""
        for name, code in self.preset_symbols.items():
            if code == symbol:
                return name
        return symbol
    
    def get_all_preset_symbols(self) -> Dict[str, str]:
        """获取所有预设标的"""
        return self.preset_symbols
