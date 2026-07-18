"""Pattern di matching e NLP — unica fonte di verità.

Copiato da lib/patterns.py e mantenuto come primario.
lib/patterns.py diventa wrapper backward-compat.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Any

# ── TAG_PATTERN: regex per matching denominazione ETS ──────────────────

TAG_PATTERN: dict[str, str] = {
    "sport":                r"(sport|asd|calcio|atletica|nuoto|pallavolo|ginnastica|basket|tennis|scherma|ciclismo|equitazion|vela|canottaggio)",
    "disabilità":           r"(disabil|handicap|anffas|down|autism|sord|paralisi|lesion|ipov|neuro|demen)",
    "minori":               r"(minori|bambin|ragazz|adolescent|infanzia|bambino|children|child)",
    "giovani":              r"(giovani|ragazz|studentesc|neet|gioventù|giovanile|youth|young)",
    "cultura":              r"(cultura|museo|teatro|music|biblioteca|\barte\b|cinema|mostra|esposizion|patrimonio|perform|artistic)",
    "ambiente":             r"(ambiente|natura|ecolog|riciclo|sostenibil|verde|rifiuti|clima|transizione ecologica|sprechi|environment|climate)",
    "lavoro":               r"(lavoro|formazion|impiego|occupazion|professional|orientament|parti sociali|sindac|work|employment)",
    "salute":               r"(salute|sanit|medic|ricovero|cura|ospedal|prevenzion|benessere|health|emergency)",
    "educazione":           r"(educazion|scuola|istruzion|didattic|apprendiment|scolastic|education|school|learning)",
    "inclusione sociale":   r"(inclusione|integrazion|solidariet|povert|emarginazion|poverty|inclusion|disadvantaged)",
    "anziani":              r"(anzian|terza età|over\d+|silver)",
    "donne":                r"(donne|femminil|parità|genere|donna|women|woman|gender)",
    "migranti":             r"(migrant|rifugiat|stranier|immigrazion|intercultur|richiedent|ucrain|refugee|asylum)",
    "digitale":             r"(digitale|digital|informatic|tecnologia|software|ict|innovazion tecnologica|tech|coding)",
    "volontariato":         r"(volontariato|volontari|odv|organizzazion di volontariat)",
    "ricerca":              r"(ricerca|scientific|innovazion|sviluppo sperimentale|research)",
    "musica":               r"(music|orchestra|coro|banda|filarmonic|canto)",
    "agricoltura sociale":  r"(agricol|ort|fattoria|campagna|rurale|agri-soc)",
    "beni confiscati":      r"(beni confiscat|beni comuni|legalità|antimafia)",
    "povertà educativa":    r"(povertà educativa|dispersione scolastic|abbandono scolastic)",
    "cooperazione internazionale": r"(cooperazione internazional|sviluppo|africa|sud del mondo|ucrain|balcan|mediterraneo)",
    "pari opportunità":     r"(pari opportunità|parità di genere|discriminazion)",
    "dipendenze":           r"(dipendenz|tossicodipendenz|alcool|droga)",
    "animali":              r"(animali|cinofil|pet|canile|rifugio)",
    "malattie rare":        r"(malattie rare|malattia rara)",
    "cittadinanza attiva":  r"(cittadinanza attiva|partecipazion|civic|democrazia)",
    "diritti umani":        r"(diritti umani|diritto|civili|fondamentali)",
    "acqua":                r"(acqua|idric|depurazion)",
    "beni comuni":          r"(beni comuni|comunità|partecipazion|coprogettazion)",
}

GENERIC_TAGS: set[str] = {"lavoro", "inclusione", "ricerca", "giovani", "educazione", "salute"}

# ── SECTION_TAG_MAP: tag → sezioni RUNTS ──────────────────────────────

SECTION_TAG_MAP: dict[str, list[str]] = {
    "sport":                ["ASSOCIAZIONI DI PROMOZIONE SOCIALE"],
    "disabilità":           ["IMPRESE SOCIALI", "ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "minori":               ["ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "giovani":              ["ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "cultura":              ["ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "ambiente":             ["ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "lavoro":               ["IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "formazione":           ["IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "salute":               ["ORGANIZZAZIONI DI VOLONTARIATO", "ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "educazione":           ["IMPRESE SOCIALI", "ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "inclusione sociale":   ["IMPRESE SOCIALI", "ORGANIZZAZIONI DI VOLONTARIATO",
                              "ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ALTRI ENTI DEL TERZO SETTORE"],
    "anziani":              ["ORGANIZZAZIONI DI VOLONTARIATO", "IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "donne":                ["ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "migranti":             ["ORGANIZZAZIONI DI VOLONTARIATO", "IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "digitale":             ["IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "volontariato":         ["ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "ricerca":              ["ASSOCIAZIONI DI PROMOZIONE SOCIALE", "IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "musica":               ["ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "agricoltura sociale":  ["IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "beni confiscati":      ["ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "povertà educativa":    ["IMPRESE SOCIALI", "ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "cooperazione internazionale": ["ORGANIZZAZIONI DI VOLONTARIATO", "ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "pari opportunità":     ["ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "dipendenze":           ["ORGANIZZAZIONI DI VOLONTARIATO", "IMPRESE SOCIALI",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "animali":              ["ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "malattie rare":        ["ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "cittadinanza attiva":  ["ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "diritti umani":        ["ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ORGANIZZAZIONI DI VOLONTARIATO",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "acqua":                [],
    "beni comuni":          ["ASSOCIAZIONI DI PROMOZIONE SOCIALE",
                              "ALTRI ENTI DEL TERZO SETTORE"],
    "premi":                [],
}

# ── REGIONE → PROVINCE ────────────────────────────────────────────────

REGION_PROVINCES: dict[str, list[str]] = {
    "Abruzzo": ["AQ", "CH", "PE", "TE"],
    "Basilicata": ["PZ", "MT"],
    "Calabria": ["CZ", "CS", "KR", "RC", "VV"],
    "Campania": ["AV", "BN", "CE", "NA", "SA"],
    "Emilia-Romagna": ["BO", "FE", "FC", "MO", "PC", "PR", "RA", "RE", "RN"],
    "Friuli Venezia Giulia": ["GO", "PN", "TS", "UD"],
    "Lazio": ["FR", "LT", "RI", "RM", "VT"],
    "Liguria": ["GE", "IM", "SP", "SV"],
    "Lombardia": ["BG", "BS", "CO", "CR", "LC", "LO", "MB", "MI", "MN", "PV", "SO", "VA"],
    "Marche": ["AN", "AP", "FM", "MC", "PU"],
    "Molise": ["CB", "IS"],
    "Piemonte": ["AL", "AT", "BI", "CN", "NO", "TO", "VB", "VC"],
    "Puglia": ["BA", "BR", "BT", "FG", "LE", "TA"],
    "Sardegna": ["CA", "NU", "OR", "SS", "SU"],
    "Sicilia": ["AG", "CL", "CT", "EN", "ME", "PA", "RG", "SR", "TP"],
    "Toscana": ["AR", "FI", "GR", "LI", "LU", "MS", "PI", "PO", "PT", "SI"],
    "Trentino Alto Adige": ["BZ", "TN"],
    "Umbria": ["PG", "TR"],
    "Valle d'Aosta": ["AO"],
    "Veneto": ["BL", "PD", "RO", "TV", "VE", "VI", "VR"],
}

MEZZOGIORNO_PROVINCES: list[str] = (
    REGION_PROVINCES["Abruzzo"] + REGION_PROVINCES["Basilicata"]
    + REGION_PROVINCES["Calabria"] + REGION_PROVINCES["Campania"]
    + REGION_PROVINCES["Molise"] + REGION_PROVINCES["Puglia"]
    + REGION_PROVINCES["Sardegna"] + REGION_PROVINCES["Sicilia"]
)

# ── MAPPA CATEGORIE INFOBANDI ────────────────────────────────────────

INFOBANDI_CAT_MAP: dict[int, str] = {
    1200: "giovani",
    1199: "volontariato",
    803:  "volontariato",
    1201: "cultura",
    1234: "diritti",
    1434: "migranti",
    1213: "lavoro",
    130:  "giovani",
    81:   "sport",
    1203: "migranti",
    1206: "ambiente",
    1208: "giustizia",
    1204: "ricerca",
    128:  "cultura",
    127:  "cooperazione internazionale",
}

# ── TEXT_KEYWORDS: NLP per estrarre tag da testi bandi ────────────────

TEXT_KEYWORDS: dict[str, str] = {
    "sport":        r"\b(sport|calcio|atletica|nuoto|pallavolo|ginnastica|basket|tennis|scherma|ciclismo|vela|canottaggio|asd)\b",
    "disabilità":   r"\b(disabil|handicap|anffas|down|autism|sord|paralisi|lesion|ipov|neuro|demen)\b",
    "minori":       r"\b(minori|bambin|ragazz|adolescent|infanzia|bambino|children|child|infant)\b",
    "giovani":      r"\b(giovani|ragazz|studentesc|neet|under\s?\d+|gioventù|giovanile|youth|young)\b",
    "cultura":      r"\b(cultura|museo|teatro|music|biblioteca|arte|cinema|mostra|esposizion|patrimonio|creatività)\b",
    "arte":         r"\b(arte|artist|artigian)\b",
    "ambiente":     r"\b(ambiente|natura|ecolog|riciclo|sostenibil|verde|rifiuti|clima|sprechi|spreco|transizione|environment|greenpeace|climate)\b",
    "lavoro":       r"\b(lavoro|formazion|impiego|occupazion|professional|orientament|parti sociali|sindacale|work|labour|employment)\b",
    "salute":       r"\b(salute|sanit|medic|ricovero|cura|ospedal|prevenzion|benessere|health|emergency|cancer)\b",
    "educazione":   r"\b(educazion|scuola|istruzion|didattic|apprendiment|scolastic|education|school|learning)\b",
    "inclusione sociale": r"\b(inclusione|integrazion|solidariet|povert|emarginazion|inclusion|poverty|disadvantaged)\b",
    "donne":        r"\b(donne|femminil|parità|genere|donna|migratorio|violenza di genere|women|woman|gender)\b",
    "migranti":     r"\b(migrant|rifugiat|stranier|immigrazion|intercultur|richiedent|ucrain|refugee|asylum)",
    "digitale":     r"\b(digitale|digital|informatic|tecnologia|software|ict|tech|coding)\b",
    "ricerca":      r"\b(ricerca|scientific|innovazion|research|innovation)\b",
    "musica":       r"\b(music|orchestra|coro|banda|filarmonic|canto)\b",
    "volontariato": r"\b(volontariato|volontari|solidarietà)\b",
    "animali":      r"\b(animali|cinofil|pet|canile|rifugio|protezione animali)\b",
    "premi":        r"\b(premio|premi|prize|concorso|challenge)\b",
}


# ── Funzioni ──────────────────────────────────────────────────────────

def get_pattern_from_tags(tags: list[str]) -> str | None:
    """Costruisce pattern regexp combinato dai tag del bando."""
    tags_lower = set(t.lower() for t in tags)
    specific = {t for t in tags_lower if t not in GENERIC_TAGS}
    specific_validi = {t for t in specific if t in TAG_PATTERN}
    generici_validi = {t for t in tags_lower if t in TAG_PATTERN}
    use_tags = specific_validi if specific_validi else generici_validi
    parts = []
    for tag, pattern in TAG_PATTERN.items():
        if tag in use_tags and pattern:
            parts.append(pattern)
    return "|".join(parts) if parts else None


def extract_tags_from_text(text: str) -> list[str]:
    """NLP leggero: estrae tag dal testo usando TEXT_KEYWORDS."""
    text_lower = text.lower()
    found = []
    for tag, pattern in TEXT_KEYWORDS.items():
        if re.search(pattern, text_lower):
            found.append(tag)
    return found


def get_sections_from_tags(tags: list[str]) -> list[str]:
    """Restituisce le sezioni RUNTS pertinenti per i tag dati."""
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        t_clean = t.strip().lower()
        sezioni = SECTION_TAG_MAP.get(t_clean, [])
        for s in sezioni:
            if s not in seen:
                seen.add(s)
                result.append(s)
    return result


def get_province_filter(territorio: list[str]) -> list[str]:
    """Restituisce province per filtro geografico."""
    if not territorio:
        return []
    provinces = []
    for t in territorio:
        t_clean = t.strip().title()
        if t_clean == "Mezzogiorno":
            return list(MEZZOGIORNO_PROVINCES)
        if t_clean in REGION_PROVINCES:
            provinces.extend(REGION_PROVINCES[t_clean])
    return provinces


def normalize_comune(nome: str) -> str:
    """Normalizza nome comune: NFD, uppercase, rimuove apostrofi."""
    if not nome:
        return ""
    nome = unicodedata.normalize("NFD", nome.strip().upper())
    nome = nome.replace("'", "").replace("`", "").replace("´", "")
    nome = re.sub(r'\bMC\xCC\xA7\xCC\x87[AEIOU]\b', 'M', nome)  # noqa
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome.replace("'", "").replace("`", "").replace("´", "")


# SPECIAL_COMUNI: correzioni manuali per comuni con nomi complessi
# (importato da cruscotto-italia)
SPECIAL_COMUNI: dict[str, str] = {
    "SANT'ANTONIO ABATE": "SANTANTONIO ABATE",
    "SANT'ANTIMO": "SANTANTIMO",
    "MONTE SAN GIUSTO": "MONTE SAN GIUSTO",
    "ROCCA SAN CASCIANO": "ROCCA SAN CASCIANO",
    "SAN GIOVANNI LUPATOTO": "SAN GIOVANNI LUPATOTO",
    "SAN GIOVANNI IN PERSICETO": "SAN GIOVANNI IN PERSICETO",
    "SAN GIOVANNI IN FIORE": "SAN GIOVANNI IN FIORE",
    "SAN GIOVANNI LA PUNTA": "SAN GIOVANNI LA PUNTA",
    "SAN GIOVANNI ROTONDO": "SAN GIOVANNI ROTONDO",
    "SAN GIORGIO DI MANTOVA": "SAN GIORGIO DI MANTOVA",
    "SAN GIORGIO IN BOSCO": "SAN GIORGIO IN BOSCO",
    "SAN GIORGIO A CREMANO": "SAN GIORGIO A CREMANO",
    "SAN GIORGIO SU LEGNANO": "SAN GIORGIO SU LEGNANO",
    "SAN GIUSEPPE VESUVIANO": "SAN GIUSEPPE VESUVIANO",
    "SAN GREGORIO DI CATANIA": "SAN GREGORIO DI CATANIA",
    "SAN MARCO IN LAMIS": "SAN MARCO IN LAMIS",
    "SAN MARCO ARGENTANO": "SAN MARCO ARGENTANO",
    "SAN MARTINO SICCOMARIO": "SAN MARTINO SICCOMARIO",
    "SAN MARTINO BUON ALBERGO": "SAN MARTINO BUON ALBERGO",
    "SAN MAURO TORINESE": "SAN MAURO TORINESE",
    "SAN MAURO PASCOLI": "SAN MAURO PASCOLI",
    "SAN MAURO LA BRUCA": "SAN MAURO LA BRUCA",
    "SAN NAZZARO": "SAN NAZZARO",
    "SAN PAOLO D'ARGON": "SAN PAOLO DARGON",
    "SAN PAOLO DI CIVITATE": "SAN PAOLO DI CIVITATE",
    "SAN PIERO PATTI": "SAN PIERO PATTI",
    "SAN PIETRO DI FEBBETO": "SAN PIETRO DI FEBBETO",
    "SAN PIETRO IN CASALE": "SAN PIETRO IN CASALE",
    "SAN PIETRO IN GU": "SAN PIETRO IN GU",
    "SAN PIETRO MOSEZZO": "SAN PIETRO MOSEZZO",
    "SAN PIETRO VERNOTICO": "SAN PIETRO VERNOTICO",
    "SAN PROSPERO": "SAN PROSPERO",
    "SAN SEBASTIANO AL VESUVIO": "SAN SEBASTIANO AL VESUVIO",
    "SAN SEBASTIANO CURONE": "SAN SEBASTIANO CURONE",
    "SAN SEVERINO MARCHE": "SAN SEVERINO MARCHE",
    "RAVANUSA": "RAVANUSA",
    "PORTOPALO DI CAPO PASSERO": "PORTOPALO DI CAPO PASSERO",
    "LAGONEGRO": "LAGONEGRO",
    "ROVIGO": "ROVIGO",
    "GIOVINAZZO": "GIOVINAZZO",
    "MOLA DI BARI": "MOLA DI BARI",
    "PALO DEL COLLE": "PALO DEL COLLE",
    "RUVO DI PUGLIA": "RUVO DI PUGLIA",
    "SAMMICHELE DI BARI": "SAMMICHELE DI BARI",
    "SANNICANDRO DI BARI": "SANNICANDRO DI BARI",
    "TERLIZZI": "TERLIZZI",
    "TORITTO": "TORITTO",
    "TRIGGIANO": "TRIGGIANO",
    "TURI": "TURI",
    "VALENZANO": "VALENZANO",
}
