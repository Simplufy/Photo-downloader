"""Scraper for Wikimedia Commons - uses the MediaWiki API."""

import logging
from urllib.parse import quote

from ..scraper_base import BaseScraper, ImageResult

logger = logging.getLogger(__name__)


class WikimediaScraper(BaseScraper):
    """
    Scrapes Wikimedia Commons using the MediaWiki API.

    Uses the API to search for car images, which is more reliable and
    respectful than scraping HTML pages.
    """

    API_URL = "https://commons.wikimedia.org/w/api.php"

    @property
    def name(self):
        return "Wikimedia Commons"

    @property
    def base_url(self):
        return "https://commons.wikimedia.org"

    def search_images(self, make, model, year, max_results=20):
        results = []

        # Try multiple search queries
        queries = self._build_queries(make, model, year)

        for query in queries:
            if len(results) >= max_results:
                break

            found = self._api_search(query, make, model, year, max_results - len(results))
            results.extend(found)

        # Deduplicate by URL
        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        return unique[:max_results]

    def _build_queries(self, make, model, year):
        """Build search queries for the Wikimedia API."""
        queries = [
            f"{make} {model} {year}",
            f"{year} {make} {model}",
            f"{make} {model} {year} car",
        ]

        # Add exterior/interior specific searches
        queries.extend([
            f"{make} {model} {year} exterior",
            f"{make} {model} {year} interior",
        ])

        return queries

    def _api_search(self, query, make, model, year, limit=20):
        """Search Wikimedia Commons API for images."""
        results = []

        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": "6",  # File namespace
            "gsrlimit": min(limit * 2, 50),  # Request extra to account for filtering
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": "1920",  # Request reasonably large thumbnails
        }

        response = self._get(self.API_URL, params=params)
        if response is None:
            return results

        try:
            data = response.json()
        except (ValueError, AttributeError):
            logger.warning(f"[{self.name}] Failed to parse API response")
            return results

        pages = data.get("query", {}).get("pages", {})

        for page_id, page in pages.items():
            if len(results) >= limit:
                break

            imageinfo_list = page.get("imageinfo", [])
            if not imageinfo_list:
                continue

            info = imageinfo_list[0]

            # Filter by MIME type
            mime = info.get("mime", "")
            if not mime.startswith("image/"):
                continue

            # Filter by size
            width = info.get("width", 0)
            height = info.get("height", 0)
            if width < self.config.min_width or height < self.config.min_height:
                continue

            # Get the best URL (prefer thumburl for bandwidth, fall back to full url)
            url = info.get("thumburl") or info.get("url", "")
            if not url:
                continue

            # Extract metadata
            extmetadata = info.get("extmetadata", {})
            description = extmetadata.get("ImageDescription", {}).get("value", "")
            categories = extmetadata.get("Categories", {}).get("value", "")

            results.append(ImageResult(
                url=url,
                make=make,
                model=model,
                year=year,
                alt_text=page.get("title", ""),
                caption=description,
                page_context=categories,
                source_page=f"https://commons.wikimedia.org/wiki/{quote(page.get('title', ''))}",
            ))

        return results

    def _search_by_category(self, make, model, year, limit=20):
        """Search by Wikimedia category, which is often more precise."""
        results = []

        # Try common category patterns
        categories = [
            f"{make} {model}",
            f"{year} {make} {model}",
            f"{make} {model} ({year})",
        ]

        for cat_name in categories:
            if len(results) >= limit:
                break

            params = {
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": f"Category:{cat_name}",
                "cmtype": "file",
                "cmlimit": min(limit, 50),
                "cmprop": "title",
            }

            response = self._get(self.API_URL, params=params)
            if response is None:
                continue

            try:
                data = response.json()
            except (ValueError, AttributeError):
                continue

            members = data.get("query", {}).get("categorymembers", [])

            for member in members:
                if len(results) >= limit:
                    break

                title = member.get("title", "")
                if not title:
                    continue

                # Get image info for this file
                file_results = self._get_file_info(title, make, model, year)
                results.extend(file_results)

        return results

    def _get_file_info(self, title, make, model, year):
        """Get detailed info for a specific file."""
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": "1920",
        }

        response = self._get(self.API_URL, params=params)
        if response is None:
            return []

        try:
            data = response.json()
        except (ValueError, AttributeError):
            return []

        results = []
        pages = data.get("query", {}).get("pages", {})

        for page_id, page in pages.items():
            imageinfo_list = page.get("imageinfo", [])
            if not imageinfo_list:
                continue

            info = imageinfo_list[0]
            mime = info.get("mime", "")
            if not mime.startswith("image/"):
                continue

            width = info.get("width", 0)
            height = info.get("height", 0)
            if width < self.config.min_width or height < self.config.min_height:
                continue

            url = info.get("thumburl") or info.get("url", "")
            if url:
                results.append(ImageResult(
                    url=url,
                    make=make,
                    model=model,
                    year=year,
                    alt_text=title,
                    source_page=f"https://commons.wikimedia.org/wiki/{quote(title)}",
                ))

        return results
