"""
Orchestrator - coordinates scraping, downloading, categorization, and storage.

This is the main engine that ties together all components:
1. Iterates through brand/model/year combinations
2. Queries multiple scrapers for images
3. Categorizes images as interior/exterior
4. Downloads and saves to the organized folder structure
5. Tracks progress and avoids duplicates
"""

import logging
import os
import time

from tqdm import tqdm

from .categorizer import classify_image
from .file_manager import FileManager
from .scraper_base import BaseScraper
from .scrapers.netcarshow import NetCarShowScraper
from .scrapers.wikimedia import WikimediaScraper
from .scrapers.motor1 import Motor1Scraper
from .scrapers.manufacturer import ManufacturerScraper, BRAND_CONFIGS

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the full download pipeline."""

    def __init__(self, config):
        self.config = config
        self.file_manager = FileManager(config.download_dir)
        self.scrapers = self._init_scrapers()

    def _init_scrapers(self):
        """Initialize all enabled scrapers in priority order."""
        scrapers = []
        enabled_sources = self.config.get_enabled_sources()

        for source in enabled_sources:
            name = source["name"]
            try:
                scraper = self._create_scraper(name)
                if scraper:
                    scrapers.append((name, scraper))
            except Exception as e:
                logger.warning(f"Failed to initialize scraper '{name}': {e}")

        return scrapers

    def _create_scraper(self, source_name):
        """Create a scraper instance by source name."""
        if source_name == "netcarshow":
            return NetCarShowScraper(self.config)
        elif source_name == "wikimedia":
            return WikimediaScraper(self.config)
        elif source_name == "motor1":
            return Motor1Scraper(self.config)
        elif source_name in BRAND_CONFIGS:
            return ManufacturerScraper(self.config, source_name)
        else:
            logger.warning(f"Unknown source: {source_name}")
            return None

    def _get_scrapers_for_brand(self, brand, source_filter=None):
        """
        Get the appropriate scrapers for a brand.

        Returns general scrapers (netcarshow, wikimedia, motor1) plus
        the brand-specific manufacturer scraper if available.
        """
        result = []

        # Map brands to their source names
        brand_source_map = {
            "Audi": "audi_media",
            "BMW": "bmw_media",
            "Mercedes-Benz": "mercedes_media",
            "Porsche": "porsche_media",
            "Ferrari": "ferrari_media",
            "Bentley": "bentley_media",
            "Rolls-Royce": "rolls_royce_media",
            "Lamborghini": "lamborghini_media",
            "McLaren": "mclaren_media",
            "Jaguar": "jaguar_media",
            "Aston Martin": "aston_martin_media",
            "Bugatti": "bugatti_media",
            "Maserati": "maserati_media",
            "Pagani": "pagani_media",
            "Koenigsegg": "koenigsegg_media",
            "Lotus": "lotus_media",
            "Rimac": "rimac_media",
            "Pininfarina": "pininfarina_media",
            "Gordon Murray": "gordon_murray_media",
        }

        for name, scraper in self.scrapers:
            if source_filter and name != source_filter:
                continue

            # Include general-purpose scrapers for all brands
            if name in ("netcarshow", "wikimedia", "motor1"):
                result.append((name, scraper))
            # Include brand-specific scraper
            elif name == brand_source_map.get(brand):
                result.append((name, scraper))

        return result

    def run(self, brands, source_filter=None, dry_run=False):
        """
        Execute the full download pipeline.

        Args:
            brands: dict of {brand_name: {model: [years]}}
            source_filter: if set, only use this source
            dry_run: if True, find images but don't download
        """
        # Calculate total combinations for progress tracking
        total_combinations = sum(
            len(years) for models in brands.values() for years in models.values()
        )
        combination_count = 0

        print(f"\nProcessing {total_combinations} brand/model/year combinations...\n")

        category_targets = self.config.category_targets

        for brand, models in sorted(brands.items()):
            for model, model_years in sorted(models.items()):
                for year in model_years:
                    combination_count += 1

                    # Check per-category needs
                    needed_by_cat = {}
                    for cat, target in category_targets.items():
                        have = self.file_manager.get_category_count(brand, model, year, cat)
                        if have < target:
                            needed_by_cat[cat] = target - have

                    if not needed_by_cat:
                        total = self.config.images_per_combination
                        print(
                            f"[{combination_count}/{total_combinations}] "
                            f"{brand} {model} {year}: Already have {total}/{total} images, skipping"
                        )
                        continue

                    total_needed = sum(needed_by_cat.values())
                    breakdown = ", ".join(
                        f"{n} {c}" for c, n in needed_by_cat.items()
                    )
                    print(
                        f"\n[{combination_count}/{total_combinations}] "
                        f"{brand} {model} ({year}) - Need {total_needed} more ({breakdown})"
                    )

                    self._download_for_combination(
                        brand, model, year, needed_by_cat,
                        source_filter=source_filter,
                        dry_run=dry_run,
                    )

                    # Save progress after each combination
                    self.file_manager.save_manifest()

        # Final summary
        self.file_manager.save_manifest()
        self.file_manager.print_summary()

    def _download_for_combination(self, brand, model, year, needed_by_cat,
                                   source_filter=None, dry_run=False):
        """Download images for a single brand/model/year combination."""
        scrapers = self._get_scrapers_for_brand(brand, source_filter)
        downloaded_by_cat = {cat: 0 for cat in needed_by_cat}
        total_needed = sum(needed_by_cat.values())
        total_downloaded = 0

        for source_name, scraper in scrapers:
            if total_downloaded >= total_needed:
                break

            remaining = total_needed - total_downloaded
            print(f"  Searching {scraper.name}...", end=" ", flush=True)

            try:
                results = scraper.search_images(brand, model, year, max_results=remaining * 3)
                print(f"found {len(results)} candidates")
            except Exception as e:
                print(f"error: {e}")
                logger.exception(f"Scraper {source_name} failed for {brand} {model} {year}")
                continue

            if not results:
                continue

            # Process results with progress bar
            for result in tqdm(results, desc=f"  Downloading from {scraper.name}",
                              leave=False, disable=dry_run):
                if total_downloaded >= total_needed:
                    break

                # Skip already-downloaded URLs
                if self.file_manager.is_url_downloaded(result.url):
                    continue

                # Classify the image
                category, confidence = classify_image(
                    filename=result.filename,
                    alt_text=result.alt_text,
                    caption=result.caption,
                    page_context=result.page_context,
                )

                # Skip if this category is already full
                if category not in needed_by_cat or downloaded_by_cat.get(category, 0) >= needed_by_cat[category]:
                    continue

                if dry_run:
                    print(f"    [DRY RUN] Would download: {result.url[:80]}...")
                    print(f"              Category: {category} (confidence: {confidence:.2f})")
                    downloaded_by_cat[category] = downloaded_by_cat.get(category, 0) + 1
                    total_downloaded += 1
                    continue

                # Download the image
                image_data = scraper.download_image(result.url)
                if image_data is None:
                    continue

                # Check for duplicate content
                if self.file_manager.is_duplicate_content(image_data):
                    logger.debug(f"Skipping duplicate content: {result.url}")
                    continue

                # Validate image dimensions
                if not self._validate_image(image_data):
                    continue

                # Save the image
                try:
                    save_dir = self.file_manager.get_save_path(brand, model, year, category)
                    index = self.file_manager.get_next_index(brand, model, year, category)
                    filename = self.file_manager.generate_filename(
                        brand, model, year, category, result.url, index=index
                    )
                    save_path = save_dir / filename

                    with open(save_path, "wb") as f:
                        f.write(image_data)

                    # Record the download
                    self.file_manager.mark_url_downloaded(result.url, str(save_path))
                    self.file_manager.record_content_hash(image_data)
                    self.file_manager.increment_count(brand, model, year)
                    self.file_manager.increment_category_count(brand, model, year, category)
                    downloaded_by_cat[category] = downloaded_by_cat.get(category, 0) + 1
                    total_downloaded += 1

                    logger.info(
                        f"Saved: {save_path} ({category}, confidence: {confidence:.2f})"
                    )

                except OSError as e:
                    logger.error(f"Failed to save image: {e}")

        breakdown = ", ".join(
            f"{downloaded_by_cat.get(c, 0)}/{n} {c}" for c, n in needed_by_cat.items()
        )
        print(f"  -> Downloaded {total_downloaded}/{total_needed} for {brand} {model} ({year}): {breakdown}")

    def _validate_image(self, image_data):
        """Validate image dimensions meet minimum requirements."""
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            width, height = img.size

            if width < self.config.min_width or height < self.config.min_height:
                logger.debug(
                    f"Image too small: {width}x{height} "
                    f"(min: {self.config.min_width}x{self.config.min_height})"
                )
                return False

            return True

        except Exception as e:
            logger.warning(f"Could not validate image: {e}")
            # If we can't validate, allow it (might be a format PIL doesn't support)
            return True

    def show_status(self):
        """Display current download status."""
        self.file_manager.print_summary()

        print("\nConfigured targets:")
        brands = self.config.get_brand_models()
        category_targets = self.config.category_targets
        target_per = self.config.images_per_combination

        total_needed = 0
        total_have = 0

        for brand, models in sorted(brands.items()):
            for model, model_years in models.items():
                for year in model_years:
                    count = self.file_manager.get_count(brand, model, year)
                    total_have += count
                    total_needed += target_per

        total_combinations = sum(
            len(years) for models in brands.values() for years in models.values()
        )
        breakdown = ", ".join(f"{n} {c}" for c, n in category_targets.items())
        print(f"  Combinations: {total_combinations}")
        print(f"  Per combo:    {breakdown}")
        print(f"  Target total: {total_needed} images")
        print(f"  Downloaded:   {total_have} images")
        print(f"  Remaining:    {total_needed - total_have} images")
