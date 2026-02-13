"""Setup script for Photo Downloader."""

from setuptools import setup, find_packages

setup(
    name="photo-downloader",
    version="1.0.0",
    description="Download and categorize luxury car images from media sites",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "Pillow>=10.0.0",
        "PyYAML>=6.0",
        "click>=8.1.0",
        "tqdm>=4.65.0",
    ],
    extras_require={
        "selenium": [
            "selenium>=4.15.0",
            "webdriver-manager>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "photo-downloader=downloader.cli:main",
        ],
    },
)
