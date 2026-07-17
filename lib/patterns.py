"""Pattern di matching e NLP: unica fonte di verità per scan_completo e segnale."""

TAG_PATTERN = {
    "sport":                r"(sport|asd|calcio|atletica|nuoto|pallavolo|ginnastica|basket|tennis|scherma|ciclismo|equitazion|vela|canottaggio)",
    "disabilità":           r"(disabil|handicap|anffas|down|autism|sord|paralisi|lesion|ipov|neuro|demen)",
    "minori":               r"(minori|bambin|ragazz|adolescent|infanzia|bambino)",
    "giovani":              r"(giovani|ragazz|studentesc|neet|gioventù|giovanile)",
    "cultura":              r"(cultura|museo|teatro|music|biblioteca|\barte\b|cinema|mostra|esposizion|patrimonio|perform|artistic)",
    "ambiente":             r"(ambiente|natura|ecolog|riciclo|sostenibil|verde|rifiuti|clima|transizione ecologica|sprechi)",
    "lavoro":               r"(lavoro|formazion|impiego|occupazion|professional|orientament|parti sociali|sindac)",
    "salute":               r"(salute|sanit|medic|ricovero|cura|ospedal|prevenzion|benessere)",
    "educazione":           r"(educazion|scuola|istruzion|didattic|apprendiment|scolastic)",
    "inclusione sociale":   r"(inclusione|integrazion|solidariet|povert|emarginazion)",
    "anziani":              r"(anzian|terza età|over\d+|silver)",
    "donne":                r"(donne|femminil|parità|genere|donna)",
    "migranti":             r"(migrant|rifugiat|stranier|immigrazion|intercultur|richiedent|ucrain)",
    "digitale":             r"(digitale|digital|informatic|tecnologia|software|ict|innovazion tecnologica)",
    "volontariato":         r"(volontariato|volontari|odv|organizzazion di volontariat)",
    "ricerca":              r"(ricerca|scientific|innovazion|sviluppo sperimentale)",
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

GENERIC_TAGS = {"lavoro", "inclusione", "ricerca", "giovani", "educazione", "salute"}

# Mappa categorie infobandi (ID → tag)
# Fonte: https://infobandi.csvnet.it/wp-json/wp/v2/categories?per_page=50
INFOBANDI_CAT_MAP = {
    1200: "giovani",      # Erasmus+
    1199: "volontariato", # Corpo Europeo di Solidarietà
    803:  "volontariato", # Corpo Europeo di Solidarietà
    1201: "cultura",      # Europa Creativa
    1234: "diritti",      # CERV
    1434: "migranti",     # Ucraina
    1213: "lavoro",       # Mercato Unico
    130:  "giovani",      # Erasmus +
    81:   "sport",        # Programmi UE 2014-2020
    1203: "migranti",     # FAMI
    1206: "ambiente",     # LIFE
    1208: "giustizia",    # Giustizia
    1204: "ricerca",      # Horizon Europe
    128:  "cultura",      # Nazionali (Ministero Cultura, etc.)
    127:  "cooperazione internazionale", # Internazionali
}

TEXT_KEYWORDS = {
    "sport":        r"\b(sport|calcio|atletica|nuoto|pallavolo|ginnastica|basket|tennis|scherma|ciclismo|vela|canottaggio|asd)\b",
    "disabilità":   r"\b(disabil|handicap|anffas|down|autism|sord|paralisi|lesion|ipov|neuro|demen)\b",
    "minori":       r"\b(minori|bambin|ragazz|adolescent|infanzia|bambino|alunni|minore)\b",
    "giovani":      r"\b(giovani|ragazz|studentesc|neet|under\s?\d+|gioventù|giovanile|youth)\b",
    "cultura":      r"\b(cultura|museo|teatro|music|biblioteca|arte|cinema|mostra|esposizion|patrimonio|creatività)\b",
    "arte":         r"\b(arte|artist|artigian)\b",
    "ambiente":     r"\b(ambiente|natura|ecolog|riciclo|sostenibil|verde|rifiuti|clima|sprechi|spreco|transizione)\b",
    "lavoro":       r"\b(lavoro|formazion|impiego|occupazion|professional|orientament|parti sociali|sindacale)\b",
    "salute":       r"\b(salute|sanit|medic|ricovero|cura|ospedal|prevenzion|benessere)\b",
    "educazione":   r"\b(educazion|scuola|istruzion|didattic|apprendiment|scolastic)\b",
    "inclusione sociale": r"\b(inclusione|integrazion|solidariet|povert|emarginazion)\b",
    "donne":        r"\b(donne|femminil|parità|genere|donna|migratorio|violenza di genere)\b",
    "migranti":     r"\b(migrant|rifugiat|stranier|immigrazion|intercultur|richiedent|ucrain)",
    "digitale":     r"\b(digitale|digital|informatic|tecnologia|software|ict)\b",
    "ricerca":      r"\b(ricerca|scientific|innovazion)\b",
    "musica":       r"\b(music|orchestra|coro|banda|filarmonic|canto)\b",
    "volontariato": r"\b(volontariato|volontari|solidarietà)\b",
    "animali":      r"\b(animali|cinofil|pet|canile|rifugio|protezione animali)\b",
    "premi":        r"\b(premio|premi|prize|concorso|challenge)\b",
}

def get_pattern_from_tags(tags):
    """Costruisce pattern regexp combinato dai tag del bando.
    
    Usa tag specifici se presenti, altrimenti ricade sui generici.
    """
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

def extract_tags_from_text(text):
    """NLP leggero: estrae tag dal testo usando TEXT_KEYWORDS."""
    text_lower = text.lower()
    found = []
    for tag, pattern in TEXT_KEYWORDS.items():
        import re
        if re.search(pattern, text_lower):
            found.append(tag)
    return list(set(found))
