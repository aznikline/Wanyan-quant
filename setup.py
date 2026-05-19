#!/usr/bin/env python3
"""
Rock Quant - 顽岩量化 Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="rockquant",
    version="2.6.0",
    author="Rock Quant Team",
    author_email="dev@rockquant.io",
    description="AI驱动的量价策略回测与分析工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aznikline/Wanyan-quant",
    packages=find_packages(),
    package_data={
        "": ["*.md", "*.txt"],
    },
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "streamlit>=1.20.0",
        "plotly>=5.0.0",
        "reportlab>=3.6.0",
        "akshare>=1.8.0",
        "tushare>=1.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rockquant=rockquant.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="quant backtest trading strategy ai analysis finance stock",
    python_requires=">=3.8",
    platforms="any",
    zip_safe=False,
)
