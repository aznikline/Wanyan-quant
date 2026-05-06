import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import BacktestConfig
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
    page_title="绩效分析 - Rock Quant 2.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 绩效深度分析")
st.markdown("月度热力图、盈亏分布、收益统计的专业级可视化分析")
st.markdown("---")

# 侧边栏参数
st.sidebar.header("回测参数")

strategy_name = st.sidebar.selectbox("选择策略", get_all_strategies())
loader = DataLoader()
preset_symbols = list(loader.preset_symbols.keys())
symbol_name = st.sidebar.selectbox("选择标的", preset_symbols)

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("开始日期", pd.to_datetime("2020-01-01"))
with col2:
    end_date = st.date_input("结束日期", pd.to_datetime("2023-12-31"))

initial_capital = st.sidebar.number_input("初始资金", value=1000000, step=100000)

if st.sidebar.button("🚀 开始分析", type="primary"):
    with st.spinner("正在进行深度绩效分析..."):
        # 执行回测
        symbol_code = loader.preset_symbols[symbol_name]
        data = loader.load_data(symbol_code, str(start_date), str(end_date))
        config = BacktestConfig(initial_capital=initial_capital)
        engine = BacktestEngine(config)
        strategy = create_strategy(strategy_name)
        signals = strategy.generate_signals(data)
        result = engine.run(data, signals)
        
        st.success("分析完成!")
        
        # ========== 第一部分：月度收益率热力图 ==========
        st.markdown("## 🗓️ 月度收益率热力图")
        st.caption("颜色越深代表收益率越高，红色=亏损，绿色=盈利，一眼看清季节性规律")
        
        # 计算月度收益率
        equity_daily = result.equity_curve
        monthly_equity = equity_daily.resample('M').last()
        monthly_returns = monthly_equity.pct_change().dropna() * 100
        
        # 构建年月矩阵
        monthly_data = []
        for date, ret in monthly_returns.items():
            monthly_data.append({
                'year': date.year,
                'month': date.month,
                'return': round(ret, 2)
            })
        
        df_monthly = pd.DataFrame(monthly_data)
        
        # 创建热力图数据透视表
        pivot_data = df_monthly.pivot(index='year', columns='month', values='return')
        pivot_data.columns = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        
        # 绘制热力图
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index.astype(str),
            colorscale='RdYlGn',
            zmid=0,
            text=[[f"{v:.2f}%" for v in row] for row in pivot_data.values],
            texttemplate='%{text}',
            textfont={"size": 11},
            hoverongaps=False,
            showscale=True,
            colorbar=dict(title="收益率%", tickformat=".1f")
        ))
        
        fig_heatmap.update_layout(
            title='月度收益率热力图',
            height=400,
            xaxis_title='月份',
            yaxis_title='年份'
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # 月度统计摘要
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            best_month = df_monthly.loc[df_monthly['return'].idxmax()]
            st.metric("历史最佳单月", f"{best_month['return']:.2f}%", 
                     f"{int(best_month['year'])}年{int(best_month['month'])}月")
        with col2:
            worst_month = df_monthly.loc[df_monthly['return'].idxmin()]
            st.metric("历史最差单月", f"{worst_month['return']:.2f}%", 
                     f"{int(worst_month['year'])}年{int(worst_month['month'])}月", delta_color="inverse")
        with col3:
            positive_months = len(df_monthly[df_monthly['return'] > 0])
            total_months = len(df_monthly)
            st.metric("月度胜率", f"{positive_months/total_months*100:.1f}%", 
                     f"{positive_months}/{total_months}个月")
        with col4:
            avg_positive = df_monthly[df_monthly['return'] > 0]['return'].mean() if len(df_monthly[df_monthly['return'] > 0]) > 0 else 0
            avg_negative = df_monthly[df_monthly['return'] < 0]['return'].mean() if len(df_monthly[df_monthly['return'] < 0]) > 0 else 0
            st.metric("月均盈亏比", f"{abs(avg_positive/avg_negative) if avg_negative != 0 else 0:.2f}",
                     f"月均盈{avg_positive:.1f}%/月均亏{avg_negative:.1f}%")
        
        st.markdown("---")
        
        # ========== 第二部分：年度收益率对比 ==========
        st.markdown("## 📈 年度收益率对比")
        st.caption("分年度的策略表现统计，查看策略的年份稳定性")
        
        yearly_equity = equity_daily.resample('Y').last()
        yearly_returns = yearly_equity.pct_change().dropna() * 100
        
        # 计算基准收益率（买入持有）
        benchmark_yearly = data['close'].resample('Y').last().pct_change().dropna() * 100
        
        yearly_data = []
        for date in yearly_returns.index:
            year = date.year
            strat_ret = yearly_returns.get(date, 0)
            bench_ret = benchmark_yearly.get(date, 0)
            yearly_data.append({
                '年份': str(year),
                '策略收益率': round(strat_ret, 2),
                '基准收益率': round(bench_ret, 2),
                '超额收益': round(strat_ret - bench_ret, 2)
            })
        
        df_yearly = pd.DataFrame(yearly_data)
        
        # 绘制年度对比柱状图
        fig_yearly = go.Figure()
        fig_yearly.add_trace(go.Bar(
            x=df_yearly['年份'],
            y=df_yearly['策略收益率'],
            name='策略收益率',
            marker_color='#1f77b4',
            text=df_yearly['策略收益率'].astype(str) + '%',
            textposition='auto'
        ))
        fig_yearly.add_trace(go.Bar(
            x=df_yearly['年份'],
            y=df_yearly['基准收益率'],
            name='基准收益率',
            marker_color='#ff7f0e',
            text=df_yearly['基准收益率'].astype(str) + '%',
            textposition='auto'
        ))
        
        fig_yearly.update_layout(
            title='年度收益率对比（策略 vs 买入持有）',
            barmode='group',
            height=400,
            yaxis_title='收益率 %'
        )
        
        st.plotly_chart(fig_yearly, use_container_width=True)
        
        # 年度超额收益表格
        st.dataframe(df_yearly, use_container_width=True)
        
        st.markdown("---")
        
        # ========== 第三部分：单笔交易盈亏分布 ==========
        st.markdown("## 💰 单笔交易盈亏分布")
        st.caption("分析每笔交易的盈亏统计，识别策略的盈亏分布特征")
        
        trades = result.trades
        if len(trades) > 0:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # 盈亏分布直方图
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Histogram(
                    x=trades[trades['return_pct'] > 0]['return_pct'],
                    name='盈利交易',
                    marker_color='#2ecc71',
                    opacity=0.7,
                    nbinsx=20
                ))
                fig_hist.add_trace(go.Histogram(
                    x=trades[trades['return_pct'] < 0]['return_pct'],
                    name='亏损交易',
                    marker_color='#e74c3c',
                    opacity=0.7,
                    nbinsx=20
                ))
                
                fig_hist.update_layout(
                    title='单笔交易收益率分布',
                    height=400,
                    xaxis_title='单笔交易收益率 %',
                    yaxis_title='交易数量',
                    barmode='overlay'
                )
                
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                # 盈亏箱线图
                fig_box = go.Figure()
                fig_box.add_trace(go.Box(
                    y=trades['return_pct'],
                    name='所有交易',
                    marker_color='#3498db'
                ))
                fig_box.add_trace(go.Box(
                    y=trades[trades['return_pct'] > 0]['return_pct'],
                    name='仅盈利',
                    marker_color='#2ecc71'
                ))
                fig_box.add_trace(go.Box(
                    y=trades[trades['return_pct'] < 0]['return_pct'],
                    name='仅亏损',
                    marker_color='#e74c3c'
                ))
                
                fig_box.update_layout(
                    title='交易盈亏箱线图统计',
                    height=400,
                    yaxis_title='收益率 %'
                )
                
                st.plotly_chart(fig_box, use_container_width=True)
            
            # 交易统计卡片
            st.markdown("### 📋 交易统计摘要")
            
            col1, col2, col3, col4 = st.columns(4)
            
            winning_trades = trades[trades['return_pct'] > 0]
            losing_trades = trades[trades['return_pct'] < 0]
            
            with col1:
                st.metric("总交易次数", len(trades))
                st.metric("盈利交易数", len(winning_trades))
                st.metric("亏损交易数", len(losing_trades))
            with col2:
                avg_win = winning_trades['return_pct'].mean() if len(winning_trades) > 0 else 0
                avg_loss = losing_trades['return_pct'].mean() if len(losing_trades) > 0 else 0
                st.metric("平均单笔盈利", f"{avg_win:.2f}%")
                st.metric("平均单笔亏损", f"{avg_loss:.2f}%")
                st.metric("盈亏比", f"{abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}")
            with col3:
                max_win = trades['return_pct'].max()
                max_loss = trades['return_pct'].min()
                st.metric("单笔最大盈利", f"{max_win:.2f}%")
                st.metric("单笔最大亏损", f"{max_loss:.2f}%")
                st.metric("盈亏极值比", f"{abs(max_win/max_loss) if max_loss != 0 else 0:.2f}")
            with col4:
                p75_win = winning_trades['return_pct'].quantile(0.75) if len(winning_trades) > 0 else 0
                p25_loss = losing_trades['return_pct'].quantile(0.25) if len(losing_trades) > 0 else 0
                st.metric("75%分位盈利", f"{p75_win:.2f}%")
                st.metric("25%分位亏损", f"{p25_loss:.2f}%")
                st.metric("交易胜率", f"{len(winning_trades)/len(trades)*100:.1f}%")
            
            st.markdown("---")
            
            # ========== 第四部分：连续盈亏分析 ==========
            st.markdown("## 🔄 连续盈亏分析")
            st.caption("分析连续盈利和连续亏损的分布特征，识别策略的极端风险")
            
            # 计算连续盈亏
            trade_results = trades['return_pct'].values
            consecutive_stats = []
            current_streak = 1
            current_type = 'win' if trade_results[0] > 0 else 'loss'
            
            for i in range(1, len(trade_results)):
                if (trade_results[i] > 0 and current_type == 'win') or (trade_results[i] < 0 and current_type == 'loss'):
                    current_streak += 1
                else:
                    consecutive_stats.append({
                        'type': current_type,
                        'streak': current_streak
                    })
                    current_streak = 1
                    current_type = 'win' if trade_results[i] > 0 else 'loss'
            
            consecutive_stats.append({
                'type': current_type,
                'streak': current_streak
            })
            
            df_consecutive = pd.DataFrame(consecutive_stats)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # 连续盈利分布
                win_streaks = df_consecutive[df_consecutive['type'] == 'win']
                if len(win_streaks) > 0:
                    fig_win = go.Figure()
                    fig_win.add_trace(go.Bar(
                        x=win_streaks['streak'].value_counts().index,
                        y=win_streaks['streak'].value_counts().values,
                        marker_color='#2ecc71'
                    ))
                    fig_win.update_layout(
                        title='连续盈利次数分布',
                        height=350,
                        xaxis_title='连续盈利笔数',
                        yaxis_title='出现次数'
                    )
                    st.plotly_chart(fig_win, use_container_width=True)
                    
                    max_win_streak = win_streaks['streak'].max()
                    st.info(f"🔝 最长连续盈利：{max_win_streak}笔交易")
            
            with col2:
                # 连续亏损分布
                loss_streaks = df_consecutive[df_consecutive['type'] == 'loss']
                if len(loss_streaks) > 0:
                    fig_loss = go.Figure()
                    fig_loss.add_trace(go.Bar(
                        x=loss_streaks['streak'].value_counts().index,
                        y=loss_streaks['streak'].value_counts().values,
                        marker_color='#e74c3c'
                    ))
                    fig_loss.update_layout(
                        title='连续亏损次数分布',
                        height=350,
                        xaxis_title='连续亏损笔数',
                        yaxis_title='出现次数'
                    )
                    st.plotly_chart(fig_loss, use_container_width=True)
                    
                    max_loss_streak = loss_streaks['streak'].max()
                    st.warning(f"⚠️  最长连续亏损：{max_loss_streak}笔交易")
            
            st.markdown("---")
            
            # ========== 第五部分：每日盈亏分析 ==========
            st.markdown("## 📅 每日盈亏统计")
            st.caption("从日度维度分析策略表现的分布特征")
            
            daily_returns = equity_daily.pct_change().dropna() * 100
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # QQ图 - 检验收益率正态性
                sorted_returns = np.sort(daily_returns.values)
                normal_quantiles = np.random.normal(0, 1, len(sorted_returns))
                normal_quantiles = np.sort(normal_quantiles)
                
                fig_qq = go.Figure()
                fig_qq.add_trace(go.Scatter(
                    x=normal_quantiles,
                    y=sorted_returns,
                    mode='markers',
                    name='日收益率',
                    marker=dict(size=4, color='#1f77b4')
                ))
                
                # 添加对角线
                min_val = min(normal_quantiles.min(), sorted_returns.min())
                max_val = max(normal_quantiles.max(), sorted_returns.max())
                fig_qq.add_trace(go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name='正态分布基准',
                    line=dict(color='red', dash='dash')
                ))
                
                fig_qq.update_layout(
                    title='Q-Q图 - 日收益率分布正态性检验',
                    height=400,
                    xaxis_title='正态分位数',
                    yaxis_title='实际日收益率分位数 %'
                )
                
                st.plotly_chart(fig_qq, use_container_width=True)
            
            with col2:
                # 日收益率分布与核密度估计
                fig_dist = go.Figure()
                fig_dist.add_trace(go.Histogram(
                    x=daily_returns.values,
                    name='日收益率',
                    marker_color='#1f77b4',
                    opacity=0.6,
                    nbinsx=50,
                    histnorm='probability density'
                ))
                
                # 添加KDE曲线
                from scipy import stats
                kde = stats.gaussian_kde(daily_returns.values)
                x_range = np.linspace(daily_returns.min(), daily_returns.max(), 200)
                fig_dist.add_trace(go.Scatter(
                    x=x_range,
                    y=kde(x_range),
                    mode='lines',
                    name='核密度估计',
                    line=dict(color='red', width=2)
                ))
                
                fig_dist.update_layout(
                    title='日收益率概率密度分布',
                    height=400,
                    xaxis_title='日收益率 %',
                    yaxis_title='概率密度'
                )
                
                st.plotly_chart(fig_dist, use_container_width=True)
            
            # 日度统计摘要
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("日均收益率", f"{daily_returns.mean():.2f}%")
                st.metric("日收益率中位数", f"{daily_returns.median():.2f}%")
            with col2:
                st.metric("日波动率", f"{daily_returns.std():.2f}%")
                st.metric("偏度系数", f"{stats.skew(daily_returns.values):.2f}")
            with col3:
                st.metric("峰度系数", f"{stats.kurtosis(daily_returns.values):.2f}")
                st.metric("正收益天数占比", f"{(daily_returns > 0).mean()*100:.1f}%")
            with col4:
                st.metric("单日最大盈利", f"{daily_returns.max():.2f}%")
                st.metric("单日最大亏损", f"{daily_returns.min():.2f}%")
            
            st.info("💡 **解读建议**：偏度为正表示收益分布右偏（厚尾盈利），峰度>3表示收益分布有肥尾特征（极端行情出现概率高于正态分布）。")
        
        else:
            st.warning("该策略在当前参数和标的下没有产生任何交易，请调整参数或选择其他策略。")

st.markdown("---")
st.caption("Rock Quant 2.0 - 顽岩量价模型 | 专业级绩效分析")
