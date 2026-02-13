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
    def category_targets(self):
        """Per-category image targets. Defaults to 12 ext / 6 int / 1 trunk / 1 engine."""
        return self._data.get("category_targets", {
            "exterior": 12,
            "interior": 6,
            "trunk": 1,
            "engine": 1,
        })

    @property
    def images_per_combination(self):
        return sum(self.category_targets.values())

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
        """Return brands as {brand: {model: [years]}} with year ranges expanded."""
        raw = self._data.get("brands", {})
        result = {}
        for brand, models in raw.items():
            result[brand] = {}
            for model, year_range in models.items():
                model_name = str(model)
                if isinstance(year_range, str) and "-" in year_range:
                    start, end = year_range.split("-")
                    years = list(range(int(start), int(end) + 1))
                elif isinstance(year_range, list):
                    years = [int(y) for y in year_range]
                else:
                    years = []
                result[brand][model_name] = years
        return result

    def get_enabled_sources(self):
        """Return sources that are enabled, sorted by priority."""
        return sorted(
            [s for s in self.sources if s.get("enabled", True)],
            key=lambda s: s.get("priority", 999),
        )

    def get_brand_models(self, brand=None):
        """Return brand->{model: [years]} mapping, optionally filtered to one brand."""
        if brand:
            models = self.brands.get(brand, {})
            return {brand: models} if models else {}
        return dict(self.brands)
