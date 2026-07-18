"""Pattern di matching e NLP: unica fonte di verità per scan_completo e segnale."""

import unicodedata

TAG_PATTERN = {
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

GENERIC_TAGS = {"lavoro", "inclusione", "ricerca", "giovani", "educazione", "salute"}

# Mappa tag → sezioni RUNTS pertinenti
# Ogni tag del bando mappa a zero o più sezioni. Se un ETS appartiene
# a una sezione mappata, riceve un bonus di score (match per sezione).
# Sezione residuale "ALTRI ENTI DEL TERZO SETTORE": categoria generica che
# raccoglie associazioni non classificate come ODV/APS, fondazioni, enti vari.
# Include ETS di grandi dimensioni (Save the Children, Fondazione Progetto Arca,
# Fondazione Difesa Fanciulli...) invisibili al matching senza questo gate.
SECTION_TAG_MAP = {
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
    "formazione":           ["IMPRESI SOCIALI",
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

# Mappa regione → province (sigla)
REGION_PROVINCES = {
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

# Tutte le province del Mezzogiorno (Abruzzo + Sud)
MEZZOGIORNO_PROVINCES = (
    REGION_PROVINCES["Abruzzo"] + REGION_PROVINCES["Basilicata"]
    + REGION_PROVINCES["Calabria"] + REGION_PROVINCES["Campania"]
    + REGION_PROVINCES["Molise"] + REGION_PROVINCES["Puglia"]
    + REGION_PROVINCES["Sardegna"] + REGION_PROVINCES["Sicilia"]
)

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


def get_sections_from_tags(tags):
    """Restituisce le sezioni RUNTS pertinenti per i tag del bando.
    
        Usato come bonus di score: un ETS con sezione pertinente
        riceve punti extra anche senza match di denominazione.
    """
    tags_lower = set(t.lower().strip() for t in tags if t and t.strip())
    sections = set()
    for tag, sezioni in SECTION_TAG_MAP.items():
        if tag in tags_lower:
            sections.update(sezioni)
    return sorted(sections)


def get_province_filter(territorio):
    """Converte territorio (lista di stringhe) in lista di province filtro.
    
        Restituisce [] se nessun filtro da applicare (nazionale/europa/estero).
    """
    if not territorio:
        return []
    
    province_filtro = []
    for t in territorio:
        t_clean = t.strip().lower()
        # Salta generici
        if t_clean in ("nazionale", "nazionale/da verificare", "europa", "locale", "regionale"):
            continue
        if t_clean in ("ucraina", "libia", "mediterraneo"):
            continue
        
        # Mezzogiorno → tutte le province del Sud
        if t_clean == "mezzogiorno":
            province_filtro.extend(MEZZOGIORNO_PROVINCES)
            continue
        
        # Regione italiana → province corrispondenti
        for reg_name, provinces in REGION_PROVINCES.items():
            if t_clean == reg_name.lower():
                province_filtro.extend(provinces)
                break
    
    return list(set(province_filtro))


def normalize_comune(s: str) -> str:
    """Normalizza nome comune per match: ASCII, uppercase, no apostrofi/trattini.
    
    Stessa logica di cruscotto-italia/etl/sources/runts.py.
    Gestisce bilingui ('/' mantiene solo IT), accenti (NFD+ASCII strip),
    apostrofi dritti e tipografici, trattini.
    """
    if not s:
        return ""
    s = s.split("/")[0]  # Bilingui: keep Italian first
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    s = s.replace("'", "").replace("\u2019", "")  # apostrofi dritti e tipografici
    s = s.replace("-", " ")
    return " ".join(s.upper().split())


# Mappa comuni con nomi anomali nel RUNTS/ETS rispetto all'anagrafe ISTAT.
# Compilata da cruscotto-italia (SPECIAL_ACI + PNRR_SPECIAL_NAMES + RUNTS_EXTRA_ALIASES).
# Chiave: nome normalizzato (via normalize_comune). Valore: codice ISTAT.
SPECIAL_COMUNI: dict[str, str] = {
    # --- Bilingui Alto Adige (RUNTS scrive solo italiano, bundle ha "X/Y") ---
    "BOLZANO":                  "021008",  # Bolzano/Bozen
    "MERANO":                   "021051",  # Merano/Meran
    "BRESSANONE":               "021011",  # Bressanone/Brixen
    "BRUNICO":                  "021013",  # Brunico/Bruneck
    "LAIVES":                   "021040",  # Laives/Leifers
    "VIPITENO":                 "021115",  # Vipiteno/Sterzing
    "MONTAGNA":                 "021053",  # Montagna sulla Strada del Vino/Montan (BZ)
    "SALORNO":                  "021076",  # Salorno sulla Strada del Vino (BZ)
    "DUINO AURISINA":           "032001",  # Duino-Aurisina/Devin Nabrezina (TS)
    "CHIENES":                  "021021",  # Chienes/Kiens  (da PNRR: "CHIENES GEMEINDE KIENS")
    "NOVA PONENTE":             "021060",  # Nova Ponente/Deutschnofen
    "SAN GIOVANNI DI FASSA":    "022250",  # Sen Jan di Fassa (TN, fus. 2018)
    # --- Bilingui FVG ---
    "DOBERDO DEL LAGO":         "031003",  # Doberdo del Lago-Doberdob
    "SAN DORLIGO DELLA VALLE":  "032004",  # San Dorligo della Valle-Dolina
    "SAN FLORIANO DEL COLLIO":  "031019",  # San Floriano del Collio-Steverjan
    "MONRUPINO":                "032002",  # Monrupino-Repentabor
    "SGONICO":                  "032005",  # Sgonico-Zgonik
    "SAVOGNA DISONZO":          "031022",  # Savogna d'Isonzo-Sovodnje ob Soci
    # --- Preposizioni e forme diverse ---
    "REGGIO CALABRIA":          "080063",  # Reggio di Calabria
    "REGGIO EMILIA":            "035033",  # Reggio nell'Emilia
    "CASSANO ALLO IONIO":       "078029",  # Cassano all'Ionio
    "CASTELNUOVO VAL DI CECINA": "050011", # Castelnuovo di Val di Cecina (PI)
    "CASTELNOVO NE MONTI":      "035016",  # Castelnovo ne' Monti (RE)
    "BARBERINO VAL D ELSA":     "048054",  # -> Barberino Tavarnelle (FI, fus. 2019)
    "CAPACCIO":                 "065025",  # Capaccio Paestum (SA, rinom. 2016)
    "SANNICANDRO GARGANICO":    "071049",  # San Nicandro Garganico (FG)
    "PUEGNAGO":                 "017158",  # Puegnago del Garda (BS, rinom.)
    "PUEGNAGO SUL GARDA":       "017158",  # Puegnago del Garda (BS)
    "CASSANO ALLO IONIO":       "078029",  # Cassano all'Ionio (ridondante, OK)
    # --- Bilingui FVG e fusioni FVG ---
    "TERZO DI AQUILEIA":        "030120",  # Terzo d'Aquileia (UD)
    "FIUMICELLO":               "030190",  # -> Fiumicello Villa Vicentina (UD, fus. 2018)
    "VALVASONE":                "093053",  # -> Valvasone Arzene (PN, fus. 2015)
    "REANA DEL ROIALE":         "030090",  # Reana del Rojale (UD)
    # --- Fusioni Trentino ---
    "TAIO":                     "022230",  # -> Predaia (TN, fus. 2015)
    "TUENNO":                   "022230",  # -> Predaia (TN, fus. 2015)
    "CEMBRA":                   "022241",  # -> Cembra Lisignago (TN, fus. 2016)
    "ZAMBANA":                  "022167",  # -> San Michele all'Adige (TN, fus. 2018)
    "MOLINA DI LEDRO":          "022229",  # -> Ledro (TN, fus. 2010)
    "SAN LORENZO IN BANALE":    "022231",  # -> San Lorenzo Dorsino (TN, fus. 2015)
    "SPERA":                    "022240",  # -> Castel Ivano (TN, fus. 2016)
    "BREZ":                     "022253",  # -> Novella (TN, 2020)
    "CAGNO":                    "022253",  # -> Novella (TN, 2020)
    "CLOZ":                     "022253",  # -> Novella (TN, 2020)
    "REVO":                     "022253",  # -> Novella (TN, 2020)
    "ROMALLO":                  "022253",  # -> Novella (TN, 2020)
    "CARANO":                   "022254",  # -> Ville di Fiemme (TN, 2020)
    "DAIANO":                   "022254",  # -> Ville di Fiemme (TN, 2020)
    "VARENA":                   "022254",  # -> Ville di Fiemme (TN, 2020)
    "CASTELFONDO":              "022252",  # -> Borgo d'Anaunia (TN, 2020)
    "FONDO":                    "022252",  # -> Borgo d'Anaunia (TN, 2020)
    "MALOSCO":                  "022252",  # -> Borgo d'Anaunia (TN, 2020)
    "FAEDO":                    "022167",  # -> San Michele all'Adige (TN, 2020)
    # --- TN forme troncate ---
    "PRIMIERO SAN MARTINO DI CASTRO": "022245",  # Primiero S.M. di Castrozza (RUNTS truncated)
    # --- BZ forme troncate ---
    "CORTACCIA SULLA STRADA DEL VIN": "021023",  # Cortaccia s.S.d.V./Kurtatsch (RUNTS truncated)
    # --- Fusioni Piemonte ---
    "MONTEMAGNO":               "005077",  # Montemagno Monferrato (AT)
    "CASORZO":                  "005020",  # Casorzo Monferrato (AT, 2023)
    "GRANA":                    "005056",  # Grana Monferrato (AT, 2023)
    "MORANSENGO":               "005122",  # -> Moransengo-Tonengo (AT, 2023)
    "TONENGO":                  "005122",  # -> Moransengo-Tonengo (AT, 2023)
    "CASTELLINALDO":            "004051",  # Castellinaldo d'Alba (CN)
    "CERESOLE D ALBA":          "004062",  # Ceresole Alba (CN)
    "PECCO":                    "001318",  # -> Valchiusa (TO, fus. 2019)
    # --- Fusioni Veneto ---
    "CRESPANO DEL GRAPPA":      "026096",  # -> Pieve del Grappa (TV, fus. 2019)
    "QUERO VAS":                "025075",  # -> Setteville (BL, 2024)
    "ALANO DI PIAVE":           "025075",  # -> Setteville (BL, 2024)
    "VIGHIZZOLO DESTE":         "028037",  # -> Este (PD, fus. 2024)
    "CARCERI":                  "028107",  # -> Borgo Veneto (PD, 2018)
    # --- Fusioni Lombardia ---
    "BREMBILLA":                "016253",  # -> Val Brembilla (BG, fus. 2014)
    "VALLE MOSSO":              "096088",  # -> Valdilana (BI, fus. 2019)
    "TRIVERO":                  "096088",  # -> Valdilana (BI, fus. 2019)
    "SOPRANA":                  "096088",  # -> Valdilana (BI, fus. 2019)
    "CAVALLASCA":               "013206",  # -> San Fermo della Battaglia (CO, fus. 2017)
    "LENNO":                    "013252",  # -> Tremezzina (CO, fus. 2014)
    "MACCAGNO":                 "012142",  # -> Maccagno con Pino e Veddasca (VA)
    "SAN FEDELE INTELVI":       "013254",  # -> Centro Valle Intelvi (CO, fus. 2017)
    "VERMEZZO":                 "015251",  # -> Vermezzo con Zelo (MI, fus. 2019)
    "RUINO":                    "018193",  # -> Colli Verdi (PV, fus. 2019)
    "RONAGO":                   "013256",  # -> Uggiate con Ronago (CO, 2024)
    "UGGIATE TREVANO":          "013256",  # -> Uggiate con Ronago (CO, 2024)
    "BREGANO":                  "012144",  # -> Bardello con Malgesso e Bregano (VA, 2024)
    "BARDELLO":                 "012144",  # -> Bardello con Malgesso e Bregano (VA, 2024)
    "MALGESSO":                 "012144",  # -> Bardello con Malgesso e Bregano (VA, 2024)
    "ALBAREDO ARNABOLDI":       "018026",  # -> Campospinoso Albaredo (PV, 2024)
    "CAMPOSPINOSO":             "018026",  # -> Campospinoso Albaredo (PV, 2024)
    "GAMBUGLIANO":              "024128",  # -> Sovizzo (VI, 2024)
    # --- Veneto ---
    "MEL":                      "025074",  # -> Borgo Valbelluna (BL, fus. 2019)
    "COSTERMANO":               "023030",  # Costermano sul Garda (VR, rinom. 2017)
    # --- Fusioni Toscana ---
    "FIGLINE VALDARNO":         "048052",  # -> Figline e Incisa Valdarno (FI, fus. 2014)
    "PERGINE VALDARNO":         "051042",  # -> Laterina Pergine Valdarno (AR, fus. 2018)
    "LATERINA":                 "051042",  # -> Laterina Pergine Valdarno (AR, fus. 2018)
    "SCARPERIA":                "048053",  # -> Scarperia e San Piero (FI, fus. 2014)
    "PIAN DI SCO":              "051040",  # -> Castelfranco Piandisco (AR, fus. 2014)
    "RIO MARINA":               "049021",  # -> Rio (LI, fus. 2018)
    "VERGEMOLI":                "046036",  # -> Fabbriche di Vergemoli (LU, fus. 2014)
    "GIUNCUGNANO":              "046037",  # -> Sillano Giuncugnano (LU, fus. 2015)
    "SAN MARCELLO PISTOIESE":   "047024",  # -> San Marcello Piteglio (PT, fus. 2017)
    "CASCIANA TERME":           "050040",  # -> Casciana Terme Lari (PI, fus. 2014)
    "CRESPINA":                 "050041",  # -> Crespina Lorenzana (PI, fus. 2014)
    # --- Emilia-Romagna + Marche ---
    "SORBOLO":                  "034051",  # -> Sorbolo Mezzani (PR, fus. 2019)
    "ZIBELLO":                  "034050",  # -> Polesine Zibello (PR, fus. 2016)
    "MONTESCUDO":               "099029",  # -> Montescudo-Monte Colombo (RN, fus. 2016)
    "SASSOCORVARO":             "041071",  # -> Sassocorvaro Auditore (PU, fus. 2019)
    "MONTECICCARDO":            "041044",  # -> Pesaro (PU, 2024)
    "POPOLI":                   "068033",  # -> Popoli Terme (PE, 2024)
    "PIEVEBOVIGLIANA":          "043058",  # -> Valfornace (MC, fus. 2017)
    # --- Campania/Calabria/Puglia ---
    "MONTORO INFERIORE":        "064121",  # -> Montoro (AV, fus. 2013)
    "SANT ANDREA APOSTOLO DELLO ION": "079118",  # Sant'Andrea Apostolo dello Ionio (CZ, trunc.)
    "PRESICCE":                 "075098",  # -> Presicce-Acquarica (LE, fus. 2019)
    "CORIGLIANO CALABRO":       "078157",  # -> Corigliano-Rossano (CS, fus. 2018)
    "PEDACE":                   "078156",  # -> Casali del Manco (CS, fus. 2017)
    "VENDROGNO":                "097008",  # -> Bellano (LC, fus. 2018)
    # --- Sicilia / Sardegna ---
    "CALATAFIMI":               "081003",  # Calatafimi-Segesta (TP)
    "RACCUIA":                  "083069",  # Raccuja (ME) -- RUNTS con I, bundle con J
    "NIZZA SICILIA":            "083061",  # Nizza di Sicilia (ME)
    "BARISARDO":                "091005",  # Bari Sardo (NU)
    "IERZU":                    "091035",  # Jerzu (NU) -- RUNTS con I, bundle con J
    # --- Lombardia/PC ---
    "PECORARA":                 "033049",  # -> Alta Val Tidone (PC, fus. 2018)
    # --- VCO / VI ---
    "FALMENTA":                 "103079",  # -> Valle Cannobina (VB, fus. 2019)
    "MOLVENA":                  "024126",  # -> Colceresa (VI, fus. 2019)
    # --- Roma ---
    "ROMA CAPITALE":            "058091",
    "COMUNE DI ROMA":           "058091",
    # --- Casi vari ---
    "MONTORO SUPERIORE":        "064121",  # -> Montoro (AV, fus. 2013)
    "VIRGILIO":                 "020071",  # -> Borgo Virgilio (MN, fus. 2014)
    "VILLA POMA":               "020072",  # -> Borgo Mantovano (MN, fus. 2017)
    "FELONICA":                 "020061",  # -> Sermide e Felonica (MN, fus. 2017)
    "CARBONARA DI PO":          "020072",  # -> Borgo Mantovano (MN, fus. 2017)
    "DRIZZONA":                 "019116",  # -> Piadena Drizzona (CR, fus. 2019)
    "PIADENA":                  "019116",  # -> Piadena Drizzona (CR, fus. 2019)
    "MIGLIARO":                 "038027",  # -> Fiscaglia (FE, fus. 2014)
    "MIGLIARINO":               "038027",  # -> Fiscaglia (FE, fus. 2014)
}
