#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""setup.py - 模块化量化平台安装配置"""

from setuptools import setup, find_packages
import os
import re

# 读取 README.md 作为长描述
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取 __init__.py 获取版本号
with open("src/modular_quant/__init__.py", "r", encoding="utf-8") as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    version = version_match.group(1) if version_match else "1.0.0"

# 读取依赖
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="modular-quant",
    version=version,
    author="gszolo80",
    author_email="7004830@qq.com",
    description="模块化量化平台 - 数据是基础，做成模块化，功能只挂接",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gszolo80/modular-quant",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "full": [
            "akshare>=1.12.0",
            "ta-lib>=0.4.0",
            "plotly>=5.15.0",
            "dash>=2.14.0",
            "fastapi>=0.104.0",
            "uvicorn>=0.24.0",
            "sqlalchemy>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mq=modular_quant.cli:main",
            "modular-quant=modular_quant.cli:main",
        ],
    },
    project_urls={
        "Homepage": "https://github.com/gszolo80/modular-quant",
        "Repository": "https://github.com/gszolo80/modular-quant",
        "Documentation": "https://github.com/gszolo80/modular-quant/blob/main/README.md",
        "Issues": "https://github.com/gszolo80/modular-quant/issues",
    },
    keywords=[
        "quantitative",
        "backtesting",
        "stock",
        "trading",
        "finance",
        "investment",
        "algorithmic-trading",
        "data-analysis",
    ],
)