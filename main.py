#!/usr/bin/env python3
"""
Photo Downloader - Luxury car image scraper and categorizer.

Downloads high-quality images from manufacturer media sites and image
galleries, organizing them into folders by:

    downloads/
    └── {Make}/
        └── {Model}/
            └── {Year}/
                ├── exterior/
                │   ├── porsche_911_2024_exterior_001.jpg
                │   └── ...
                └── interior/
                    ├── porsche_911_2024_interior_001.jpg
                    └── ...

Usage:
    python main.py download                    # Download all configured brands
    python main.py download -b Porsche         # Download only Porsche
    python main.py download -b BMW -m "3 Series" -y 2024
    python main.py download --source wikimedia # Use only Wikimedia Commons
    python main.py download --dry-run          # Preview without downloading
    python main.py status                      # Show download progress
    python main.py list-brands                 # Show configured brands
    python main.py list-sources                # Show configured sources
"""

from downloader.cli import main

if __name__ == "__main__":
    main()
