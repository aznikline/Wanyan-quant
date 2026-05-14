# Rock Quant 2.4 - 顽岩风格量价模型
"""
Rock Quant 是一个面向个人量化交易者的轻量级量价策略验证平台

核心特性:
- 20+经典量价策略预设
- 14+标准化量价因子库
- 全向量化回测引擎，速度提升5-10倍
- 20+专业绩效指标完整计算
- 可视化参数敏感性分析
- 多维度交易归因分析
- 策略实战指南嵌入
- 3步快速开始向导
- 一键导出完整PDF回测报告

模块说明:
- config.py: 配置管理与参数校验
- backtest_engine.py: 全向量化回测引擎核心
- performance.py: 绩效指标计算器
- strategies.py: 策略基类与预设策略库
- factors.py: 标准化量价因子库（14个因子，4大类）
- data_loader.py: 行情数据加载器
- pdf_generator.py: PDF报告生成器
"""

__version__ = "2.6.0"

from src.config import BacktestConfig, RiskControlConfig, PositionConfig
from src.performance import PerformanceCalculator
from src.backtest_engine import BacktestEngine, BacktestResult
from src.strategies import (
    BaseStrategy, get_all_strategies, create_strategy, get_strategy_info,
    STRATEGY_CLASSES
)
from src.data_loader import DataLoader
from src.factors import (
    BaseFactor, FactorRegistry, calculate_factor, get_factor_info,
    list_factors_by_type, FACTOR_LIST, FACTORS_BY_TYPE
)
