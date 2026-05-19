# ClawHub Skill 提交申请

## Skill 基本信息

| 项目 | 内容 |
|------|------|
| Skill 名称 | rockquant |
| 显示名称 | 顽岩量化 - Rock Quant |
| 版本号 | 2.6.0 |
| 作者 | Rock Quant Team |
| 许可证 | MIT |
| 分类 | finance |
| 标签 | quant, backtest, ai-analysis, trading, strategy |

## 项目描述

Rock Quant 是一个面向个人量化交易者的轻量级量价策略验证平台，采用纯Python规则引擎实现的AI智能分析系统，无需LLM即可提供专业级的策略评估。

## 核心特性

- ✅ 20+ 经典量价策略（趋势类8个、震荡类6个、成交量类4个）
- ✅ 全向量化回测引擎，速度比传统循环快5-10倍
- ✅ 5维度AI智能评分系统（收益/风险/调整后收益/稳定性/交易质量）
- ✅ S/A/B/C/D/F 六级评级体系
- ✅ 4位AI专家多智能体辩论评估（风控/交易/统计/行为金融）
- ✅ 5维度收益归因分析（趋势捕捉/波动择时/均值回归/仓位管理/运气成分）
- ✅ 完整AI解读报告自动生成
- ✅ 纯Python规则引擎，无LLM依赖，10ms级响应，结果100%可复现
- ✅ CLI命令行工具，支持脚本调用
- ✅ Streamlit可视化交互界面

## 命令说明

| 命令 | 功能 |
|------|------|
| rockquant list | 列出所有20个可用策略 |
| rockquant run <策略名> | 运行指定策略的回测 |
| rockquant analyze <策略名> | AI深度分析策略表现 |
| rockquant factors | 列出所有量价因子 |
| rockquant report <策略名> | 生成PDF分析报告 |

## 项目仓库

GitHub: https://github.com/aznikline/Wanyan-quant

## 安装方式

```bash
# 1. 克隆项目
git clone https://github.com/aznikline/Wanyan-quant.git
cd Wanyan-quant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装CLI工具
pip install -e .

# 4. 使用
rockquant list
rockquant analyze 双均线策略
```

## OpenClaw Skill 集成

本Skill已支持OpenClaw原生集成，可在OpenClaw环境中直接调用：

```python
from skills import rockquant

# 运行回测
result = rockquant.run("双均线策略", short_period=10, long_period=30)

# AI深度分析
analysis = rockquant.analyze("RSI超买超卖策略")

# 批量对比
comparison = rockquant.compare(["双均线", "MACD", "RSI"])
```

## 性能基准

测试环境：Intel i7-12700H, 32GB RAM

| 任务 | 耗时 |
|------|------|
| 单策略回测（1年日频） | ~50ms |
| AI完整分析（5维度+4智能体辩论） | ~10ms |
| 批量对比20个策略 | ~1s |
| 参数优化（1000组） | ~5s |

## 发布说明

这是Rock Quant Skill的首次发布版本，所有核心功能均已完成测试并稳定运行28天以上。

## 联系方式

GitHub Issues: https://github.com/aznikline/Wanyan-quant/issues
