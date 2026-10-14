"""Static astrological reference data (Parashari system)."""

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGNS_SANSKRIT = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
]

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SEVEN_PLANETS = PLANETS[:7]
ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
        "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke", "Ascendant": "As"}

# Sign index (0 = Aries) -> lord
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

MOVABLE, FIXED, DUAL = (0, 3, 6, 9), (1, 4, 7, 10), (2, 5, 8, 11)
ELEMENT = ["Fire", "Earth", "Air", "Water"] * 3

# Exaltation: planet -> (sign, exact degree)
EXALTATION = {
    "Sun": (0, 10), "Moon": (1, 3), "Mars": (9, 28), "Mercury": (5, 15),
    "Jupiter": (3, 5), "Venus": (11, 27), "Saturn": (6, 20),
    "Rahu": (1, 20), "Ketu": (7, 20),
}
DEBILITATION = {p: ((s + 6) % 12, d) for p, (s, d) in EXALTATION.items()}

# Moolatrikona: planet -> (sign, start deg, end deg)
MOOLATRIKONA = {
    "Sun": (4, 0, 20), "Moon": (1, 3, 30), "Mars": (0, 0, 12), "Mercury": (5, 15, 20),
    "Jupiter": (8, 0, 10), "Venus": (6, 0, 15), "Saturn": (10, 0, 20),
}

OWN_SIGNS = {
    "Sun": (4,), "Moon": (3,), "Mars": (0, 7), "Mercury": (2, 5),
    "Jupiter": (8, 11), "Venus": (1, 6), "Saturn": (9, 10),
    "Rahu": (10,), "Ketu": (7,),
}

# Natural (naisargika) relationships, BPHS
NATURAL_FRIENDS = {
    "Sun": {"friends": {"Moon", "Mars", "Jupiter"}, "neutral": {"Mercury"}, "enemies": {"Venus", "Saturn"}},
    "Moon": {"friends": {"Sun", "Mercury"}, "neutral": {"Mars", "Jupiter", "Venus", "Saturn"}, "enemies": set()},
    "Mars": {"friends": {"Sun", "Moon", "Jupiter"}, "neutral": {"Venus", "Saturn"}, "enemies": {"Mercury"}},
    "Mercury": {"friends": {"Sun", "Venus"}, "neutral": {"Mars", "Jupiter", "Saturn"}, "enemies": {"Moon"}},
    "Jupiter": {"friends": {"Sun", "Moon", "Mars"}, "neutral": {"Saturn"}, "enemies": {"Mercury", "Venus"}},
    "Venus": {"friends": {"Mercury", "Saturn"}, "neutral": {"Mars", "Jupiter"}, "enemies": {"Sun", "Moon"}},
    "Saturn": {"friends": {"Mercury", "Venus"}, "neutral": {"Jupiter"}, "enemies": {"Sun", "Moon", "Mars"}},
}

NATURAL_BENEFICS = {"Jupiter", "Venus"}  # Moon & Mercury are conditional
NATURAL_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# Special aspects (houses counted from the planet, inclusive). Everyone aspects the 7th.
SPECIAL_ASPECTS = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10), "Rahu": (5, 9), "Ketu": (5, 9)}

# Combustion orbs in degrees from the Sun: (direct, retrograde)
COMBUSTION_ORB = {"Moon": (12, 12), "Mars": (17, 17), "Mercury": (14, 12),
                  "Jupiter": (11, 11), "Venus": (10, 8), "Saturn": (15, 15)}

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
    "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]
NAKSHATRA_SPAN = 360 / 27
PADA_SPAN = NAKSHATRA_SPAN / 4

DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
               "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
DASHA_TOTAL_YEARS = 120

KENDRAS = (1, 4, 7, 10)
TRIKONAS = (1, 5, 9)
DUSTHANAS = (6, 8, 12)
UPACHAYAS = (3, 6, 10, 11)

# Natural significations (karakas) used by the facts extractor
HOUSE_SIGNIFICATIONS = {
    1: "self, body, constitution, appearance, vitality",
    2: "wealth, family, speech, food, face",
    3: "courage, siblings, communication, short travel, efforts",
    4: "mother, home, property, vehicles, happiness, education",
    5: "children, intellect, creativity, past merit, romance, speculation",
    6: "disease, enemies, debts, service, litigation",
    7: "spouse, marriage, partnerships, business",
    8: "longevity, chronic illness, sudden events, inheritance, occult",
    9: "fortune, father, dharma, higher learning, guru, long travel",
    10: "career, status, karma, authority, reputation",
    11: "gains, income, elder siblings, fulfilment of desires",
    12: "losses, expenses, foreign lands, isolation, moksha, sleep",
}
