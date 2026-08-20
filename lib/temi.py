"""Unico dizionario keyword → tag tematici.

Usato da:
- match/funnel.py (motore di matching)
- match/bando.py (normalizzazione bandi)
- match/pipeline.py (orchestrazione scan)
- tests/test_match.py

Non duplicare altrove.
"""

import re

# Mappa: tag → pattern regex
# Il pattern matcha sottostringhe (no word boundary finale)
# per coprire flessioni italiane: "educativ" matcha "educativa", "educativo", "educativi"
TEMA_PATTERN: dict[str, str] = {
    "sport":                r"(sport|calcio|atletica|nuoto|pallavolo|ginnastica|basket|tennis|scherma|ciclismo|vela|canottaggio|asd|polisportiv)",
    "disabilità":           r"(disabil|handicap|anffas|down|autism|sord|paralisi|ipov|neuro|demen)",
    "minori":               r"(minori|bambin|adolescent|infanzia|nido|alunni|ragazz|children|child)",
    "giovani":              r"(giovani|gioventù|neet|studentesc|giovanile|youth|young|under\s?\d+)",
    "cultura":              r"(cultura|museo|teatro|music|biblioteca|cinema|mostra|patrimonio|creativit|artistic)",
    "ambiente":             r"(ambiente|natura|ecolog|riciclo|sostenibil|verde|rifiuti|clima|spreco|transizione ecologica|environment|greenpeace)",
    "lavoro":               r"(lavoro|formazion|impiego|occupazion|professional|orientament|parti sociali|sindac|inseriment|tirocin|work)",
    "salute":               r"(salute|sanit|medic|assistenz|domiciliar|cura|ospedal|prevenzion|benessere|sociosanit|socio sanit|health|emergency)",
    "educazione":           r"(educazion|educativ|scuola|istruzion|didattic|apprendiment|scolastic|formativo|socio educativ|education|school|learning)",
    "inclusione sociale":   r"(inclusione|integrazion|solidariet|povert|emarginazion|vulnerab|inclusion|poverty|disadvantaged)",
    "anziani":              r"(anzian|terza età|over\d+|silver)",
    "donne":                r"(donne|femminil|parità|genere|vittime|violenza|women|woman|gender)",
    "migranti":             r"(migrant|rifugiat|stranier|immigrazion|intercultur|richiedent|asilo|ucrain|refugee|asylum)",
    "digitale":             r"(digitale|digital|informatic|tecnologia|software|ict|tech|coding)",
    "volontariato":         r"(volontariato|volontari|solidarietà|odv)",
    "ricerca":              r"(ricerca|scientific|innovazion|research|innovation)",
    "musica":               r"(music|orchestra|coro|banda|filarmonic|canto)",
    "animali":              r"(animali|cinofil|pet|canile|rifugio|protezione animali)",
    "povertà educativa":    r"(povertà educativa|dispersione scolastic|abbandono scolastic)",
    "premi":                r"\b(premio|premi|prize|concorso|challenge)\b",
    "cooperazione internazionale": r"(cooperazione internazionale|cooperazione allo sviluppo|cooperazione allo sviluppo internazionale|internazionalizzazione|development cooperation)",
}

# Sinonimi: varianti non normalizzate dei tag reali → tema canonico.
# Il dizionario ha nomi canonici ("inclusione sociale"); i bandi usano
# spesso forme diverse ("inclusione", "istruzione", "scuole", "adolescenti").
TAG_SINONIMI: dict[str, str] = {
    # forme plurali / abbreviate / varianti del dizionario
    "inclusione": "inclusione sociale",
    "inclusione sociali": "inclusione sociale",
    "inclusiv": "inclusione sociale",
    "istruzione": "educazione",
    "istruzion": "educazione",
    "scuole": "educazione",
    "scuola": "educazione",
    "scolastic": "educazione",
    "adolescenti": "minori",
    "adolescent": "minori",
    "bambini": "minori",
    "infanzia": "minori",
    "pari opportunità": "donne",
    "pari opportunita": "donne",
    "genere": "donne",
    "disabilita": "disabilità",
    "handicap": "disabilità",
    "terza età": "anziani",
    "anziano": "anziani",
    "immigrazione": "migranti",
    "immigrat": "migranti",
    "rifugiati": "migranti",
    "rifugiat": "migranti",
    "stranieri": "migranti",
    "intercultura": "migranti",
    "formazione": "lavoro",
    "formazion": "lavoro",
    "impiego": "lavoro",
    "occupazione": "lavoro",
    "occupazion": "lavoro",
    "professionale": "lavoro",
    "professional": "lavoro",
    "sostenibilità": "ambiente",
    "sostenibilita": "ambiente",
    "sostenibil": "ambiente",
    "transizione ecologica": "ambiente",
    "rifiuti": "ambiente",
    "clima": "ambiente",
    "sportivo": "sport",
    "sportiva": "sport",
    "sportivi": "sport",
    "sportiv": "sport",
    "attività sportive": "sport",
    "volontari": "volontariato",
    "volontar": "volontariato",
    "ricerca scientifica": "ricerca",
    "innovazione": "ricerca",
    "innovazion": "ricerca",
    "culturale": "cultura",
    "culturali": "cultura",
    "cultura": "cultura",
    "ambiente e sostenibilità": "ambiente",
    "povertà": "inclusione sociale",
    "poverta": "inclusione sociale",
    "poveri": "inclusione sociale",
    "dispersione scolastica": "povertà educativa",
    "dispersione scolastic": "povertà educativa",
    "abbandono scolastico": "povertà educativa",
    # tag multi-parola reali dai bandi
    "obiettivi per lo sviluppo sostenibile": "cooperazione internazionale",
    "sviluppo sostenibile": "cooperazione internazionale",
    "agenda 2030": "cooperazione internazionale",
    "cooperazione allo sviluppo": "cooperazione internazionale",
    "cooperazione internazionale": "cooperazione internazionale",
    "cooperazione": "cooperazione internazionale",
    "if design": "cultura",
    "design": "cultura",
    "turismo": "cultura",
    "sviluppo economico": "lavoro",
    "sostegno alla persona": "inclusione sociale",
    "smart city": "digitale",
    "innovazione digitale": "digitale",
    "internazionalizzazione": "cultura",
    "energia": "ambiente",
    "energie rinnovabili": "ambiente",
    "montagna": "ambiente",
    "agricoltura": "agricoltura sociale",
    "famiglia": "minori",
    "premi internazionali": "premi",
    "beni confiscati": "beni confiscati",
    "in evidenza": None,
    "pnrr": None,
}
# Tag "generici": non discriminano il tema (servono come contesto, non come match)
GENERIC_TAGS = {"lavoro", "inclusione", "ricerca", "giovani", "educazione", "salute"}

