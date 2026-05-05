import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict
import hashlib
import json


class DataLoader:
    """行情数据加载器 - 支持本地缓存、多数据源"""
    
    def __init__(self, cache_dir: str = "data"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_dir_parquet = self.cache_dir / "parquet"
        self.cache_dir_parquet.mkdir(exist_ok=True)
        
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
    
    def load_data(self, symbol: str, start_date: str, end_date: str, use_cache: bool = True) -> pd.DataFrame:
        """加载行情数据"""
        cache_key = self.get_cache_key(symbol, start_date, end_date)
        
        # 尝试从缓存加载
        if use_cache:
            cached = self.load_from_cache(cache_key)
            if cached is not None:
                return cached
        
        # 生成示例数据（实际项目中对接Tushare/Akshare）
        data = self.generate_sample_data(symbol, start_date, end_date)
        
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
