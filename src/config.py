from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import yaml
from pathlib import Path


class BacktestConfig(BaseModel):
    """回测核心配置"""
    symbol: str = Field(default="000001.SZ", description="标的代码")
    start_date: str = Field(default="2020-01-01", description="开始日期")
    end_date: str = Field(default="2024-12-31", description="结束日期")
    initial_capital: float = Field(default=1000000, ge=10000, description="初始资金")
    commission_rate: float = Field(default=0.0003, ge=0, le=0.01, description="手续费率")
    slippage_rate: float = Field(default=0.001, ge=0, le=0.05, description="滑点率")
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"日期格式错误，应为 YYYY-MM-DD: {v}")
        return v


class StrategyConfig(BaseModel):
    """策略配置基类"""
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class RiskControlConfig(BaseModel):
    """风控配置"""
    enable_stop_loss: bool = True
    stop_loss_pct: float = Field(default=0.05, ge=0.01, le=0.3, description="止损比例")
    enable_take_profit: bool = True
    take_profit_pct: float = Field(default=0.15, ge=0.01, le=1.0, description="止盈比例")
    enable_trailing_stop: bool = False
    trailing_stop_pct: float = Field(default=0.03, ge=0.01, le=0.2, description="跟踪止损比例")
    max_position_pct: float = Field(default=1.0, ge=0.1, le=1.0, description="最大仓位比例")
    max_single_day_loss_pct: float = Field(default=0.1, ge=0.01, le=0.5, description="单日最大亏损限制")


class PositionConfig(BaseModel):
    """仓位管理配置"""
    mode: str = Field(default="fixed", description="仓位模式: fixed/kelly/martingale/volatility")
    fixed_size: float = Field(default=1.0, description="固定仓位比例")
    kelly_fraction: float = Field(default=0.5, description="凯利系数")
    martingale_multiplier: float = Field(default=2.0, description="鞅策略倍数")
    volatility_target: float = Field(default=0.2, description="目标年化波动率")


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
    
    def save_config(self, name: str, config: BaseModel):
        """保存配置到文件"""
        config_path = self.config_dir / f"{name}.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config.dict(), f, allow_unicode=True)
        return str(config_path)
    
    def load_config(self, name: str, config_class: type) -> BaseModel:
        """从文件加载配置"""
        config_path = self.config_dir / f"{name}.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return config_class(**data)
    
    def list_configs(self):
        """列出所有保存的配置"""
        return [f.stem for f in self.config_dir.glob("*.yaml")]