# Priorità dei temi per la scelta del tema PRINCIPALE di un bando.
# I temi "forti" (attività specifica) dominano su quelli "trasversali"
# (popolazione target: minori, giovani, anziani, donne, inclusione).
# Un bando di sport per minori è PRIMA sport, poi minori.
TEMA_PRIORITA: dict[str, int] = {
    # temi forti (attività) — priorità alta
    "sport": 100,
    "disabilità": 95,
    "ambiente": 90,
    "digitale": 85,
    "cultura": 80,
    "musica": 80,
    "volontariato": 75,
    "agricoltura sociale": 75,
    "beni confiscati": 70,
    "povertà educativa": 70,
    "animali": 65,
    "ricerca": 60,
    "premi": 55,
    "cooperazione internazionale": 55,
    # temi trasversali (popolazione/contesto) — priorità bassa
    "migranti": 40,
    "lavoro": 35,
    "educazione": 30,
    "salute": 30,
    "inclusione sociale": 25,
    "donne": 25,
    "minori": 20,
    "giovani": 20,
    "anziani": 15,
}

# Compila i pattern
TEMA_REGEX = {tag: re.compile(p, re.IGNORECASE) for tag, p in TEMA_PATTERN.items()}


def normalizza_tags(tags: list[str]) -> list[str]:
    """Normalizza i tag del bando verso i nomi canonici del dizionario.

    Applica i sinonimi (es. 'inclusione' → 'inclusione sociale') e tiene i
    tag già canonici. Scarta i tag con sinonimo None (rumore: 'in evidenza').
    Rimuove i tag non riconducibili a un tema noto.
    """
    normalizzati = []
    visti = set()
    for t in tags:
        t_clean = (t or "").strip().lower()
        if not t_clean:
            continue
        canonico = TAG_SINONIMI.get(t_clean, t_clean)
        if canonico is None:
            continue  # rumore da scartare
        if canonico in TEMA_PATTERN and canonico not in visti:
            normalizzati.append(canonico)
            visti.add(canonico)
    return normalizzati


def estrai_temi(testo: str) -> list[str]:
    """Estrae tag tematici da un testo."""
    if not testo:
        return []
    return [tag for tag, regex in TEMA_REGEX.items() if regex.search(testo)]


def tema_principale(tags: list[str], testo: str | None = None) -> str | None:
    """Identifica il tema dominante del bando.

    Priorità:
    1. Il tema con priorità più alta (TEMA_PRIORITA): sport > minori,
       attività > popolazione target
    2. Se nessun tag mappato, fallback sui temi estratti dal testo
    3. None se nessun tema è identificabile
    """
    normalizzati = normalizza_tags(tags)
    if not normalizzati and testo:
        normalizzati = estrai_temi(testo)
    if not normalizzati:
        return None
    # max priorità, a parità tiene l'ordine di apparizione
    return max(normalizzati, key=lambda t: (TEMA_PRIORITA.get(t, 0), -normalizzati.index(t)))


def get_pattern_from_tags(tags, testo: str | None = None):
    """Costruisce pattern regexp combinato dai tag del bando.

    v2: normalizza i tag (sinonimi → canonici) prima di costruire il pattern,
    così 'inclusione' e 'inclusione sociale' producono lo stesso pattern.
    Se nessun tag è mappabile, estrae i temi dal testo (fallback).
    """
    normalizzati = normalizza_tags(tags)
    if not normalizzati and testo:
        normalizzati = estrai_temi(testo)
    if not normalizzati:
        return None
    specific = [t for t in normalizzati if t not in GENERIC_TAGS]
    use_tags = specific if specific else normalizzati
    parts = []
    for tag in use_tags:
        pattern = TEMA_PATTERN.get(tag)
        if pattern:
            parts.append(pattern)
    return "|".join(parts) if parts else None


# Mappa: tag → sezioni RUNTS pertinenti
# (usata dal matching per gate di sezione)
SEZIONI_PER_TAG: dict[str, list[str]] = {
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


def sezioni_per_tag(tags: list[str]) -> list[str]:
    """Restituisce le sezioni RUNTS pertinenti per una lista di tag (normalizzati)."""
    normalizzati = normalizza_tags(tags)
    viste: set[str] = set()
    risultato: list[str] = []
    for t in normalizzati:
        for s in SEZIONI_PER_TAG.get(t, []):
            if s not in viste:
                viste.add(s)
                risultato.append(s)
    return risultato
