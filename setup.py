from setuptools import setup, find_packages

setup(
    name="multi-asset-factor-dashboard",
    version="0.1.0",
    description="Multi Asset and Factor Trend Dashboard for quantitative analysis",
    author="Quantitative Research",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.10.0",
        "pyarrow>=12.0.0",
        "fastparquet>=2023.0.0",
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
        ],
        "viz": [
            "plotly>=5.14.0",
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
        ],
    },
)
