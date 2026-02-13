"""
Generic scraper for manufacturer media/press websites.

Many manufacturer media sites share common patterns:
- Press release pages with image galleries
- Media library sections with searchable images
- Model-specific landing pages

This scraper provides a generic approach that works across many
manufacturer sites, with brand-specific URL patterns.
"""

import logging
import re
from urllib.parse import quote, urljoin

from ..scraper_base import BaseScraper, ImageResult

logger = logging.getLogger(__name__)


# Brand-specific configuration for URL patterns and search behavior
BRAND_CONFIGS = {
    "audi_media": {
        "brand": "Audi",
        "base_url": "https://www.audi-mediacenter.com",
        "search_patterns": [
            "/en/search?q={make}+{model}+{year}&type=image",
            "/en/models/{model_slug}",
        ],
        "gallery_selectors": ["img.gallery-image", "img.media-image", ".image-gallery img"],
    },
    "bmw_media": {
        "brand": "BMW",
        "base_url": "https://www.press.bmwgroup.com",
        "search_patterns": [
            "/global/article/search?query={make}+{model}+{year}&mediaType=image",
            "/global/article/search?query={year}+{make}+{model}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "mercedes_media": {
        "brand": "Mercedes-Benz",
        "base_url": "https://media.mercedes-benz.com",
        "search_patterns": [
            "/search/?q={model}+{year}&type=images",
            "/vehicles/{model_slug}/",
        ],
        "gallery_selectors": [".gallery img", ".image-item img"],
    },
    "porsche_media": {
        "brand": "Porsche",
        "base_url": "https://newsroom.porsche.com",
        "search_patterns": [
            "/en/search.html?q={model}+{year}&type=images",
            "/en/models/{model_slug}.html",
        ],
        "gallery_selectors": [".gallery img", ".media-gallery img"],
    },
    "ferrari_media": {
        "brand": "Ferrari",
        "base_url": "https://media.ferrari.com",
        "search_patterns": [
            "/en/search?q={model}+{year}",
            "/en/cars/{model_slug}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "bentley_media": {
        "brand": "Bentley",
        "base_url": "https://www.bentleymedia.com",
        "search_patterns": [
            "/en/search?q={model}+{year}",
            "/en/models/{model_slug}",
        ],
        "gallery_selectors": [".gallery img", ".media-image img"],
    },
    "rolls_royce_media": {
        "brand": "Rolls-Royce",
        "base_url": "https://www.press.rolls-roycemotorcars.com",
        "search_patterns": [
            "/search?q={model}+{year}",
        ],
        "gallery_selectors": [".gallery img", ".article-image img"],
    },
    "lamborghini_media": {
        "brand": "Lamborghini",
        "base_url": "https://media.lamborghini.com",
        "search_patterns": [
            "/en/search?q={model}+{year}",
            "/en/models/{model_slug}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "mclaren_media": {
        "brand": "McLaren",
        "base_url": "https://cars.mclaren.press",
        "search_patterns": [
            "/search?q={model}+{year}",
            "/models/{model_slug}",
        ],
        "gallery_selectors": [".gallery img", ".press-image img"],
    },
    "jaguar_media": {
        "brand": "Jaguar",
        "base_url": "https://media.jaguar.com",
        "search_patterns": [
            "/search?q={model}+{year}",
            "/models/{model_slug}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "aston_martin_media": {
        "brand": "Aston Martin",
        "base_url": "https://media.astonmartin.com",
        "search_patterns": [
            "/search?q={model}+{year}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "bugatti_media": {
        "brand": "Bugatti",
        "base_url": "https://newsroom.bugatti.com",
        "search_patterns": [
            "/search?q={model}+{year}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "maserati_media": {
        "brand": "Maserati",
        "base_url": "https://media.maserati.com",
        "search_patterns": [
            "/search?q={model}+{year}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "pagani_media": {
        "brand": "Pagani",
        "base_url": "https://www.pagani.com/press",
        "search_patterns": [
            "/?s={model}+{year}",
        ],
        "gallery_selectors": [".gallery img", "img"],
    },
    "koenigsegg_media": {
        "brand": "Koenigsegg",
        "base_url": "https://www.koenigsegg.com/media",
        "search_patterns": [
            "?q={model}",
        ],
        "gallery_selectors": [".gallery img", "img"],
    },
    "lotus_media": {
        "brand": "Lotus",
        "base_url": "https://media.lotuscars.com",
        "search_patterns": [
            "/search?q={model}+{year}",
        ],
        "gallery_selectors": [".gallery img", ".media-item img"],
    },
    "rimac_media": {
        "brand": "Rimac",
        "base_url": "https://rimac-automobili.com/media",
        "search_patterns": [
            "?q={model}",
        ],
        "gallery_selectors": [".gallery img", "img"],
    },
    "pininfarina_media": {
        "brand": "Pininfarina",
        "base_url": "https://automobili-pininfarina.com/media-hub",
        "search_patterns": [
            "?q={model}",
        ],
        "gallery_selectors": [".gallery img", "img"],
    },
    "gordon_murray_media": {
        "brand": "Gordon Murray",
        "base_url": "https://gordonmurrayautomotive.com/media-centre",
        "search_patterns": [
            "?q={model}",
        ],
        "gallery_selectors": [".gallery img", "img"],
    },
}


class ManufacturerScraper(BaseScraper):
    """
    Generic scraper for manufacturer media/press websites.

    Configurable per-brand using BRAND_CONFIGS. Attempts multiple
    search and gallery URL patterns for each manufacturer.
    """

    def __init__(self, config, source_name):
        super().__init__(config)
        self._source_name = source_name
        self._brand_config = BRAND_CONFIGS.get(source_name, {})

        if not self._brand_config:
            logger.warning(f"No brand config found for source: {source_name}")

    @property
    def name(self):
        brand = self._brand_config.get("brand", self._source_name)
        return f"{brand} Media"

    @property
    def base_url(self):
        return self._brand_config.get("base_url", "")

    def search_images(self, make, model, year, max_results=20):
        if not self._brand_config:
            return []

        results = []
        model_slug = model.lower().replace(" ", "-").replace(".", "")

        # Try each search pattern
        for pattern in self._brand_config.get("search_patterns", []):
            if len(results) >= max_results:
                break

            url = self.base_url + pattern.format(
                make=quote(make),
                model=quote(model),
                year=year,
                model_slug=model_slug,
            )

            logger.info(f"[{self.name}] Trying: {url}")
            soup = self._get_soup(url)
            if soup is None:
                continue

            # Extract images using configured selectors
            page_results = self._extract_with_selectors(
                soup, url, make, model, year
            )
            results.extend(page_results)

            # Find and follow gallery/detail page links
            detail_links = self._find_detail_links(soup, url, make, model, year)
            for detail_url in detail_links[:5]:
                if len(results) >= max_results:
                    break

                detail_soup = self._get_soup(detail_url)
                if detail_soup:
                    detail_results = self._extract_with_selectors(
                        detail_soup, detail_url, make, model, year
                    )
                    results.extend(detail_results)

        # Fallback: generic image extraction
        if not results:
            results = self._fallback_search(make, model, year, max_results)

        # Deduplicate
        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        return unique[:max_results]

    def _extract_with_selectors(self, soup, page_url, make, model, year):
        """Extract images using the configured CSS selectors."""
        results = []
        selectors = self._brand_config.get("gallery_selectors", [])

        for selector in selectors:
            try:
                elements = soup.select(selector)
            except Exception:
                continue

            for element in elements:
                if element.name == "img":
                    src = (
                        element.get("data-src")
                        or element.get("data-original")
                        or element.get("data-full")
                        or self._best_from_srcset(element.get("srcset", ""))
                        or element.get("src", "")
                    )
                else:
                    img = element.find("img")
                    if not img:
                        continue
                    src = img.get("data-src") or img.get("src", "")

                if not src:
                    continue

                full_url = self._resolve_url(src, page_url)
                if not self._is_image_url(full_url):
                    continue

                alt = element.get("alt", "") if element.name == "img" else ""
                caption = self._find_caption(element)

                results.append(ImageResult(
                    url=full_url,
                    make=make,
                    model=model,
                    year=year,
                    alt_text=alt,
                    caption=caption,
                    source_page=page_url,
                ))

        # Also do generic extraction
        generic = self._extract_images_from_page(soup, page_url, make, model, year)
        results.extend(generic)

        return results

    def _find_detail_links(self, soup, page_url, make, model, year):
        """Find links to detail/gallery pages from a search results page."""
        links = []
        make_lower = make.lower()
        model_lower = model.lower()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True).lower()
            full_url = self._resolve_url(href, page_url)

            # Skip if same as current page
            if full_url == page_url:
                continue

            # Skip external links
            if self.base_url and not full_url.startswith(self.base_url):
                continue

            # Look for links that mention the vehicle
            combined = f"{href} {text}".lower()
            if model_lower in combined or make_lower in combined:
                links.append(full_url)

        return links

    def _fallback_search(self, make, model, year, max_results):
        """Fallback: just scrape the base URL for any relevant images."""
        results = []

        soup = self._get_soup(self.base_url)
        if soup is None:
            return results

        all_images = self._extract_images_from_page(
            soup, self.base_url, make, model, year
        )

        # Filter to only images that seem related
        model_lower = model.lower()
        make_lower = make.lower()

        for img in all_images:
            combined = f"{img.alt_text} {img.caption} {img.filename}".lower()
            if model_lower in combined or make_lower in combined:
                results.append(img)

        return results[:max_results]
