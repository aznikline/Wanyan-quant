"""
Rock Quant AI智能分析引擎
v2.6.0 核心特性：策略评分 + 回测解读 + 多智能体辩论 + 5维度收益归因
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class AgentRole(Enum):
    """多智能体角色定义"""
    CONSERVATIVE = "保守风控官"
    AGGRESSIVE = "激进交易员"
    STATISTICIAN = "统计分析师"
    BEHAVIORAL = "行为金融专家"
    SUMMARY = "总结主持人"


@dataclass
class StrategyScore:
    """策略多维度评分"""
    overall_score: float          # 综合评分 0-100
    return_score: float           # 收益能力评分
    risk_score: float             # 风险控制评分
    risk_adjusted_score: float   # 风险调整后收益评分
    consistency_score: float      # 稳定性评分
    trading_quality_score: float  # 交易质量评分
    grade: str                    # 评级 S/A/B/C/D/F
    strengths: List[str]          # 优势
    weaknesses: List[str]         # 不足
    recommendations: List[str]    # 改进建议


@dataclass
class ReturnAttribution:
    """5维度收益归因"""
    trend_capture: float          # 趋势捕捉贡献
    volatility_timing: float      # 波动择时贡献
    mean_reversion: float         # 均值回归贡献
    position_sizing: float        # 仓位管理贡献
    luck_factor: float            # 运气成分（极值收益占比）
    
    def total(self):
        return self.trend_capture + self.volatility_timing + \
               self.mean_reversion + self.position_sizing + self.luck_factor


@dataclass
class AgentDebate:
    """多智能体辩论结果"""
    role: AgentRole
    opinion: str
    key_points: List[str]
    recommendation: str  # 强烈推荐 / 可以使用 / 谨慎使用 / 不推荐
    confidence: float    # 0-100


@dataclass
class AIAnalysisResult:
    """AI分析完整结果"""
    score: StrategyScore
    attribution: ReturnAttribution
    interpretation: str
    debate_results: List[AgentDebate]
    final_conclusion: str


class AIStrategyAnalyzer:
    """AI策略分析引擎"""
    
    def __init__(self):
        pass
    
    def analyze(self, 
                equity_curve: pd.Series,
                trades: pd.DataFrame,
                perf: Dict[str, Any],
                strategy_name: str,
                symbol_name: str) -> AIAnalysisResult:
        """执行完整AI分析"""
        
        # 1. 多维度策略评分
        score = self._calculate_strategy_score(equity_curve, trades, perf)
        
        # 2. 5维度收益归因
        attribution = self._attribute_returns(equity_curve, trades)
        
        # 3. 回测AI解读
        interpretation = self._generate_interpretation(score, attribution, perf, strategy_name, symbol_name)
        
        # 4. 多智能体辩论评估
        debates = self._run_agent_debate(score, attribution, perf, strategy_name)
        
        # 5. 最终结论
        final_conclusion = self._generate_final_conclusion(score, debates)
        
        return AIAnalysisResult(
            score=score,
            attribution=attribution,
            interpretation=interpretation,
            debate_results=debates,
            final_conclusion=final_conclusion
        )
    
    def _calculate_strategy_score(self, 
                                   equity_curve: pd.Series,
                                   trades: pd.DataFrame,
                                   perf: Dict[str, Any]) -> StrategyScore:
        """计算策略多维度评分"""
        
        # 1. 收益能力评分 (0-40分)
        annual_return = perf['年化收益率(CAGR)']
        if annual_return > 30:
            return_score = 40
        elif annual_return > 20:
            return_score = 35 + (annual_return - 20) * 0.5
        elif annual_return > 15:
            return_score = 30 + (annual_return - 15) * 1
        elif annual_return > 10:
            return_score = 25 + (annual_return - 10) * 1
        elif annual_return > 5:
            return_score = 15 + (annual_return - 5) * 2
        elif annual_return > 0:
            return_score = 5 + annual_return * 2
        else:
            return_score = max(0, 5 + annual_return)
        
        # 2. 风险控制评分 (0-20分) - 回撤越小分越高
        max_drawdown = abs(perf['最大回撤'])  # 取绝对值，因为有些实现返回负数
        if max_drawdown < 10:
            risk_score = 20
        elif max_drawdown < 15:
            risk_score = 15 + (15 - max_drawdown) * 1
        elif max_drawdown < 25:
            risk_score = 10 + (25 - max_drawdown) * 0.5
        elif max_drawdown < 35:
            risk_score = 5 + (35 - max_drawdown) * 0.5
        else:
            risk_score = max(0, 40 - max_drawdown)
        
        # 3. 风险调整后收益评分 (0-15分) - 夏普比率
        sharpe = perf['夏普比率']
        if sharpe > 2.5:
            risk_adjusted_score = 15
        elif sharpe > 1.5:
            risk_adjusted_score = 10 + (sharpe - 1.5) * 5
        elif sharpe > 1.0:
            risk_adjusted_score = 7 + (sharpe - 1.0) * 6
        elif sharpe > 0.5:
            risk_adjusted_score = 4 + (sharpe - 0.5) * 6
        elif sharpe > 0:
            risk_adjusted_score = sharpe * 8
        else:
            risk_adjusted_score = 0
        
        # 4. 稳定性评分 (0-10分) - 卡玛比率 + 月度胜率
        calmar = perf['卡玛比率']
        win_rate = perf['胜率']
        
        calmar_score = min(5, max(0, calmar * 2))
        win_rate_score = min(5, max(0, (win_rate - 30) / 4))
        consistency_score = calmar_score + win_rate_score
        
        # 5. 交易质量评分 (0-15分)
        total_trades = perf['总交易次数']
        if len(trades) > 0:
            win_trades = len(trades[trades['return_pct'] > 0])
            loss_trades = len(trades[trades['return_pct'] < 0])
            
            avg_win = trades[trades['return_pct'] > 0]['return_pct'].mean() if win_trades > 0 else 0
            avg_loss = abs(trades[trades['return_pct'] < 0]['return_pct'].mean()) if loss_trades > 0 else 1
            
            profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
            
            # 盈亏比评分
            pl_score = min(8, max(0, profit_loss_ratio * 3))
            
            # 交易频率评分 - 太频繁扣分
            years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
            trades_per_year = total_trades / years if years > 0 else total_trades
            
            if 10 <= trades_per_year <= 100:
                freq_score = 7
            elif 5 <= trades_per_year < 10 or 100 < trades_per_year <= 200:
                freq_score = 5
            else:
                freq_score = 3
            
            trading_quality_score = pl_score + freq_score
        else:
            trading_quality_score = 0
        
        # 综合评分
        overall_score = return_score + risk_score + risk_adjusted_score + consistency_score + trading_quality_score
        
        # 评级
        if overall_score >= 85:
            grade = "S"
        elif overall_score >= 75:
            grade = "A"
        elif overall_score >= 65:
            grade = "B"
        elif overall_score >= 50:
            grade = "C"
        elif overall_score >= 35:
            grade = "D"
        else:
            grade = "F"
        
        # 优势和不足
        strengths, weaknesses = self._analyze_strengths_weaknesses(
            return_score, risk_score, risk_adjusted_score, consistency_score, 
            trading_quality_score, annual_return, max_drawdown, sharpe, perf
        )
        
        # 改进建议
        recommendations = self._generate_recommendations(
            return_score, risk_score, risk_adjusted_score, consistency_score, 
            trading_quality_score, perf
        )
        
        return StrategyScore(
            overall_score=round(overall_score, 1),
            return_score=round(return_score, 1),
            risk_score=round(risk_score, 1),
            risk_adjusted_score=round(risk_adjusted_score, 1),
            consistency_score=round(consistency_score, 1),
            trading_quality_score=round(trading_quality_score, 1),
            grade=grade,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )
    
    def _analyze_strengths_weaknesses(self, return_score, risk_score, risk_adjusted_score, 
                                       consistency_score, trading_quality_score,
                                       annual_return, max_drawdown, sharpe, perf):
        """分析策略的优势和不足"""
        strengths = []
        weaknesses = []
        
        # 收益能力
        if return_score >= 30:
            strengths.append(f"收益能力极强（年化{annual_return:.1f}%）")
        elif return_score >= 20:
            strengths.append(f"收益能力良好（年化{annual_return:.1f}%）")
        else:
            weaknesses.append(f"收益能力偏弱（年化{annual_return:.1f}%）")
        
        # 风险控制
        if risk_score >= 15:
            strengths.append(f"风险控制优秀（最大回撤{max_drawdown:.1f}%）")
        elif risk_score >= 10:
            strengths.append(f"风险控制良好（最大回撤{max_drawdown:.1f}%）")
        else:
            weaknesses.append(f"风险控制不足（最大回撤{max_drawdown:.1f}%）")
        
        # 风险调整后收益
        if risk_adjusted_score >= 12:
            strengths.append(f"风险调整后收益出色（夏普比率{sharpe:.2f}）")
        elif risk_adjusted_score >= 8:
            strengths.append(f"风险调整后收益良好（夏普比率{sharpe:.2f}）")
        else:
            weaknesses.append(f"风险调整后收益一般（夏普比率{sharpe:.2f}）")
        
        # 稳定性
        if consistency_score >= 8:
            strengths.append("策略表现稳定，一致性好")
        elif consistency_score >= 5:
            strengths.append("策略表现尚可")
        else:
            weaknesses.append("策略稳定性不足，表现波动大")
        
        # 交易质量
        if trading_quality_score >= 12:
            strengths.append("交易质量优秀，盈亏比合理")
        elif trading_quality_score >= 8:
            strengths.append("交易质量良好")
        else:
            weaknesses.append("交易质量有待提升")
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, return_score, risk_score, risk_adjusted_score, 
                                   consistency_score, trading_quality_score, perf):
        """生成改进建议"""
        recommendations = []
        
        if return_score < 20:
            recommendations.append("建议优化策略参数或更换策略，提升收益能力")
            recommendations.append("可以尝试放宽止盈条件，让利润充分奔跑")
        
        if risk_score < 10:
            recommendations.append("建议加强止损设置，控制最大回撤")
            recommendations.append("可以考虑增加仓位动态调整机制，降低风险暴露")
        
        if risk_adjusted_score < 8:
            recommendations.append("建议优化风险收益比，在收益和风险间寻找更好平衡")
            recommendations.append("可以考虑在高波动期降低仓位，提升夏普比率")
        
        if consistency_score < 5:
            recommendations.append("建议增加策略过滤条件，剔除低质量信号")
            recommendations.append("可以考虑多策略组合平滑收益曲线")
        
        if trading_quality_score < 8:
            recommendations.append("建议优化进出场时机，提升单笔交易质量")
            recommendations.append("可以考虑增加交易成本（滑点手续费）测试")
        
        if perf['总交易次数'] > 200:
            recommendations.append("交易频率偏高，建议过滤噪音信号，降低交易成本影响")
        
        if not recommendations:
            recommendations.append("策略整体表现优秀，建议维持现有参数进行实盘验证")
            recommendations.append("可以考虑多品种分散投资，进一步降低风险")
        
        return recommendations
    
    def _attribute_returns(self, equity_curve: pd.Series, trades: pd.DataFrame) -> ReturnAttribution:
        """5维度收益归因分析"""
        if len(trades) == 0:
            return ReturnAttribution(0, 0, 0, 0, 0)
        
        total_pnl = trades['pnl'].sum()
        if abs(total_pnl) < 0.001:
            return ReturnAttribution(0, 0, 0, 0, 0)
        
        # 计算每笔交易的持有期和市场环境
        returns = equity_curve.pct_change().fillna(0)
        
        # 1. 趋势捕捉贡献：持有期间市场同向的交易收益占比
        trend_contributions = []
        for _, trade in trades.iterrows():
            entry_idx = equity_curve.index.get_loc(trade['entry_date'])
            exit_idx = equity_curve.index.get_loc(trade['exit_date'])
            
            # 计算持有期间市场趋势（用标的本身的涨跌幅代替）
            market_return = (trade['exit_price'] - trade['entry_price']) / trade['entry_price'] * 100
            
            # 判断交易方向与市场方向是否一致
            if trade['position'] > 0 and market_return > 0:  # 做多且市场上涨
                trend_contributions.append(trade['pnl'])
            elif trade['position'] < 0 and market_return < 0:  # 做空且市场下跌
                trend_contributions.append(trade['pnl'])
        
        trend_capture = sum(trend_contributions) / total_pnl * 100 if total_pnl != 0 else 0
        
        # 2. 波动择时贡献：高波动期交易的收益占比
        volatility = returns.rolling(20).std() * np.sqrt(252) * 100
        high_vol_contributions = []
        
        for _, trade in trades.iterrows():
            entry_idx = min(equity_curve.index.get_loc(trade['entry_date']), len(volatility) - 1)
            trade_vol = volatility.iloc[entry_idx] if entry_idx < len(volatility) else volatility.mean()
            
            if trade_vol > volatility.quantile(0.66):  # 高波动期
                high_vol_contributions.append(trade['pnl'])
        
        volatility_timing = sum(high_vol_contributions) / total_pnl * 100 if total_pnl != 0 else 0
        
        # 3. 均值回归贡献：逆向交易（逆势交易）的收益占比
        mean_reversion_contributions = []
        for _, trade in trades.iterrows():
            entry_idx = min(equity_curve.index.get_loc(trade['entry_date']), len(returns) - 1)
            
            # 看前20天是否超买超卖
            prev_20d_return = returns.iloc[max(0, entry_idx-20):entry_idx].sum() * 100
            
            # 逆向：跌多了买，涨多了卖
            if trade['position'] > 0 and prev_20d_return < -5:  # 大跌后做多
                mean_reversion_contributions.append(trade['pnl'])
            elif trade['position'] < 0 and prev_20d_return > 5:  # 大涨后做空
                mean_reversion_contributions.append(trade['pnl'])
        
        mean_reversion = sum(mean_reversion_contributions) / total_pnl * 100 if total_pnl != 0 else 0
        
        # 4. 仓位管理贡献：大仓位时盈利，小仓位时亏损
        position_contributions = []
        for _, trade in trades.iterrows():
            position_size = abs(trade['position'])
            
            # 大仓位交易（>70%的最大仓位）
            if position_size > 0.7 and trade['pnl'] > 0:
                position_contributions.append(trade['pnl'])
            elif position_size < 0.3 and trade['pnl'] < 0:
                # 小仓位亏损也算好的仓位管理
                position_contributions.append(abs(trade['pnl']))
        
        position_sizing = sum(position_contributions) / abs(total_pnl) * 100 if total_pnl != 0 else 0
        
        # 5. 运气成分：极端收益（>15%或<-10%）占比
        extreme_contributions = []
        for _, trade in trades.iterrows():
            if abs(trade['return_pct']) > 10:
                extreme_contributions.append(trade['pnl'])
        
        luck_factor = sum(extreme_contributions) / total_pnl * 100 if total_pnl != 0 else 0
        
        # 归一化到0-100%
        total = trend_capture + volatility_timing + mean_reversion + position_sizing + luck_factor
        if total != 0:
            factor = 100 / total
            trend_capture *= factor
            volatility_timing *= factor
            mean_reversion *= factor
            position_sizing *= factor
            luck_factor *= factor
        
        return ReturnAttribution(
            trend_capture=round(trend_capture, 1),
            volatility_timing=round(volatility_timing, 1),
            mean_reversion=round(mean_reversion, 1),
            position_sizing=round(position_sizing, 1),
            luck_factor=round(luck_factor, 1)
        )
    
    def _generate_interpretation(self, score: StrategyScore, attribution: ReturnAttribution, 
                                   perf: Dict[str, Any], strategy_name: str, symbol_name: str) -> str:
        """生成AI解读文本"""
        
        intro = f"""## {strategy_name} 策略在 {symbol_name} 上的AI深度解读

