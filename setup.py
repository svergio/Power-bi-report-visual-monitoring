from pathlib import Path
from setuptools import find_packages, setup


README = Path("README.md").read_text(encoding="utf-8")


setup(
    name="powerbi-report-visual-monitor",
    version="0.1.0",
    description="Visual monitoring for Power BI Report Server reports",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Power BI Report Monitor Contributors",
    license="MIT",
    url="https://github.com/example/powerbi-report-visual-monitor",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "python-dotenv>=1.0.0",
        "psycopg[binary]>=3.2.0",
        "psycopg_pool>=3.2.0",
        "selenium>=4.20.0",
        "webdriver-manager>=4.0.1",
        "Pillow>=10.3.0",
        "ImageHash>=4.3.1",
        "numpy>=1.26.0",
        "python-json-logger>=2.0.7",
        "pydantic>=2.8.0",
        "pydantic-settings>=2.3.4",
    ],
    extras_require={
        "dev": [
            "pytest>=8.2.0",
            "flake8>=7.1.0",
            "mypy>=1.10.0",
            "bandit>=1.7.9",
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Monitoring",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    keywords=["powerbi", "monitoring", "visual-regression", "quadtree", "xor-delta"],
    python_requires=">=3.10",
    entry_points={"console_scripts": ["pbimonitor=pbimonitor.main:main"]},
)
