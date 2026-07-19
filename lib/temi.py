"""Unico dizionario keyword → tag tematici.

Usato da:
- aggregatori/ (NLP sui testi dei bandi)
- scripts/build_unified_ets.py (estrazione temi da denominazione ETS + oggetti ANAC)
- radar/core.py (matching: temi_ets matcha tag del bando)

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
}

# Compila i pattern
TEMA_REGEX = {tag: re.compile(p, re.IGNORECASE) for tag, p in TEMA_PATTERN.items()}


def estrai_temi(testo: str) -> list[str]:
    """Estrae tag tematici da un testo."""
    if not testo:
        return []
    return [tag for tag, regex in TEMA_REGEX.items() if regex.search(testo)]


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
    """Restituisce le sezioni RUNTS pertinenti per una lista di tag."""
    viste: set[str] = set()
    risultato: list[str] = []
    for t in tags:
        t_clean = t.strip().lower()
        for s in SEZIONI_PER_TAG.get(t_clean, []):
            if s not in viste:
                viste.add(s)
                risultato.append(s)
    return risultato
