# Photo Downloader

Download and categorize luxury car images from manufacturer media sites and image galleries.

## Folder Structure

Images are organized into:

```
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
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Download all configured brands/models/years (20 images each)
python main.py download -v

# Download only one brand
python main.py download -b Porsche

# Download a specific make/model/year
python main.py download -b BMW -m "3 Series" -y 2024

# Use only a specific source
python main.py download --source wikimedia
python main.py download --source netcarshow

# Preview what would be downloaded (no actual downloads)
python main.py download --dry-run

# Override images-per-combination count
python main.py download -l 50

# Check download progress
python main.py status

# List configured brands and models
python main.py list-brands

# List configured sources
python main.py list-sources
```

## Sources

| Source | Type | URL |
|--------|------|-----|
| NetCarShow | Gallery | netcarshow.com |
| Wikimedia Commons | API | commons.wikimedia.org |
| Motor1 | Gallery | motor1.com/photos |
| Audi Media | Manufacturer | audi-mediacenter.com |
| BMW Media | Manufacturer | press.bmwgroup.com |
| Mercedes Media | Manufacturer | media.mercedes-benz.com |
| Porsche Newsroom | Manufacturer | newsroom.porsche.com |
| Ferrari Media | Manufacturer | media.ferrari.com |
| Bentley Media | Manufacturer | bentleymedia.com |
| Rolls-Royce Media | Manufacturer | press.rolls-roycemotorcars.com |
| Lamborghini Media | Manufacturer | media.lamborghini.com |
| McLaren Press | Manufacturer | cars.mclaren.press |
| Jaguar Media | Manufacturer | media.jaguar.com |
| Aston Martin Media | Manufacturer | media.astonmartin.com |
| Bugatti Newsroom | Manufacturer | newsroom.bugatti.com |
| Maserati Media | Manufacturer | media.maserati.com |
| Pagani Press | Manufacturer | pagani.com/press |
| Koenigsegg Media | Manufacturer | koenigsegg.com/media |
| Lotus Media | Manufacturer | media.lotuscars.com |
| Rimac Media | Manufacturer | rimac-automobili.com/media |
| Pininfarina Media | Manufacturer | automobili-pininfarina.com/media-hub |
| Gordon Murray Media | Manufacturer | gordonmurrayautomotive.com/media-centre |

## Configuration

Edit `config.yaml` to:

- Add/remove brands and models
- Change target years
- Adjust images per combination (default: 20)
- Set minimum image dimensions
- Enable/disable specific sources
- Tune rate limiting and retry settings

## Image Categorization

Images are automatically classified as **interior** or **exterior** based on:

- Filename patterns (e.g., `*_interior_*`, `*_cockpit_*`)
- Alt text and captions from the source page
- Surrounding page context and keywords

The classifier uses weighted keyword matching across ~50 interior and ~60 exterior indicator terms.
