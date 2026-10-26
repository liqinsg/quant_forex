from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="forex-oanda-bot",
    version="0.6.8",
    description="AI-powered Forex Trading Bot for OANDA — LightGBM + TCN + GARCH",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    packages=[
        "config",
        "execution",
        "features",
        "models",
        "validation",
        "data",
    ],
    install_requires=[
        "pandas==2.2.3",
        "numpy==1.26.4",
        "pyyaml==6.0.2",
        "python-dotenv==1.0.1",
        "pytz==2026.1",
        "oandapyV20==0.7.0",
        "arch==7.2.0",
        "TA-Lib==0.8.2",
        "scipy==1.14.1",
        "scikit-learn==1.5.2",
        "lightgbm==4.5.0",
        "xgboost==2.0.3",
        "torch==2.5.1",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "forex-bot=scripts.run_bot:main",
        ],
    },
)
