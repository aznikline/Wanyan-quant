"""
Rock Quant - 顽岩量化 v2.6

一个面向个人量化交易者的轻量级量价策略验证平台。

Features:
    - 20+ 经典量价策略预设
    - 14+ 标准化量价因子库
    - 全向量化回测引擎，速度提升5-10倍
    - 5维度AI智能评分系统（纯规则引擎，无LLM依赖）
    - 4位AI专家多智能体辩论评估
    - 5维度收益归因分析
    - 一键导出完整PDF回测报告
    - Streamlit可视化交互界面
    - CLI命令行工具
    - OpenClaw Skill集成

License: MIT
"""

__version__ = "2.6.0"
__author__ = "Rock Quant Team"
__license__ = "MIT"

from src.config import BacktestConfig, RiskControlConfig, PositionConfig
from src.backtest_engine import BacktestEngine, BacktestResult
from src.strategies import (
    BaseStrategy,
    create_strategy,
    get_all_strategies,
    get_strategy_info,
)
from src.performance import PerformanceCalculator
from src.ai_analyzer import AIStrategyAnalyzer, AIAnalysisResult
from src.factors import (
    BaseFactor,
    FactorRegistry,
    calculate_factor,
    get_factor_info,
    list_factors_by_type,
)
from src.data_loader import DataLoader

__all__ = [
    'BacktestConfig',
    'RiskControlConfig',
    'PositionConfig',
    'BacktestEngine',
    'BacktestResult',
    'BaseStrategy',
    'create_strategy',
    'get_all_strategies',
    'get_strategy_info',
    'PerformanceCalculator',
    'AIStrategyAnalyzer',
    'AIAnalysisResult',
    'BaseFactor',
    'FactorRegistry',
    'calculate_factor',
    'get_factor_info',
    'list_factors_by_type',
    'DataLoader',
    '__version__',
]