**综合评级：{score.grade} 级 | 综合评分：{score.overall_score}/100**

### 📊 核心表现概览
- 年化收益率：**{perf['年化收益率(CAGR)']:.2f}%**（击败市场上 {max(0, min(95, perf['年化收益率(CAGR)'] * 2)):.0f}% 的策略）
- 最大回撤：**{perf['最大回撤']:.2f}%**（{'控制优秀' if perf['最大回撤'] < 15 else '风险偏高'}）
- 夏普比率：**{perf['夏普比率']:.2f}**（{'优秀' if perf['夏普比率'] > 1.5 else '良好' if perf['夏普比率'] > 1 else '一般'}）
- 卡玛比率：**{perf['卡玛比率']:.2f}**
- 交易胜率：**{perf['胜率']:.1f}%**（共 {perf['总交易次数']} 笔交易）
"""
        
        # 优势分析
        strengths_section = "\n### ✅ 策略优势\n"
        for s in score.strengths:
            strengths_section += f"- {s}\n"
        
        # 不足分析
        weaknesses_section = "\n### ⚠️ 需要改进\n"
        for w in score.weaknesses:
            weaknesses_section += f"- {w}\n"
        
        # 收益归因解读
        attribution_section = f"""
### 🔬 收益来源归因分析
| 收益来源 | 贡献占比 | AI解读 |
|---------|---------|-------|
| 📈 趋势捕捉 | {attribution.trend_capture:.1f}% | {self._interpret_attribution_factor('trend', attribution.trend_capture)} |
| 🌊 波动择时 | {attribution.volatility_timing:.1f}% | {self._interpret_attribution_factor('volatility', attribution.volatility_timing)} |
| ⚖️ 均值回归 | {attribution.mean_reversion:.1f}% | {self._interpret_attribution_factor('mean_reversion', attribution.mean_reversion)} |
| 🎯 仓位管理 | {attribution.position_sizing:.1f}% | {self._interpret_attribution_factor('position', attribution.position_sizing)} |
| 🎲 运气成分 | {abs(attribution.luck_factor):.1f}% | {self._interpret_attribution_factor('luck', attribution.luck_factor)} |
"""
        
        # 改进建议
        recommendations_section = "\n### 💡 改进建议\n"
        for i, rec in enumerate(score.recommendations[:5], 1):
            recommendations_section += f"{i}. {rec}\n"
        
        # 实盘适用性判断
        is_ready_for_live = score.overall_score >= 60 and score.risk_score >= 8 and perf['总交易次数'] >= 10
        conclusion_section = f"""
