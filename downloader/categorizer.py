"""Image categorizer - classifies car images into exterior/interior/trunk/engine."""

import re


# Keywords for trunk/cargo area shots (checked first - most specific)
TRUNK_KEYWORDS = [
    "trunk open",
    "trunk space",
    "trunk capacity",
    "boot space",
    "boot open",
    "cargo space",
    "cargo area",
    "cargo capacity",
    "cargo volume",
    "luggage compartment",
    "luggage space",
    "luggage capacity",
    "storage space",
    "storage compartment",
    "load area",
    "load space",
    "kofferraum",  # German: trunk
    "coffre",      # French: trunk
    "bagagliaio",  # Italian: trunk
]

# Keywords for engine bay shots (checked second - specific)
ENGINE_KEYWORDS = [
    "engine bay",
    "engine compartment",
    "engine room",
    "engine detail",
    "motor bay",
    "motor compartment",
    "motor detail",
    "under the hood",
    "under the bonnet",
    "under hood",
    "under bonnet",
    "powerplant",
    "engine block",
    "cylinder head",
    "valve cover",
    "intake manifold",
    "motorraum",           # German: engine bay
    "compartiment moteur", # French: engine bay
    "vano motore",         # Italian: engine bay
]

# Keywords that strongly indicate interior shots
INTERIOR_KEYWORDS = [
    "interior",
    "cabin",
    "cockpit",
    "dashboard",
    "dash",
    "steering wheel",
    "steering",
    "instrument cluster",
    "instrument panel",
    "infotainment",
    "center console",
    "centre console",
    "gear shift",
    "gearshift",
    "seats",
    "rear seat",
    "front seat",
    "back seat",
    "upholstery",
    "leather",
    "headliner",
    "door panel",
    "gauge",
    "speedometer",
    "tachometer",
    "pedal",
    "armrest",
    "glovebox",
    "glove box",
    "ambient lighting",
    "touchscreen",
    "head-up",
    "heads-up",
    "hud",
    "panoramic roof inside",
    "sunroof inside",
    "rear bench",
    "center tunnel",
    "centre tunnel",
    "innenraum",  # German: interior
    "interieur",  # French/German: interior
    "habitacle",  # French: cabin
]

# Keywords that strongly indicate exterior shots
EXTERIOR_KEYWORDS = [
    "exterior",
    "front view",
    "rear view",
    "side view",
    "front quarter",
    "rear quarter",
    "three-quarter",
    "3/4 view",
    "profile",
    "driving",
    "on road",
    "on track",
    "parked",
    "static",
    "front fascia",
    "rear fascia",
    "grille",
    "headlight",
    "headlamp",
    "taillight",
    "tail light",
    "tail lamp",
    "bumper",
    "hood",
    "bonnet",
    "fender",
    "wheel",
    "rim",
    "tire",
    "tyre",
    "spoiler",
    "wing",
    "diffuser",
    "splitter",
    "roofline",
    "silhouette",
    "aerodynamic",
    "body",
    "paintwork",
    "paint",
    "badge",
    "emblem",
    "windshield",
    "windscreen",
    "side mirror",
    "door handle",
    "roof rack",
    "action shot",
    "cornering",
    "motion",
    "dynamic",
    "studio shot",
    "press photo",
    "beauty shot",
    "hero shot",
    "aussenansicht",  # German: exterior view
    "exterieur",  # French/German: exterior
]

# Filename patterns per category
TRUNK_FILE_PATTERNS = [
    r"trunk",
    r"boot[\-_\s]?(?:space|open|capacity)",
    r"cargo",
    r"luggage",
    r"kofferraum",
]

ENGINE_FILE_PATTERNS = [
    r"engine",
    r"motor[\-_\s]?(?:bay|compartment|detail|room)",
    r"powertrain",
    r"under[\-_\s]?(?:hood|bonnet)",
]

