"""Base scraper class with common HTTP and parsing functionality."""

import logging
import time
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ImageResult:
    """Represents a found image with its metadata."""

    def __init__(self, url, make=None, model=None, year=None, alt_text="",
                 caption="", page_context="", source_page="", filename=""):
        self.url = url
        self.make = make
        self.model = model
        self.year = year
        self.alt_text = alt_text
        self.caption = caption
        self.page_context = page_context
        self.source_page = source_page
        self.filename = filename or self._filename_from_url(url)

    @staticmethod
    def _filename_from_url(url):
        parsed = urlparse(url)
        path = parsed.path
        return path.split('/')[-1] if '/' in path else path

    def __repr__(self):
        return (f"ImageResult(make={self.make!r}, model={self.model!r}, "
                f"year={self.year}, url={self.url[:60]}...)")


class BaseScraper(ABC):
    """
    Abstract base class for all image scrapers.

    Provides common HTTP session management, rate limiting, and retry logic.
    Subclasses must implement search_images().
    """

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        })
        self._last_request_time = 0

    @property
    @abstractmethod
    def name(self):
        """Human-readable name of the scraper."""
        pass

    @property
    @abstractmethod
    def base_url(self):
        """Base URL of the site being scraped."""
        pass

    @abstractmethod
    def search_images(self, make, model, year, max_results=20):
        """
        Search for images of a specific vehicle.

        Args:
            make: Brand name (e.g. "Porsche")
            model: Model name (e.g. "911")
            year: Model year (e.g. 2024)
            max_results: Maximum number of images to return

        Returns:
            list of ImageResult objects
        """
        pass

    def _rate_limit(self):
        """Enforce delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.request_delay:
            time.sleep(self.config.request_delay - elapsed)
        self._last_request_time = time.time()

    def _get(self, url, **kwargs):
        """Make a rate-limited GET request with retries."""
        self._rate_limit()

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=self.config.request_timeout,
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except requests.HTTPError as e:
                if e.response is not None and 400 <= e.response.status_code < 500:
                    logger.debug(
                        f"[{self.name}] {e.response.status_code} for: {url}"
                    )
                    return None
                logger.warning(
                    f"[{self.name}] Request failed (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {url} - {e}"
                )
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
            except requests.RequestException as e:
                logger.warning(
                    f"[{self.name}] Request failed (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {url} - {e}"
                )
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))

        logger.error(f"[{self.name}] All retries exhausted for: {url}")
        return None

    def _get_soup(self, url, **kwargs):
        """Fetch a URL and parse the HTML into BeautifulSoup."""
        response = self._get(url, **kwargs)
        if response is None:
            return None
        return BeautifulSoup(response.text, "lxml")

    def _resolve_url(self, url, base=None):
        """Resolve a relative URL to absolute."""
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(base or self.base_url, url)

    def _is_image_url(self, url):
        """Check if a URL likely points to an image."""
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')
        parsed = urlparse(url)
        path = parsed.path.lower()
        return any(path.endswith(ext) for ext in image_extensions)

    def _extract_images_from_page(self, soup, page_url, make, model, year):
        """
        Extract image results from a BeautifulSoup page.

        Looks for <img> tags and <a> tags linking to images,
        preferring larger/higher-resolution versions.
        """
        results = []
        if soup is None:
            return results

        seen_urls = set()

        # Look for linked images first (often higher resolution)
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = self._resolve_url(href, page_url)

            if self._is_image_url(full_url) and full_url not in seen_urls:
                seen_urls.add(full_url)
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

        # Then look for standalone img tags
        for img_tag in soup.find_all("img", src=True):
            src = img_tag["src"]

            # Try to get higher-res version from srcset or data attributes
            high_res = (
                img_tag.get("data-src")
                or img_tag.get("data-original")
                or img_tag.get("data-full")
                or img_tag.get("data-large")
                or self._best_from_srcset(img_tag.get("srcset", ""))
                or src
            )

            full_url = self._resolve_url(high_res, page_url)

            if full_url not in seen_urls and self._is_image_url(full_url):
                seen_urls.add(full_url)
                alt = img_tag.get("alt", "")
                caption = self._find_caption(img_tag)

                results.append(ImageResult(
                    url=full_url,
                    make=make,
                    model=model,
                    year=year,
                    alt_text=alt,
                    caption=caption,
                    source_page=page_url,
                ))

        return results

    @staticmethod
    def _find_caption(element):
        """Try to find a caption near an image element."""
        # Check for figcaption in parent figure
        parent = element.find_parent("figure")
        if parent:
            figcaption = parent.find("figcaption")
            if figcaption:
                return figcaption.get_text(strip=True)

        # Check for title attribute
        title = element.get("title", "")
        if title:
            return title

        # Check sibling elements for caption-like classes
        for sibling in element.find_next_siblings(limit=2):
            classes = sibling.get("class", [])
            class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
            if any(kw in class_str.lower() for kw in ("caption", "desc", "title")):
                return sibling.get_text(strip=True)

        return ""

    @staticmethod
    def _best_from_srcset(srcset):
        """Extract the highest-resolution URL from a srcset attribute."""
        if not srcset:
            return None

        candidates = []
        for entry in srcset.split(","):
            parts = entry.strip().split()
            if len(parts) >= 1:
                url = parts[0]
                width = 0
                if len(parts) >= 2:
                    descriptor = parts[1]
                    if descriptor.endswith("w"):
                        try:
                            width = int(descriptor[:-1])
                        except ValueError:
                            pass
                    elif descriptor.endswith("x"):
                        try:
                            width = int(float(descriptor[:-1]) * 1000)
                        except ValueError:
                            pass
                candidates.append((url, width))

        if candidates:
            candidates.sort(key=lambda c: c[1], reverse=True)
            return candidates[0][0]
        return None

    def download_image(self, url):
        """
        Download an image and return the raw bytes.

        Returns:
            bytes or None if download fails
        """
        self._rate_limit()

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=self.config.request_timeout,
                    stream=True,
                )
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if "image" not in content_type and "octet-stream" not in content_type:
                    logger.warning(f"[{self.name}] Non-image content type: {content_type} for {url}")
                    return None

                data = response.content

                # Basic size check (skip tiny images like icons)
                if len(data) < 10000:  # Less than ~10KB is likely a thumbnail/icon
                    logger.debug(f"[{self.name}] Skipping tiny image ({len(data)} bytes): {url}")
                    return None

                return data

            except requests.HTTPError as e:
                if e.response is not None and 400 <= e.response.status_code < 500:
                    logger.debug(
                        f"[{self.name}] {e.response.status_code} downloading: {url}"
                    )
                    return None
                logger.warning(
                    f"[{self.name}] Image download failed (attempt {attempt + 1}): {url} - {e}"
                )
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
            except requests.RequestException as e:
                logger.warning(
                    f"[{self.name}] Image download failed (attempt {attempt + 1}): {url} - {e}"
                )
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))

        return None