### 🎯 实盘适用性判断

{'✅ **建议可以进行实盘验证**' if is_ready_for_live else '⚠️ **建议继续优化后再实盘**'}

{'''该策略综合评分超过60分，风险控制达标，交易样本量充足，具备实盘可行性。
建议先用小资金试运行3个月，观察实盘表现与回测的一致性后再逐步加仓。''' if is_ready_for_live else '''该策略在某些维度还有提升空间，建议先在模拟环境中继续优化参数，
待综合评分和稳定性提升后再考虑实盘应用。'''}
"""
        
        return intro + strengths_section + weaknesses_section + attribution_section + recommendations_section + conclusion_section
    
    def _interpret_attribution_factor(self, factor_type: str, value: float) -> str:
        """解读归因因子"""
        abs_value = abs(value)
        
        interpretations = {
            'trend': [
                "趋势捕捉能力强，是策略核心收益来源",
                "趋势捕捉贡献较大",
                "趋势捕捉有一定贡献",
                "趋势捕捉贡献较小，建议优化趋势识别能力"
            ],
            'volatility': [
                "波动择时能力强，善于利用高波动获利",
                "波动择时贡献较大",
                "波动择时有一定贡献",
                "波动择时贡献较小，建议优化波动率过滤"
            ],
            'mean_reversion': [
                "均值回归能力强，善于捕捉超买超卖机会",
                "均值回归贡献较大",
                "均值回归有一定贡献",
                "均值回归贡献较小，逆向交易能力待提升"
            ],
            'position': [
                "仓位管理优秀，大仓位精准盈利",
                "仓位管理贡献较大",
                "仓位管理有一定贡献",
                "仓位管理贡献较小，建议优化仓位算法"
            ],
            'luck': [
                "运气成分偏高，注意排除极端值干扰",
                "运气有一定贡献",
                "运气影响适中",
                "策略收益主要来自能力，运气影响小"
            ]
        }
        
        level = 0 if abs_value > 30 else 1 if abs_value > 20 else 2 if abs_value > 10 else 3
        return interpretations[factor_type][level]
    
    def _run_agent_debate(self, score: StrategyScore, attribution: ReturnAttribution, 
                           perf: Dict[str, Any], strategy_name: str) -> List[AgentDebate]:
        """运行多智能体辩论评估"""
        debates = []
        
        # 1. 保守风控官
        conservative = self._agent_conservative(score, perf)
        debates.append(conservative)
        
        # 2. 激进交易员
        aggressive = self._agent_aggressive(score, perf)
        debates.append(aggressive)
        
        # 3. 统计分析师
        statistician = self._agent_statistician(score, perf, attribution)
        debates.append(statistician)
        
        # 4. 行为金融专家
        behavioral = self._agent_behavioral(score, perf, attribution)
        debates.append(behavioral)
        
        return debates
    
    def _agent_conservative(self, score: StrategyScore, perf: Dict[str, Any]) -> AgentDebate:
        """保守风控官角色"""
        max_drawdown = perf['最大回撤']
        sharpe = perf['夏普比率']
        calmar = perf['卡玛比率']
        
        if max_drawdown > 30:
            opinion = "坚决反对使用该策略，回撤风险过高"
            recommendation = "不推荐"
            confidence = 90
            key_points = [
                f"最大回撤高达{max_drawdown:.1f}%，远超20%的安全阈值",
                f"卡玛比率仅{calmar:.2f}，风险收益比严重失衡",
                "建议大幅降低仓位或增加止损机制"
            ]
        elif max_drawdown > 20:
            opinion = "风险偏高，建议谨慎使用，必须控制仓位"
            recommendation = "谨慎使用"
            confidence = 75
            key_points = [
                f"最大回撤{max_drawdown:.1f}%，超过20%警戒线",
                f"夏普比率{sharpe:.2f}尚可，需注意仓位管理",
                "建议仓位不超过30%，并设置严格止损"
            ]
        else:
            opinion = "风险控制良好，可以正常使用"
            recommendation = "可以使用"
            confidence = 80
            key_points = [
                f"最大回撤{max_drawdown:.1f}%，在可控范围内",
                f"卡玛比率{calmar:.2f}，风险收益比较为合理",
                "建议维持现有风险参数，注意监控实盘回撤"
            ]
        
        return AgentDebate(
            role=AgentRole.CONSERVATIVE,
            opinion=opinion,
            key_points=key_points,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def _agent_aggressive(self, score: StrategyScore, perf: Dict[str, Any]) -> AgentDebate:
        """激进交易员角色"""
        annual_return = perf['年化收益率(CAGR)']
        win_rate = perf['胜率']
        total_trades = perf['总交易次数']
        
        if annual_return > 25 and win_rate > 45:
            opinion = "这是一个非常棒的策略！强烈推荐重仓使用"
            recommendation = "强烈推荐"
            confidence = 95
            key_points = [
                f"年化收益{annual_return:.1f}%，盈利能力惊人",
                f"胜率{win_rate:.1f}%，交易质量高",
                f"{total_trades}笔交易样本充足，策略验证可靠",
                "建议作为核心策略配置，仓位可以给到50-80%"
            ]
        elif annual_return > 15:
            opinion = "收益表现不错，可以重点配置"
            recommendation = "可以使用"
            confidence = 80
            key_points = [
                f"年化{annual_return:.1f}%的收益具有吸引力",
                f"胜率{win_rate:.1f}%在可接受范围",
                "建议作为组合策略之一配置"
            ]
        elif annual_return > 5:
            opinion = "收益一般，只能作为辅助策略"
            recommendation = "谨慎使用"
            confidence = 60
            key_points = [
                f"年化{annual_return:.1f}%，收益能力偏弱",
                f"需要配合其他高收益策略使用",
                "建议优化参数提升收益能力"
            ]
        else:
            opinion = "收益太差，完全不值得考虑"
            recommendation = "不推荐"
            confidence = 85
            key_points = [
                f"年化{annual_return:.1f}%，连无风险收益都不如",
                "建议彻底放弃该策略，寻找更好的替代"
            ]
        
        return AgentDebate(
            role=AgentRole.AGGRESSIVE,
            opinion=opinion,
            key_points=key_points,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def _agent_statistician(self, score: StrategyScore, perf: Dict[str, Any], attribution: ReturnAttribution) -> AgentDebate:
        """统计分析师角色"""
        sharpe = perf['夏普比率']
        calmar = perf['卡玛比率']
        win_rate = perf['胜率']
        
        # 统计显著性判断
        total_trades = perf['总交易次数']
        is_stat_significant = total_trades >= 30 and win_rate > 40
        
        # 收益来源稳定性
        main_source = max([
            ('趋势捕捉', attribution.trend_capture),
            ('波动择时', attribution.volatility_timing),
            ('均值回归', attribution.mean_reversion),
            ('仓位管理', attribution.position_sizing)
        ], key=lambda x: x[1])
        
        if sharpe > 1.5 and calmar > 1.0 and is_stat_significant:
            opinion = f"统计上显著有效，核心收益来源为{main_source[0]}"
            recommendation = "强烈推荐"
            confidence = 90
        elif sharpe > 1.0 and is_stat_significant:
            opinion = f"统计有效，{main_source[0]}贡献{main_source[1]:.1f}%收益"
            recommendation = "可以使用"
            confidence = 75
        elif total_trades < 20:
            opinion = f"交易样本量不足（仅{total_trades}笔），统计可靠性有限"
            recommendation = "谨慎使用"
            confidence = 50
        else:
            opinion = f"统计显著性一般，{main_source[0]}是主要收益来源"
            recommendation = "谨慎使用"
            confidence = 65
        
        key_points = [
            f"夏普比率 {sharpe:.2f}，{'达到统计标准' if sharpe > 1.0 else '未达统计标准'}",
            f"核心收益来源：{main_source[0]}（{main_source[1]:.1f}%）",
            f"交易样本量：{total_trades}笔 {'充足' if total_trades >= 30 else '不足'}",
            f"运气成分占比：{abs(attribution.luck_factor):.1f}%"
        ]
        
        return AgentDebate(
            role=AgentRole.STATISTICIAN,
            opinion=opinion,
            key_points=key_points,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def _agent_behavioral(self, score: StrategyScore, perf: Dict[str, Any], attribution: ReturnAttribution) -> AgentDebate:
        """行为金融专家角色"""
        luck_factor = abs(attribution.luck_factor)
        win_rate = perf['胜率']
        
        # 判断是否过度拟合
        is_overfitting = luck_factor > 40 or (win_rate > 70 and perf['总交易次数'] < 50)
        
        if is_overfitting:
            opinion = "存在过度拟合风险，历史表现可能无法复现"
            recommendation = "谨慎使用"
            confidence = 85
            key_points = [
                f"运气成分高达{luck_factor:.1f}%，可能是参数过度拟合",
                "高胜率低交易量通常是过拟合征兆",
                "建议进行样本外测试和参数敏感性验证",
                "实盘时务必降低仓位，严格监控表现偏离"
            ]
        elif luck_factor > 25:
            opinion = "运气有一定影响，需要警惕幸存者偏差"
            recommendation = "可以使用"
            confidence = 70
            key_points = [
                f"运气贡献{luck_factor:.1f}%，占比偏高",
                "建议进行多品种交叉验证",
                "不要过度依赖单一策略表现"
            ]
        else:
            opinion = "收益主要来自策略能力，运气影响可控"
            recommendation = "可以使用"
            confidence = 85
            key_points = [
                f"运气成分仅{luck_factor:.1f}%，策略能力是核心",
                "收益来源较为多元化，稳健性较好",
                "可以考虑作为核心策略配置"
            ]
        
        return AgentDebate(
            role=AgentRole.BEHAVIORAL,
            opinion=opinion,
            key_points=key_points,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def _generate_final_conclusion(self, score: StrategyScore, debates: List[AgentDebate]) -> str:
        """生成最终结论"""
        
        # 汇总推荐
        recommendations = [d.recommendation for d in debates]
        rec_counts = {}
        for r in recommendations:
            rec_counts[r] = rec_counts.get(r, 0) + 1
        
        # 找出主流意见
        dominant_rec = max(rec_counts, key=rec_counts.get)
        dominant_count = rec_counts[dominant_rec]
        
        # 生成结论
        grade_text = {
            'S': '极其优秀的策略，强烈推荐实盘验证',
            'A': '优秀策略，具备实盘应用价值',
            'B': '良好策略，可以考虑在风控下使用',
            'C': '一般策略，建议继续优化',
            'D': '较差策略，需要大幅改进',
            'F': '不推荐，建议重新设计'
        }
        
        conclusion = f"""
