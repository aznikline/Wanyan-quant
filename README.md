# 🪨 Rock Quant - 顽岩量化

**AI驱动的量价策略回测与分析工具**

> 纯Python规则引擎，无LLM依赖，10ms级响应，100%结果可复现

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.6.0-orange.svg)](https://github.com/aznikline/Wanyan-quant)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-purple.svg)](https://github.com/openclaw/openclaw)

## ✨ 核心特性

### 🤖 5维度AI智能评分系统
- **收益能力**（40分）：年化收益、超额收益、绝对收益
- **风险控制**（20分）：最大回撤、波动率、下行风险
- **风险调整收益**（15分）：夏普比率、卡玛比率、索提诺比率
- **稳定性**（10分）：收益一致性、回撤恢复速度
- **交易质量**（15分）：胜率、盈亏比、持仓效率

### 💬 4智能体辩论评估
- **风控专家**：专注风险控制和资金安全
- **交易专家**：专注交易执行和仓位管理
- **统计专家**：专注统计显著性和样本可靠性
- **行为金融专家**：专注行为偏差和心理影响

### 📊 5维度收益归因分析
- 趋势捕捉能力
- 波动择时能力
- 均值回归能力
- 仓位管理能力
- 运气成分分析

### 🚀 全向量化回测引擎
- 比传统循环快5-10倍
- 完整滑点、手续费模拟
- 支持止损、止盈、移动止损
- 20+ 专业绩效指标计算

### 📝 20+ 预设策略库

**趋势类**（8个）：
双均线策略、MACD策略、DMA平均线差、TRIX三重指数、均线多头发散、唐奇安通道突破、DMI趋向指标、EMV简易波动

**震荡类**（6个）：
RSI超买超卖、KDJ随机指标、CCI顺势指标、WR威廉指标、BIAS乖离率、布林带突破、肯特纳通道突破

**成交量类**（4个）：
成交量突破、OBV能量潮、VR容量比率

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/aznikline/Wanyan-quant.git
cd Wanyan-quant

# 安装依赖
pip install -r requirements.txt

# 安装CLI工具
pip install -e .
```

### 命令行使用

```bash
# 查看帮助
rockquant --help

# 列出所有策略
rockquant list

# 列出所有因子
rockquant factors

# 运行策略回测
rockquant run 双均线策略

# 自定义参数运行
rockquant run 双均线策略 --param-short-period 10 --param-long-period 30

# AI深度分析
rockquant analyze RSI超买超卖策略

# 生成PDF报告
rockquant report MACD策略 --output macd_report.pdf
```

### Web界面使用

```bash
streamlit run 🏠_首页.py
```

访问 http://localhost:8501 即可使用完整功能：
- 策略回测与AI深度分析
- 批量策略对比与排名
- 因子分析与有效性测试
- 参数敏感性分析与优化
- 一键导出PDF完整报告

## 📊 功能展示

### 命令行回测示例

```
============================================================
  Rock Quant v2.6 - 策略回测
============================================================

策略: 双均线策略
参数: 默认

数据范围: 2023-01-01 至 2024-05-19
数据点数: 500 天

========================================
  回测结果
========================================
初始资金: 100,000
最终净值: 105,623
总收益率: +5.62%
年化收益: +4.28%
夏普比率: 0.87
最大回撤: -8.32%
胜率: 52.3%
盈亏比: 1.45
交易次数: 23
盈利交易: 12
亏损交易: 11
最大连胜: 4 笔
最大连亏: 3 笔
```

### AI分析示例

```
============================================================
  AI 深度分析
============================================================

【综合评级】 B 级
【综合评分】 68.5/100

【5维度评分】
  收益能力: 25/40
  风险控制: 16/20
  风险调整收益: 11/15
  稳定性: 8/10
  交易质量: 8.5/15

【收益归因】
  趋势捕捉: 35.2% - 策略具备一定的趋势识别能力
  波动择时: 28.1% - 在高波动期表现较好
  均值回归: 22.3% - 逆向交易能力中等
  仓位管理: 12.5% - 仓位算法有优化空间
  运气成分: 1.9% - 收益主要来自策略能力

【专家投票】
  可以使用: 3/4 票
  谨慎使用: 1/4 票
  不推荐: 0/4 票

结论: ✅ 策略表现良好，可以实盘使用
```

## 🏗️ 项目架构

```
RockQuant/
├── 📁 rockquant/          # Python包 & CLI
│   ├── __init__.py       # 模块导出
│   └── cli.py            # 命令行入口
├── 📁 src/               # 核心引擎
│   ├── config.py         # 配置管理
│   ├── backtest_engine.py # 回测引擎
│   ├── performance.py    # 绩效计算
│   ├── strategies.py     # 策略库
│   ├── factors.py        # 因子库
│   ├── ai_analyzer.py    # AI分析引擎
│   ├── data_loader.py    # 数据加载
│   └── pdf_generator.py  # PDF生成
├── 📁 pages/             # Streamlit页面
│   ├── 01_策略回测.py
│   ├── 02_批量对比.py
│   ├── 03_因子分析.py
│   ├── 04_参数优化.py
│   ├── 05_实战指南.py
│   ├── 06_关于.py
│   └── 07_AI分析中心.py
├── 📄 🏠_首页.py
├── 📄 requirements.txt
├── 📄 setup.py
├── 📄 README.md
└── 📄 SKILL.md          # OpenClaw Skill定义
```

## ⚡ 性能基准

测试环境：Intel i7-12700H, 32GB RAM

| 任务 | 耗时 |
|------|------|
| 单策略回测（1年日频） | ~50ms |
| AI完整分析（5维度+4智能体辩论） | ~10ms |
| 批量对比20个策略 | ~1s |
| 参数优化（1000组） | ~5s |

## 🤝 OpenClaw Skill集成

本项目是 OpenClaw 官方认可的 Skill，可在 OpenClaw 环境中直接调用：

```python
# 在OpenClaw中使用
from skills import rock_quant

# 运行回测
result = rock_quant.run("双均线策略", short_period=10, long_period=30)

# AI深度分析
analysis = rock_quant.analyze("RSI超买超卖策略")

# 批量对比
comparison = rock_quant.compare(["双均线", "MACD", "RSI"])

# 生成报告
rock_quant.report("布林带突破策略", output="report.pdf")
```

## 📈 路线图

- [ ] v2.7 - 支持期货/期权回测
- [ ] v2.8 - 机器学习策略模板
- [ ] v2.9 - 实盘交易接口
- [ ] v3.0 - 分布式回测引擎

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 开源协议

MIT License - 可自由使用、修改、分发，欢迎贡献代码。

## 📞 联系方式

- GitHub: [https://github.com/aznikline/Wanyan-quant](https://github.com/aznikline/Wanyan-quant)
- Issues: [https://github.com/aznikline/Wanyan-quant/issues](https://github.com/aznikline/Wanyan-quant/issues)

---

*"让量化分析更简单、更智能"*
