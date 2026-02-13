"""Scraper for motor1.com photo galleries."""

import logging
import re
from urllib.parse import quote

from ..scraper_base import BaseScraper, ImageResult

logger = logging.getLogger(__name__)


class Motor1Scraper(BaseScraper):
    """
    Scrapes motor1.com for car photos.

    Motor1 has extensive photo galleries organized by make/model.
    URL pattern: https://www.motor1.com/photos/{slug}/
    """

    @property
    def name(self):
        return "Motor1"

    @property
    def base_url(self):
        return "https://www.motor1.com"

    def search_images(self, make, model, year, max_results=20):
        results = []

        # Try searching via their photo gallery section
        search_urls = self._build_search_urls(make, model, year)

        for url in search_urls:
            if len(results) >= max_results:
                break

            logger.info(f"[{self.name}] Trying: {url}")
            soup = self._get_soup(url)
            if soup is None:
                continue

            # Find gallery links on the search/listing page
            gallery_links = self._find_gallery_links(soup, url, make, model, year)

            for gallery_url in gallery_links:
                if len(results) >= max_results:
                    break

                gallery_results = self._scrape_gallery(gallery_url, make, model, year)
                results.extend(gallery_results)

            # Also extract any direct images from the page
            page_results = self._extract_images_from_page(soup, url, make, model, year)
            results.extend(page_results)

        # Deduplicate
        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        return unique[:max_results]

    def _build_search_urls(self, make, model, year):
        """Build search URLs for Motor1."""
        make_slug = make.lower().replace(" ", "-").replace(".", "")
        model_slug = model.lower().replace(" ", "-").replace(".", "")

        return [
            f"{self.base_url}/photos/?q={quote(f'{year} {make} {model}')}",
            f"{self.base_url}/photo/{year}-{make_slug}-{model_slug}/",
            f"{self.base_url}/{make_slug}/{model_slug}/photos/",
        ]

    def _find_gallery_links(self, soup, page_url, make, model, year):
        """Find links to photo gallery pages."""
        gallery_links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True).lower()
            full_url = self._resolve_url(href, page_url)

            # Look for gallery/photo links that mention our vehicle
            if "/photo" in href.lower() or "/gallery" in href.lower():
                make_lower = make.lower()
                model_lower = model.lower()
                str_year = str(year)

                # Check if the link or text mentions our vehicle
                combined = f"{href} {text}".lower()
                if (make_lower in combined or model_lower in combined) and str_year in combined:
                    gallery_links.append(full_url)

        return gallery_links[:5]  # Limit to avoid too many requests

    def _scrape_gallery(self, gallery_url, make, model, year):
        """Scrape a photo gallery page for images."""
        results = []

        soup = self._get_soup(gallery_url)
        if soup is None:
            return results

        # Motor1 galleries have images in various container patterns
        # Look for large image containers
        for img_tag in soup.find_all("img", src=True):
            src = img_tag["src"]

            # Try to get the highest resolution version
            high_res = (
                img_tag.get("data-src")
                or img_tag.get("data-original")
                or img_tag.get("data-lazy-src")
                or self._best_from_srcset(img_tag.get("srcset", ""))
                or src
            )

            full_url = self._resolve_url(high_res, gallery_url)

            if not self._is_image_url(full_url):
                continue

            alt = img_tag.get("alt", "")

            # Skip non-car images (ads, logos, author photos)
            if any(skip in alt.lower() for skip in
                   ("logo", "icon", "avatar", "author", "banner", "ad ", "advertisement")):
                continue

            results.append(ImageResult(
                url=full_url,
                make=make,
                model=model,
                year=year,
                alt_text=alt,
                caption=self._find_caption(img_tag),
                source_page=gallery_url,
            ))

        return results
