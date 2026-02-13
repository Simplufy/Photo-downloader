"""Configuration loader and manager."""

import os
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class Config:
    """Loads and provides access to configuration settings."""

    def __init__(self, config_path=None):
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r") as f:
            self._data = yaml.safe_load(f)

    @property
    def download_dir(self):
        return Path(self._data.get("download_dir", "./downloads"))

    @property
    def images_per_combination(self):
        return self._data.get("images_per_combination", 20)

    @property
    def min_width(self):
        return self._data.get("min_width", 800)

    @property
    def min_height(self):
        return self._data.get("min_height", 600)

    @property
    def max_concurrent(self):
        return self._data.get("max_concurrent", 3)

    @property
    def request_delay(self):
        return self._data.get("request_delay", 1.5)

    @property
    def request_timeout(self):
        return self._data.get("request_timeout", 30)

    @property
    def user_agent(self):
        return self._data.get("user_agent", "Mozilla/5.0")

    @property
    def max_retries(self):
        return self._data.get("max_retries", 3)

    @property
    def retry_delay(self):
        return self._data.get("retry_delay", 2)

    @property
    def use_selenium(self):
        return self._data.get("use_selenium", False)

    @property
    def sources(self):
        return self._data.get("sources", [])

    @property
    def brands(self):
        """Return brands with all model names coerced to strings."""
        raw = self._data.get("brands", {})
        return {brand: [str(m) for m in models] for brand, models in raw.items()}

    @property
    def years(self):
        return [int(y) for y in self._data.get("years", [])]

    def get_enabled_sources(self):
        """Return sources that are enabled, sorted by priority."""
        return sorted(
            [s for s in self.sources if s.get("enabled", True)],
            key=lambda s: s.get("priority", 999),
        )

    def get_brand_models(self, brand=None):
        """Return brand->models mapping, optionally filtered to one brand."""
        if brand:
            models = self.brands.get(brand, [])
            return {brand: models} if models else {}
        return dict(self.brands)
