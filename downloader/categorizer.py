"""Image categorizer - classifies car images as interior or exterior."""

import re


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
    "trim",
    "headliner",
    "door panel",
    "gauge",
    "speedometer",
    "tachometer",
    "pedal",
    "armrest",
    "glovebox",
    "glove box",
    "boot",
    "trunk interior",
    "cargo",
    "ambient lighting",
    "display",
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
    "exhaust",
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
    "color",
    "colour",
    "chrome",
    "badge",
    "emblem",
    "logo",
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

# Filename patterns
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


def classify_image(filename="", alt_text="", caption="", page_context=""):
    """
    Classify an image as 'interior' or 'exterior' based on available metadata.

    Uses filename, alt text, caption, and surrounding page context to determine
    the image category. Returns 'exterior' as default when classification is
    ambiguous.

    Args:
        filename: The image filename
        alt_text: Alt text from the img tag
        caption: Caption text near the image
        page_context: Additional text context from the page

    Returns:
        tuple: (category, confidence) where category is 'interior' or 'exterior'
               and confidence is a float 0.0-1.0
    """
    interior_score = 0
    exterior_score = 0

    # Combine all text sources, weighted differently
    text_sources = [
        (filename.lower(), 3.0),      # Filename is most reliable
        (alt_text.lower(), 2.5),      # Alt text is very reliable
        (caption.lower(), 2.0),       # Caption is reliable
        (page_context.lower(), 1.0),  # Page context is least reliable
    ]

    for text, weight in text_sources:
        if not text:
            continue

        for keyword in INTERIOR_KEYWORDS:
            if keyword in text:
                interior_score += weight

        for keyword in EXTERIOR_KEYWORDS:
            if keyword in text:
                exterior_score += weight

    # Check filename patterns (high confidence)
    fname_lower = filename.lower()
    for pattern in INTERIOR_FILE_PATTERNS:
        if re.search(pattern, fname_lower):
            interior_score += 4.0

    for pattern in EXTERIOR_FILE_PATTERNS:
        if re.search(pattern, fname_lower):
            exterior_score += 4.0

    # Determine classification
    total = interior_score + exterior_score
    if total == 0:
        return "exterior", 0.5  # Default to exterior with low confidence

    if interior_score > exterior_score:
        confidence = interior_score / total
        return "interior", min(confidence, 1.0)
    else:
        confidence = exterior_score / total
        return "exterior", min(confidence, 1.0)


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
