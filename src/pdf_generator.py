"""
PDF报告生成器
Rock Quant - 专业量化回测报告导出
"""

import io
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, 
                                   Table, TableStyle, Image, PageBreak)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class PDFReportGenerator:
    """PDF报告生成器"""
    
    def __init__(self):
        self.available = REPORTLAB_AVAILABLE and MATPLOTLIB_AVAILABLE
        
    def check_dependencies(self):
        """检查依赖"""
        missing = []
        if not REPORTLAB_AVAILABLE:
            missing.append("reportlab")
        if not MATPLOTLIB_AVAILABLE:
            missing.append("matplotlib")
        return missing
    
    def generate_report(self, result, strategy_name, symbol_name, 
                       start_date, end_date, initial_capital, perf):
        """生成完整的PDF回测报告"""
        if not self.available:
            missing = self.check_dependencies()
            raise ImportError(f"缺少依赖: {', '.join(missing)}，请执行: pip install {' '.join(missing)}")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        styles = getSampleStyleSheet()
        
        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f77b4')
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.gray
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#2c3e50')
        )
        
        normal_style = ParagraphStyle(
            'NormalText',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            leading=14
        )
        
        # ========== 封面 ==========
        story.append(Spacer(1, 3*cm))
        story.append(Paragraph("Rock Quant 量化回测报告", title_style))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("专业量化策略验证平台", subtitle_style))
        story.append(Spacer(1, 2*cm))
        
        # 基本信息表格
        basic_info = [
            ["策略名称", strategy_name],
            ["回测标的", symbol_name],
            ["回测期间", f"{start_date} 至 {end_date}"],
            ["初始资金", f"{initial_capital:,.0f} 元"],
            ["生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ]
        
        info_table = Table(basic_info, colWidths=[4*cm, 9*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 11),
            ('ALIGN', (0,0), (0,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('TEXTCOLOR', (0,0), (0,-1), colors.gray),
            ('TEXTCOLOR', (1,0), (1,-1), colors.black),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8f9fa')),
        ]))
        story.append(info_table)
        
        # ========== 分页：核心绩效 ==========
        story.append(PageBreak())
        story.append(Paragraph("一、核心绩效指标", heading_style))
        
        # 核心指标表格
        perf_data = [
            ["指标", "数值", "指标", "数值"],
            ["总收益率", f"{perf['总收益率']:.2f}%", "年化收益率", f"{perf['年化收益率(CAGR)']:.2f}%"],
            ["最大回撤", f"{perf['最大回撤']:.2f}%", "卡玛比率", f"{perf['卡玛比率']:.2f}"],
            ["夏普比率", f"{perf['夏普比率']:.2f}", "索提诺比率", f"{perf['索提诺比率']:.2f}"],
            ["交易次数", str(perf['总交易次数']), "胜率", f"{perf['胜率']:.1f}%"],
            ["盈亏比", f"{perf['盈亏比']:.2f}", "盈利因子", f"{perf['盈利因子']:.2f}"],
        ]
        
        perf_table = Table(perf_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        perf_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(perf_table)
        
        # ========== 净值曲线图 ==========
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("二、净值曲线与回撤", heading_style))
        
        img_buffer = self._generate_equity_chart(result)
        img = Image(img_buffer, width=16*cm, height=10*cm)
        story.append(img)
        
        # ========== 分页：月度收益热力图 ==========
        story.append(PageBreak())
        story.append(Paragraph("三、月度收益分析", heading_style))
        
        heatmap_buffer = self._generate_monthly_heatmap(result)
        heatmap_img = Image(heatmap_buffer, width=15*cm, height=10*cm)
        story.append(heatmap_img)
        
        # ========== 交易统计 ==========
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("四、交易统计", heading_style))
        
        trade_stats = [
            ["统计项", "数值", "统计项", "数值"],
            ["总交易次数", str(perf['总交易次数']), "盈利交易次数", str(int(perf['总交易次数'] * perf['胜率'] / 100))],
            ["平均单笔收益", f"{perf['平均单笔收益']:.2f}%", "平均盈利交易", f"{perf['平均盈利交易收益']:.2f}%"],
            ["最大单笔盈利", f"{perf['单笔最大盈利']:.2f}%", "最大单笔亏损", f"{perf['单笔最大亏损']:.2f}%"],
            ["最大连续盈利天数", str(perf['最大连续盈利天数']), "最大连续亏损天数", str(perf['最大连续亏损天数'])],
        ]
        
        trade_table = Table(trade_stats, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        trade_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2ca02c')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(trade_table)
        
        # ========== 分页：风险指标 ==========
        story.append(PageBreak())
        story.append(Paragraph("五、风险指标详解", heading_style))
        
        risk_data = [
            ["风险指标", "数值", "说明"],
            ["年化波动率", f"{perf['年化波动率']:.2f}%", "策略收益率的年化标准差，衡量整体风险"],
            ["下行波动率", f"{perf['下行波动率']:.2f}%", "仅考虑负收益的波动率，衡量下行风险"],
            ["VaR (95%)", f"{perf['VaR(95%)']:.2f}%", "95%置信水平下单日最大可能亏损"],
            ["CVaR (95%)", f"{perf['CVaR(95%)']:.2f}%", "超过VaR部分的平均亏损，衡量尾部风险"],
            ["最大回撤持续天数", str(perf['最大回撤持续天数']), "从回撤开始到恢复新高的天数"],
        ]
        
        risk_table = Table(risk_data, colWidths=[3*cm, 2.5*cm, 8.5*cm])
        risk_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (0,0), (1,-1), 'CENTER'),
            ('ALIGN', (2,0), (2,-1), 'LEFT'),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ff7f0e')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(risk_table)
        
        # ========== 免责声明 ==========
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph("免责声明", styles['Heading3']))
        
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            leading=12
        )
        
        disclaimer = """
        本报告仅为量化策略历史回测结果展示，不构成任何投资建议。回测收益不代表未来
        实际收益，市场有风险，投资需谨慎。所有回测结果基于历史数据和特定参数配置，
        实际交易可能因滑点、手续费、市场流动性等因素产生显著差异。使用本平台进行
        任何投资决策所产生的风险由使用者自行承担。
        """
        story.append(Paragraph(disclaimer, disclaimer_style))
        
        # 页脚
        story.append(Spacer(1, 1*cm))
        footer = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.lightgrey
        )
        story.append(Paragraph("Generated by Rock Quant - 顽岩量化", footer))
        
        # 构建文档
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _generate_equity_chart(self, result):
        """生成净值曲线图"""
        fig, ax1 = plt.subplots(figsize=(12, 6), dpi=100)
        
        ax1.plot(result.equity_curve.index, result.equity_curve.values, 
                color='#1f77b4', linewidth=2, label='策略净值')
        ax1.set_ylabel('净值', fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        ax2 = ax1.twinx()
        ax2.fill_between(result.drawdown_curve.index, 
                         result.drawdown_curve.values * 100, 0,
                         color='#ff7f0e', alpha=0.3, label='回撤')
        ax2.set_ylabel('回撤 (%)', fontsize=11)
        ax2.set_ylim([-100, 0])
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.title('策略净值曲线与回撤', fontsize=14, pad=20)
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        return buffer
    
    def _generate_monthly_heatmap(self, result):
        """生成月度收益热力图"""
        returns = pd.Series(result.equity_curve).pct_change().dropna()
        
        monthly_returns = returns.groupby([
            returns.index.year, 
            returns.index.month
        ]).apply(lambda x: (1 + x).prod() - 1)
        
        monthly_returns = monthly_returns.unstack()
        monthly_returns.columns = ['1月', '2月', '3月', '4月', '5月', '6月', 
                                 '7月', '8月', '9月', '10月', '11月', '12月'][:len(monthly_returns.columns)]
        
        fig, ax = plt.subplots(figsize=(14, 6), dpi=100)
        im = ax.imshow(monthly_returns.values * 100, cmap='RdYlGn', vmin=-10, vmax=10, alpha=0.8)
        
        ax.set_yticks(np.arange(len(monthly_returns.index)))
        ax.set_yticklabels(monthly_returns.index)
        ax.set_xticks(np.arange(len(monthly_returns.columns)))
        ax.set_xticklabels(monthly_returns.columns)
        
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.set_label('月度收益率 (%)')
        
        for i in range(len(monthly_returns.index)):
            for j in range(len(monthly_returns.columns)):
                if j < len(monthly_returns.values[i]):
                    val = monthly_returns.values[i, j] * 100
                    text = ax.text(j, i, f'{val:.1f}%', ha='center', va='center', 
                                  color='white' if abs(val) > 5 else 'black', fontsize=9)
        
        plt.title('月度收益热力图', fontsize=14, pad=20)
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        return buffer
