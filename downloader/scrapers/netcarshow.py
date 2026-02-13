"""Scraper for netcarshow.com - structured car image gallery."""

import logging
import re
from urllib.parse import quote

from ..scraper_base import BaseScraper, ImageResult

logger = logging.getLogger(__name__)


class NetCarShowScraper(BaseScraper):
    """
    Scrapes netcarshow.com for car images.

    NetCarShow has a well-structured gallery with images organized by
    make/model/year, making it one of the most reliable sources.

    URL pattern: https://www.netcarshow.com/{make}/{year}-{model}/
    """

    @property
    def name(self):
        return "NetCarShow"

    @property
    def base_url(self):
        return "https://www.netcarshow.com"

    def search_images(self, make, model, year, max_results=20):
        results = []

        # NetCarShow URL patterns to try
        urls_to_try = self._build_search_urls(make, model, year)

        for url in urls_to_try:
            logger.info(f"[{self.name}] Trying: {url}")
            soup = self._get_soup(url)
            if soup is None:
                continue

            # Look for the gallery page
            page_results = self._parse_gallery_page(soup, url, make, model, year)
            results.extend(page_results)

            if len(results) >= max_results:
                break

            # Also look for sub-gallery links (interior, exterior pages)
            sub_links = self._find_sub_galleries(soup, url)
            for sub_url, sub_context in sub_links:
                if len(results) >= max_results:
                    break
                sub_soup = self._get_soup(sub_url)
                if sub_soup:
                    sub_results = self._parse_gallery_page(
                        sub_soup, sub_url, make, model, year
                    )
                    for r in sub_results:
                        r.page_context += f" {sub_context}"
                    results.extend(sub_results)

        return results[:max_results]

    def _build_search_urls(self, make, model, year):
        """Build potential URLs for a vehicle on NetCarShow."""
        make_slug = make.lower().replace(" ", "-").replace(".", "")
        model_slug = model.lower().replace(" ", "-").replace(".", "")

        urls = [
            # Standard pattern
            f"{self.base_url}/{make_slug}/{year}-{model_slug}/",
            # Without year prefix in model
            f"{self.base_url}/{make_slug}/{model_slug}-{year}/",
            # Hyphenated model names
            f"{self.base_url}/{make_slug}/{year}-{model_slug.replace('_', '-')}/",
        ]

        # Special handling for specific brands
        brand_map = {
            "Mercedes-Benz": "mercedes-benz",
            "Rolls-Royce": "rolls-royce",
            "Aston Martin": "aston_martin",
            "Gordon Murray": "gordon_murray",
        }
        if make in brand_map:
            alt_make = brand_map[make]
            urls.append(f"{self.base_url}/{alt_make}/{year}-{model_slug}/")

        return urls

    def _parse_gallery_page(self, soup, page_url, make, model, year):
        """Parse a NetCarShow gallery page for images."""
        results = []

        # NetCarShow typically has images in gallery divs
        # Look for high-res image links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # NetCarShow high-res images often have specific patterns
            if not self._is_image_url(href) and "1600x1200" not in href:
                continue

            full_url = self._resolve_url(href, page_url)
            img = a_tag.find("img")
            alt = img.get("alt", "") if img else ""
            caption = self._find_caption(a_tag)

            results.append(ImageResult(
                url=full_url,
                make=make,
                model=model,
                year=year,
                alt_text=alt,
                caption=caption,
                source_page=page_url,
            ))

        # Also check for img tags with large images
        for img_tag in soup.find_all("img", src=True):
            src = img_tag["src"]
            # Look for larger image versions
            high_res = (
                img_tag.get("data-src")
                or img_tag.get("data-original")
                or src
            )

            full_url = self._resolve_url(high_res, page_url)

            # Filter out tiny thumbnails, icons, logos
            width = img_tag.get("width", "")
            height = img_tag.get("height", "")
            try:
                if width and int(width) < 200:
                    continue
                if height and int(height) < 150:
                    continue
            except ValueError:
                pass

            if self._is_image_url(full_url):
                alt = img_tag.get("alt", "")
                if any(skip in alt.lower() for skip in ("logo", "icon", "banner", "ad")):
                    continue

                results.append(ImageResult(
                    url=full_url,
                    make=make,
                    model=model,
                    year=year,
                    alt_text=alt,
                    caption=self._find_caption(img_tag),
                    source_page=page_url,
                ))

        return results

    def _find_sub_galleries(self, soup, page_url):
        """Find links to sub-gallery pages (interior, exterior, etc.)."""
        sub_galleries = []

        for a_tag in soup.find_all("a", href=True):
            text = a_tag.get_text(strip=True).lower()
            href = a_tag["href"]

            if any(kw in text for kw in ("interior", "exterior", "gallery", "photos", "images")):
                full_url = self._resolve_url(href, page_url)
                if full_url != page_url:
                    sub_galleries.append((full_url, text))

        return sub_galleries
