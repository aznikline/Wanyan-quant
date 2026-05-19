---
name: rock-quant
title: 顽岩量化 - Rock Quant
description: AI驱动的量价策略回测与分析工具，支持20+经典策略、5维度智能评分、多智能体辩论评估
version: 2.6.0
author: Rock Quant Team
license: MIT
tags:
  - quant
  - backtest
  - ai-analysis
  - trading
  - strategy
category: finance
created: 2026-04-22
updated: 2026-05-19

commands:
  - name: run
    description: 运行策略回测
    usage: rockquant run <strategy> [options]
    examples:
      - rockquant run 双均线策略 --param-short-period 10 --param-long-period 30
      - rockquant run RSI超买超卖策略 --capital 200000

  - name: analyze
    description: AI深度分析策略表现
    usage: rockquant analyze <strategy> [options]
    examples:
      - rockquant analyze 布林带突破策略
      - rockquant analyze MACD策略 --symbol 600000.SH

  - name: list
    description: 列出所有可用策略
    usage: rockquant list

  - name: factors
    description: 列出所有量价因子
    usage: rockquant factors

  - name: report
    description: 生成PDF分析报告
    usage: rockquant report <strategy> --output <file>
    examples:
      - rockquant report 唐奇安通道突破策略 --output backtest.pdf

features:
  - 20+ 经典量价策略，覆盖趋势、震荡、成交量三大类
  - 全向量化回测引擎，速度比传统循环快5-10倍
  - 5维度AI智能评分系统（收益/风险/调整后收益/稳定性/交易质量）
  - S/A/B/C/D/F 六级评级体系
  - 4位AI专家多智能体辩论评估（风控/交易/统计/行为金融）
  - 5维度收益归因分析（趋势捕捉/波动择时/均值回归/仓位管理/运气成分）
  - 完整AI解读报告自动生成
  - 纯Python规则引擎，无LLM依赖，10ms级响应，结果100%可复现

quickstart: |
  # 安装
  pip install -e .

  # 查看所有策略
  rockquant list

  # 运行回测
  rockquant run 双均线策略

  # AI深度分析
  rockquant analyze RSI超买超卖策略

  # 查看所有因子
  rockquant factors

repository: https://github.com/aznikline/Wanyan-quant
homepage: https://github.com/aznikline/Wanyan-quant
---

# Rock Quant - 顽岩量化

## 简介

Rock Quant 是一个面向个人量化交易者的轻量级量价策略验证平台，采用纯Python规则引擎实现的AI智能分析系统，无需LLM即可提供专业级的策略评估。

## 核心特性

### 🚀 超快回测引擎
- 全向量化计算设计，比传统循环快5-10倍
- 完整的滑点、手续费、仓位管理模拟
- 支持止损、止盈、移动止损等风控机制

### 🤖 5维度AI智能评分
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

### 📊 5维度收益归因
- 趋势捕捉能力
- 波动择时能力
- 均值回归能力
- 仓位管理能力
- 运气成分分析

### 📝 20+ 预设策略
- **趋势类**：双均线、MACD、DMA、TRIX、DMI、唐奇安通道、均线多头发散
- **震荡类**：RSI、KDJ、CCI、WR、BIAS、布林带、肯特纳通道
- **成交量类**：成交量突破、OBV能量潮、VR容量比率、EMV简易波动

## 快速开始

```bash
# 克隆项目
git clone https://github.com/aznikline/Wanyan-quant.git
cd Wanyan-quant

# 安装依赖
pip install -r requirements.txt

# 安装CLI
pip install -e .

# 运行CLI
rockquant --help
rockquant list
rockquant analyze 双均线策略

# 启动Web界面
streamlit run 🏠_首页.py
```

## 命令行使用

### 列出所有策略
```bash
rockquant list
```

### 运行策略回测
```bash
# 基本使用
rockquant run 双均线策略

# 自定义参数
rockquant run 双均线策略 --param-short-period 10 --param-long-period 30

# 自定义初始资金
rockquant run RSI超买超卖策略 --capital 200000
```

### AI深度分析
```bash
rockquant analyze 布林带突破策略
```

### 列出所有因子
```bash
rockquant factors
```

## Web界面使用

```bash
streamlit run 🏠_首页.py
```

访问 http://localhost:8501 即可使用完整的Web界面，包含：
- 策略回测与AI分析
- 批量策略对比
- 因子分析与有效性测试
- 参数敏感性分析
- PDF报告导出

## 项目架构

```
RockQuant/
├── 📁 rockquant/          # CLI与Python包
│   ├── __init__.py
│   └── cli.py
├── 📁 src/                # 核心引擎
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── backtest_engine.py # 回测引擎
│   ├── performance.py     # 绩效计算
│   ├── strategies.py      # 策略库
│   ├── factors.py         # 因子库
│   ├── ai_analyzer.py     # AI分析引擎
│   ├── data_loader.py     # 数据加载
│   └── pdf_generator.py   # PDF生成
├── 📁 pages/              # Streamlit页面
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
└── 📄 SKILL.md           # 本文件
```

## OpenClaw 集成

本项目是 OpenClaw 官方认可的 Skill，可在 OpenClaw 环境中直接调用：

```python
# 在OpenClaw中使用
from skills import rock_quant

# 运行回测
result = rock_quant.run("双均线策略", short_period=10, long_period=30)

# AI分析
analysis = rock_quant.analyze("RSI超买超卖策略")

# 生成报告
rock_quant.report("MACD策略", output="report.pdf")
```

## 性能基准

测试环境：Intel i7-12700H, 32GB RAM

| 任务 | 耗时 |
|------|------|
| 单策略回测（1年日频） | ~50ms |
| AI完整分析（5维度+4智能体辩论） | ~10ms |
| 批量对比20个策略 | ~1s |
| 参数优化（1000组） | ~5s |

## 开源协议

MIT License - 可自由使用、修改、分发，欢迎贡献代码。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 联系方式

- GitHub: https://github.com/aznikline/Wanyan-quant
- Issues: https://github.com/aznikline/Wanyan-quant/issues

---

*"让量化分析更简单、更智能"*
