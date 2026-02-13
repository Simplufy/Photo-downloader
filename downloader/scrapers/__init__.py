"""Scraper modules for various image sources."""

from .netcarshow import NetCarShowScraper
from .wikimedia import WikimediaScraper
from .motor1 import Motor1Scraper
from .manufacturer import ManufacturerScraper

__all__ = [
    "NetCarShowScraper",
    "WikimediaScraper",
    "Motor1Scraper",
    "ManufacturerScraper",
]