INTERIOR_FILE_PATTERNS = [
    r"int(?:erior)?[\-_\s]",
    r"cabin",
    r"cockpit",
    r"dashboard",
    r"steering",
    r"seat",
    r"console",
    r"innen",
]

EXTERIOR_FILE_PATTERNS = [
    r"ext(?:erior)?[\-_\s]",
    r"front[\-_\s]",
    r"rear[\-_\s]",
    r"side[\-_\s]",
    r"driving",
    r"static",
    r"profile",
    r"aussen",
]

# All categories with their keyword/pattern lists
CATEGORIES = {
    "trunk":    (TRUNK_KEYWORDS,    TRUNK_FILE_PATTERNS),
    "engine":   (ENGINE_KEYWORDS,   ENGINE_FILE_PATTERNS),
    "interior": (INTERIOR_KEYWORDS, INTERIOR_FILE_PATTERNS),
    "exterior": (EXTERIOR_KEYWORDS, EXTERIOR_FILE_PATTERNS),
}


def classify_image(filename="", alt_text="", caption="", page_context=""):
    """
    Classify an image as exterior, interior, trunk, or engine.

    Returns:
        tuple: (category, confidence) where confidence is 0.0-1.0
    """
    scores = {cat: 0.0 for cat in CATEGORIES}

    text_sources = [
        (filename.lower(), 3.0),
        (alt_text.lower(), 2.5),
        (caption.lower(), 2.0),
        (page_context.lower(), 1.0),
    ]

    for cat, (keywords, file_patterns) in CATEGORIES.items():
        for text, weight in text_sources:
            if not text:
                continue
            for keyword in keywords:
                if keyword in text:
                    scores[cat] += weight

        # Check filename patterns (high confidence)
        fname_lower = filename.lower()
        for pattern in file_patterns:
            if re.search(pattern, fname_lower):
                scores[cat] += 4.0

    total = sum(scores.values())
    if total == 0:
        return "exterior", 0.5

    best = max(scores, key=scores.get)
    confidence = scores[best] / total
    return best, min(confidence, 1.0)


def extract_vehicle_info(text):
    """
    Try to extract year, make, and model from text.

    Args:
        text: Text that might contain vehicle information

    Returns:
        dict with keys 'year', 'make', 'model' (values may be None)
    """
    info = {"year": None, "make": None, "model": None}

    if not text:
        return info

    # Extract year (4-digit number between 2000-2030)
    year_match = re.search(r'\b(20[0-3]\d)\b', text)
    if year_match:
        info["year"] = int(year_match.group(1))

    # Known brand names to look for
    brand_patterns = {
        "Audi": r'\baudi\b',
        "BMW": r'\bbmw\b',
        "Mercedes-Benz": r'\b(?:mercedes[\-\s]?benz|mercedes|merc)\b',
        "Porsche": r'\bporsche\b',
        "Ferrari": r'\bferrari\b',
        "Bentley": r'\bbentley\b',
        "Rolls-Royce": r'\b(?:rolls[\-\s]?royce|rolls royce)\b',
        "Lamborghini": r'\blamborghini\b',
        "McLaren": r'\bmclaren\b',
        "Jaguar": r'\bjaguar\b',
        "Aston Martin": r'\b(?:aston[\-\s]?martin)\b',
        "Bugatti": r'\bbugatti\b',
        "Maserati": r'\bmaserati\b',
        "Pagani": r'\bpagani\b',
        "Koenigsegg": r'\bkoenigsegg\b',
        "Lotus": r'\blotus\b',
        "Rimac": r'\brimac\b',
        "Pininfarina": r'\b(?:automobili[\-\s]?)?pininfarina\b',
        "Gordon Murray": r'\b(?:gordon[\-\s]?murray)\b',
    }

    text_lower = text.lower()
    for brand, pattern in brand_patterns.items():
        if re.search(pattern, text_lower):
            info["make"] = brand
            break

    return info
