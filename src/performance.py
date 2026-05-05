import pandas as pd
import numpy as np
from typing import Dict, Any


class PerformanceCalculator:
    """绩效指标计算器 - 计算20+专业量化绩效指标"""
    
    @staticmethod
    def calculate_all(equity_curve: pd.Series, 
                      trades: pd.DataFrame = None,
                      risk_free_rate: float = 0.03) -> Dict[str, Any]:
        """
        计算所有绩效指标
        Args:
            equity_curve: 净值曲线，索引为日期
            trades: 交易明细DataFrame，包含每笔交易的盈亏
            risk_free_rate: 无风险利率，默认3%
        Returns:
            完整绩效指标字典
        """
        if len(equity_curve) < 2:
            return {}
        
        # 基础收益率计算
        returns = equity_curve.pct_change().dropna()
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        
        # 年化收益率 (CAGR)
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        cagr = (1 + total_return) ** (252 / max(days, 1)) - 1
        
        # 年化波动率
        annual_volatility = returns.std() * np.sqrt(252)
        
        # 夏普比率
        sharpe_ratio = (cagr - risk_free_rate) / max(annual_volatility, 0.001)
        
        # 最大回撤
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 最大回撤持续天数
        drawdown_end = drawdown.idxmin()
        drawdown_start = rolling_max.loc[:drawdown_end].idxmax()
        max_drawdown_duration = (drawdown_end - drawdown_start).days
        
        # 卡玛比率
        calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 索提诺比率 (只考虑下行波动率)
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0.001
        sortino_ratio = (cagr - risk_free_rate) / downside_volatility
        
        # 交易相关指标
        win_rate = 0
        profit_loss_ratio = 0
        avg_trade_return = 0
        avg_win_trade_return = 0
        avg_loss_trade_return = 0
        max_win_trade = 0
        max_loss_trade = 0
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        
        if trades is not None and len(trades) > 0:
            total_trades = len(trades)
            pnl = trades['pnl'].values if 'pnl' in trades.columns else trades['profit'].values
            
            winning_trades = sum(1 for p in pnl if p > 0)
            losing_trades = sum(1 for p in pnl if p < 0)
            
            if total_trades > 0:
                win_rate = winning_trades / total_trades
                avg_trade_return = np.mean(pnl)
                
                wins = [p for p in pnl if p > 0]
                losses = [abs(p) for p in pnl if p < 0]
                
                if len(wins) > 0:
                    avg_win_trade_return = np.mean(wins)
                    max_win_trade = np.max(wins)
                
                if len(losses) > 0:
                    avg_loss_trade_return = np.mean(losses)
                    max_loss_trade = np.max(losses)
                
                if avg_loss_trade_return > 0:
                    profit_loss_ratio = avg_win_trade_return / avg_loss_trade_return
        
        # 盈亏平衡点
        profit_factor = (avg_win_trade_return * winning_trades) / max(avg_loss_trade_return * losing_trades, 0.001)
        
        # 连续盈亏
        consecutive_wins_max = 0
        consecutive_losses_max = 0
        if len(returns) > 0:
            current_wins = 0
            current_losses = 0
            for r in returns:
                if r > 0:
                    current_wins += 1
                    current_losses = 0
                    consecutive_wins_max = max(consecutive_wins_max, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    consecutive_losses_max = max(consecutive_losses_max, current_losses)
        
        # VAR (95%置信度)
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
        
        # CVAR
        cvar_95 = returns[returns <= var_95].mean() if len(returns) > 0 and var_95 != 0 else 0
        
        return {
            # 收益类
            "总收益率": round(total_return * 100, 2),
            "年化收益率(CAGR)": round(cagr * 100, 2),
            "累计净值": round(equity_curve.iloc[-1] / equity_curve.iloc[0], 3),
            
            # 风险类
            "最大回撤": round(max_drawdown * 100, 2),
            "最大回撤持续天数": max_drawdown_duration,
            "年化波动率": round(annual_volatility * 100, 2),
            "下行波动率": round(downside_volatility * 100, 2),
            "夏普比率": round(sharpe_ratio, 2),
            "卡玛比率": round(calmar_ratio, 2),
            "索提诺比率": round(sortino_ratio, 2),
            "VaR(95%)": round(var_95 * 100, 2),
            "CVaR(95%)": round(cvar_95 * 100, 2),
            
            # 交易类
            "总交易次数": total_trades,
            "胜率": round(win_rate * 100, 2),
            "盈亏比": round(profit_loss_ratio, 2),
            "盈利因子": round(profit_factor, 2),
            "平均单笔收益": round(avg_trade_return, 2),
            "平均盈利交易收益": round(avg_win_trade_return, 2),
            "平均亏损交易亏损": round(avg_loss_trade_return, 2),
            "单笔最大盈利": round(max_win_trade, 2),
            "单笔最大亏损": round(max_loss_trade, 2),
            "最大连续盈利天数": consecutive_wins_max,
            "最大连续亏损天数": consecutive_losses_max,
            
            # 其他
            "回测天数": days,
            "交易频率(次/月)": round(total_trades / max(days / 30, 1), 2),
        }
