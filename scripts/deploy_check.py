"""
deploy_check.py - 部署前自检脚本
确保所有依赖、入口、路径在 Streamlit Cloud 上能正常跑
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

errors = []
warnings = []


def check(name, cond, msg):
    if cond:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name}: {msg}")
        errors.append(f"{name}: {msg}")


def warn(name, cond, msg):
    if not cond:
        print(f"  [WARN] {name}: {msg}")
        warnings.append(f"{name}: {msg}")


print("\n========== 部署前自检 ==========\n")

# 1. 入口文件
print("[1/6] 检查入口文件")
check("Home.py 存在", (ROOT / "Home.py").exists(), "缺少主入口")
check("requirements.txt 存在", (ROOT / "requirements.txt").exists(), "缺少依赖文件")

# 2. 依赖
print("\n[2/6] 检查 Python 依赖")
required = ["pandas", "numpy", "streamlit", "plotly", "pydantic", "yaml", "scipy"]
for pkg in required:
    try:
        __import__(pkg)
        print(f"  [PASS] {pkg} 可导入")
    except ImportError:
        errors.append(f"缺少依赖: {pkg}")
        print(f"  [FAIL] {pkg} 缺失")

# 可选
optional = ["akshare", "tushare", "reportlab"]
for pkg in optional:
    try:
        __import__(pkg)
        print(f"  [OK]   {pkg} 已安装（可选）")
    except ImportError:
        print(f"  [SKIP] {pkg} 未安装（可选，按需启用）")

# 3. 源码模块
print("\n[3/6] 检查源码模块")
src_modules = [
    "config", "data_loader", "backtest_engine",
    "strategies", "factors", "performance",
    "realism", "live_signal", "paper_trader",
]
for m in src_modules:
    try:
        __import__(m)
        print(f"  [PASS] src/{m}.py 可导入")
    except Exception as e:
        errors.append(f"src/{m}.py 导入失败: {e}")
        print(f"  [FAIL] src/{m}.py: {e}")

# 4. Pages
print("\n[4/6] 检查 Streamlit 页面")
pages_dir = ROOT / "pages"
pages = list(pages_dir.glob("*.py"))
check("pages/ 目录存在", pages_dir.exists(), "缺少页面目录")
print(f"  [INFO] 共 {len(pages)} 个页面：")
for p in sorted(pages):
    # 用 py_compile 检查语法
    import py_compile
    try:
        py_compile.compile(str(p), doraise=True)
        print(f"    [PASS] {p.name}")
    except py_compile.PyCompileError as e:
        errors.append(f"{p.name} 语法错误: {e}")
        print(f"    [FAIL] {p.name}: {e}")

# 5. Streamlit 配置
print("\n[5/6] 检查 Streamlit 配置")
config_path = ROOT / ".streamlit" / "config.toml"
check(".streamlit/config.toml 存在", config_path.exists(), "缺少 Streamlit 配置")

# 6. 关键功能 smoke test
print("\n[6/6] 关键功能 smoke test")
try:
    from config import BacktestConfig
    from backtest_engine import BacktestEngine
    from realism import RealismConfig
    from data_loader import DataLoader
    from strategies import create_strategy

    loader = DataLoader(data_source="simulated")
    data = loader.load_data("TEST", "2024-01-01", "2024-06-30")
    strategy = create_strategy("双均线策略")
    signals = strategy.generate_signals(data)
    cfg = BacktestConfig(initial_capital=100_000)
    engine = BacktestEngine(cfg, realism_config=RealismConfig(enable=True))
    result = engine.run(data, signals)
    final_eq = result.equity_curve.iloc[-1]
    print(f"  [PASS] 端到端回测：最终净值 {final_eq:,.2f}")
except Exception as e:
    errors.append(f"端到端回测失败: {e}")
    print(f"  [FAIL] 回测 smoke test: {e}")

# 总结
print("\n" + "=" * 40)
if errors:
    print(f"[!] {len(errors)} 项错误，无法部署：")
    for e in errors:
        print(f"    - {e}")
    sys.exit(1)
elif warnings:
    print(f"[~] {len(warnings)} 项警告，但可部署：")
    for w in warnings:
        print(f"    - {w}")

print("\n所有检查通过，可以部署到 Streamlit Community Cloud")
print("\n部署步骤：")
print("  1. https://share.streamlit.io/ 用 GitHub 登录")
print("  2. New app → 选 aznikline/Wanyan-quant → 主文件 Home.py")
print("  3. Deploy（约 2-3 分钟）")
