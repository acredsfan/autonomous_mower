"""
Setup script for autonomous mower system.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')

setup(
    name="autonomous-mower",
    version="0.1.0",
    description="A safety-first autonomous lawn mower system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Autonomous Mower Project",
    python_requires=">=3.9",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0",
        ],
        "hardware": [
            "pyserial>=3.5",
            "smbus2>=0.4.2",
            "digitalio>=3.3.0",
            "adafruit-circuitpython-motor>=3.4.0",
            "picamera2>=0.3.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "mower=mower.tools.cli:main",
            "mower-test=mower.tools.test_runner:main",
            "mower-setup=mower.tools.setup:main",
            "mower-status=mower.tools.status:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Home Automation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="autonomous mower robotics safety hardware",
    project_urls={
        "Documentation": "https://github.com/acredsfan/autonomous_mower/docs",
        "Source": "https://github.com/acredsfan/autonomous_mower",
        "Tracker": "https://github.com/acredsfan/autonomous_mower/issues",
    },
)