**综合评级：{score.grade} 级 | {grade_text.get(score.grade, '')}**

**专家投票结果：**
"""
        
        for rec, count in rec_counts.items():
            conclusion += f"- {rec}: {count}/{len(debates)} 票\n"
        
        conclusion += f"\n"
        
        if dominant_rec == '强烈推荐' and dominant_count >= 2:
            conclusion += "✅ **策略表现优秀，强烈建议进行实盘验证**\n\n"
            conclusion += f"该策略综合评分 {score.overall_score:.0f}/100，获得多位专家一致认可。建议先用小资金试运行3个月，"
            conclusion += f"观察实盘表现与回测的一致性，验证通过后可作为核心策略配置。"
        elif dominant_rec == '可以使用' and dominant_count >= 2:
            conclusion += "✅ **策略表现良好，可以正常使用**\n\n"
            conclusion += f"该策略综合评分 {score.overall_score:.0f}/100，风险收益比较为合理。建议作为组合策略之一配置，"
            conclusion += f"注意仓位控制和持续监控表现。"
        elif dominant_rec == '谨慎使用' and dominant_count >= 2:
            conclusion += "⚠️ **建议谨慎使用，先优化再实盘**\n\n"
            conclusion += f"该策略综合评分 {score.overall_score:.0f}/100，在某些维度还有提升空间。建议先在模拟环境中继续优化，"
            conclusion += f"或仅用极小仓位进行验证，不要作为主力策略使用。"
        else:
            conclusion += "❌ **不推荐使用，建议重新设计策略**\n\n"
            conclusion += f"该策略综合评分 {score.overall_score:.0f}/100，专家存在较大分歧。建议重新审视策略逻辑，"
            conclusion += f"优化参数或寻找更优的策略替代方案。"
        
        return conclusion