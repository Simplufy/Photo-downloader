"""File manager - handles folder creation and image storage."""

import hashlib
import json
import os
import re
from pathlib import Path


class FileManager:
    """Manages the download directory structure and tracks downloaded images."""

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.base_dir / ".download_manifest.json"
        self._manifest = self._load_manifest()

    def _load_manifest(self):
        """Load the download manifest tracking all downloaded images."""
        if self._manifest_path.exists():
            with open(self._manifest_path, "r") as f:
                data = json.load(f)
            data.setdefault("category_counts", {})
            return data
        return {"downloaded_urls": {}, "file_hashes": set(), "counts": {}, "category_counts": {}}

    def save_manifest(self):
        """Persist the manifest to disk."""
        # Convert set to list for JSON serialization
        data = {
            "downloaded_urls": self._manifest["downloaded_urls"],
            "file_hashes": list(self._manifest.get("file_hashes", set())),
            "counts": self._manifest["counts"],
            "category_counts": self._manifest.get("category_counts", {}),
        }
        with open(self._manifest_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_save_path(self, make, model, year, category):
        """
        Build and return the folder path for an image.

        Structure: downloads/Make/Model/Year/category/
        Example:   downloads/Porsche/911/2024/exterior/

        Args:
            make: Brand name (e.g. "Porsche")
            model: Model name (e.g. "911")
            year: Model year (e.g. 2024)
            category: "interior" or "exterior"

        Returns:
            Path object for the target directory
        """
        safe_make = self._sanitize_name(make)
        safe_model = self._sanitize_name(model)
        safe_year = str(year)
        safe_category = category.lower()

        folder = self.base_dir / safe_make / safe_model / safe_year / safe_category
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def get_count(self, make, model, year):
        """Return how many images have been downloaded for a make/model/year."""
        key = self._count_key(make, model, year)
        return self._manifest["counts"].get(key, 0)

    def increment_count(self, make, model, year):
        """Increment the download count for a make/model/year."""
        key = self._count_key(make, model, year)
        self._manifest["counts"][key] = self._manifest["counts"].get(key, 0) + 1

    def get_category_count(self, make, model, year, category):
        """Return count for a specific make/model/year/category."""
        key = f"{self._count_key(make, model, year)}|{category}"
        return self._manifest["category_counts"].get(key, 0)

    def increment_category_count(self, make, model, year, category):
        """Increment count for a specific make/model/year/category."""
        key = f"{self._count_key(make, model, year)}|{category}"
        cc = self._manifest["category_counts"]
        cc[key] = cc.get(key, 0) + 1

    def is_url_downloaded(self, url):
        """Check if a URL has already been downloaded."""
        return url in self._manifest["downloaded_urls"]

    def mark_url_downloaded(self, url, save_path):
        """Record that a URL has been downloaded."""
        self._manifest["downloaded_urls"][url] = str(save_path)

    def is_duplicate_content(self, image_data):
        """Check if we already have an image with the same content hash."""
        h = hashlib.md5(image_data).hexdigest()
        hashes = self._manifest.get("file_hashes", set())
        if isinstance(hashes, list):
            hashes = set(hashes)
            self._manifest["file_hashes"] = hashes
        return h in hashes

    def record_content_hash(self, image_data):
        """Record the content hash of a downloaded image."""
        h = hashlib.md5(image_data).hexdigest()
        hashes = self._manifest.get("file_hashes", set())
        if isinstance(hashes, list):
            hashes = set(hashes)
            self._manifest["file_hashes"] = hashes
        hashes.add(h)

    def generate_filename(self, make, model, year, category, original_url, index=None):
        """
        Generate a clean, descriptive filename for an image.

        Format: make_model_year_category_NNN.ext
        Example: porsche_911_2024_exterior_001.jpg
        """
        ext = self._get_extension(original_url)
        safe_make = self._sanitize_name(make).lower()
        safe_model = self._sanitize_name(model).lower()

        if index is not None:
            name = f"{safe_make}_{safe_model}_{year}_{category}_{index:03d}{ext}"
        else:
            count = self.get_count(make, model, year) + 1
            name = f"{safe_make}_{safe_model}_{year}_{category}_{count:03d}{ext}"

        return name

    def get_next_index(self, make, model, year, category):
        """Get the next available index for a make/model/year/category."""
        folder = self.get_save_path(make, model, year, category)
        existing = list(folder.glob("*"))
        return len(existing) + 1

    @staticmethod
    def _sanitize_name(name):
        """Make a name safe for use as a directory/file name."""
        # Replace problematic characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'\s+', '_', name.strip())
        # Remove leading/trailing dots and spaces
        name = name.strip('. ')
        return name or "unknown"

    @staticmethod
    def _get_extension(url):
        """Extract file extension from URL, defaulting to .jpg."""
        # Strip query params
        clean = url.split('?')[0].split('#')[0]
        _, ext = os.path.splitext(clean)
        ext = ext.lower()
        if ext in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'):
            return ext
        return '.jpg'

    @staticmethod
    def _count_key(make, model, year):
        return f"{make}|{model}|{year}"

    def print_summary(self):
        """Print a summary of all downloaded images."""
        print("\n" + "=" * 60)
        print("DOWNLOAD SUMMARY")
        print("=" * 60)

        if not self._manifest["counts"]:
            print("No images downloaded yet.")
            return

        total = 0
        for key, count in sorted(self._manifest["counts"].items()):
            parts = key.split("|")
            if len(parts) == 3:
                make, model, year = parts
                print(f"  {make} {model} ({year}): {count} images")
            total += count

        print("-" * 60)
        print(f"  Total: {total} images")
        print("=" * 60)
