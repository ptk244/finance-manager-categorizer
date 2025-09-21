"""
Setup configuration for Finance Manager Categorizer
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="finance-manager-categorizer",
    version="1.0.0",
    author="Finance Manager Team",
    author_email="team@financemanager.ai",
    description="AI-powered transaction categorization using Agno 2.0.5 and Gemini models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/finance-manager-categorizer",
    project_urls={
        "Bug Tracker": "https://github.com/your-org/finance-manager-categorizer/issues",
        "Documentation": "https://finance-manager-docs.example.com",
        "Source Code": "https://github.com/your-org/finance-manager-categorizer",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.24.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.24.0",
            "pytest-cov>=4.0.0",
            "httpx>=0.28.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings>=0.20.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "finance-manager=app.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app": [
            "*.py",
            "*/*.py",
        ],
        "tests": [
            "sample_data/*",
        ],
    },
    zip_safe=False,
    keywords=[
        "finance",
        "ai",
        "machine-learning",
        "transaction-categorization",
        "agno",
        "gemini",
        "fastapi",
        "fintech",
        "banking",
        "personal-finance",
        "business-finance",
        "financial-insights",
        "automated-categorization",
        "indian-banking"
    ],
)