"""Render markdown: vista → report .md (formato identico al pre-refactor)."""

from datetime import datetime

from lib.format import fmt_euro, fmt_tags, fmt_text


def _scrivi(lines, s=""):
    lines.append(s)


# ── Segnale territoriale ────────────────────────────────────────────

def render_segnale(vista):
    out = []
    titolo = vista["comune"] or vista["territorio"]
    generato = datetime.fromisoformat(vista["generato"]).strftime("%d/%m/%Y %H:%M")

    _scrivi(out, f"# 📡 Segnali — {titolo}")
    _scrivi(out, f"Generato: {generato}")
    _scrivi(out, "")

    # 1. ETS Landscape
    _scrivi(out, "## 1. 🏛️  ETS sul territorio")
    _scrivi(out, "")
    _scrivi(out, f"**{vista['ets_landscape']['tot']} ETS** totali.")
    _scrivi(out, "")
    for label, key in (("Per capacità:", "per_capacita"), ("Per tipologia:", "per_tipologia")):
        items = vista["ets_landscape"][key]
        if items:
            _scrivi(out, f"**{label}**")
            for it in items:
                _scrivi(out, f"  · {it['grp']}: {it['n']}")
            _scrivi(out, "")

    # 2. Bandi con match locale
    _scrivi(out, "## 2. 📋 Bandi con match locale")
    _scrivi(out, "")
    if vista["bandi_locali"]:
        for b in vista["bandi_locali"]:
            _scrivi(out, f"### {b['urgenza']} {b['titolo'][:80]}")
            _scrivi(out, f"- **Scadenza**: {b['scadenza']} ({b['gg']} giorni)")
            _scrivi(out, f"- **Ente**: {b['ente']}")
            _scrivi(out, f"- **Tag**: {fmt_tags(b['tags'])}")
            _scrivi(out, "")
            for c in b["candidati"]:
                cap = c.get("capacita", "?")
                _scrivi(out, f"  · **{cap}** {c['denominazione'][:50]} "
                       f"— {fmt_text(c.get('comune'), '')} — score {int(c['score'] or 0)}, "
                       f"{c['motivo']} — 5x1000: {fmt_euro(c.get('importo_5x1000_2025'))}")
            if b["extra_candidati"]:
                _scrivi(out, f"  *...e altri {b['extra_candidati']} candidati*")
            _scrivi(out, "")
    else:
        _scrivi(out, "_Nessun bando con match locale._")
        _scrivi(out, "")

    # 3. Contesto sociale
    _scrivi(out, "## 3. 📊 Contesto sociale")
    _scrivi(out, "")
    cont = vista["contesto"]
    _scrivi(out, f"_{cont['etichetta']} — media ponderata per popolazione._")
    _scrivi(out, "")
    if cont.get("reddito") is not None and cont.get("anno_reddito") is not None:
        _scrivi(out, f"- **Reddito pro-capite** ({int(cont['anno_reddito'])}): €{int(cont['reddito']):,}")
    if cont.get("rd_pct") is not None:
        _scrivi(out, f"- **RdC/PdC takeup** (2020): {cont['rd_pct']:.1f}%")
    _scrivi(out, "")

    # 4. ETS con appalti riservati
    if vista["ets_riservati"]:
        _scrivi(out, "## 4. 📋 ETS con appalti riservati")
        _scrivi(out, "")
        for r in vista["ets_riservati"]:
            pnrr = f" — PNRR: {r['appalti_pnrr']}" if r["appalti_pnrr"] > 0 else ""
            _scrivi(out, f"  · **{r['denominazione'][:50]}** — {r['comune']} — {r['appalti_riservati']} riservati{pnrr}")
        _scrivi(out, "")

    # 5. ETS con immobili pubblici
    if vista["ets_immobili"]:
        _scrivi(out, "## 5. 🏠 ETS con immobili pubblici")
        _scrivi(out, "")
        for r in vista["ets_immobili"]:
            can = f" — €{float(r['canone']):,.0f}/anno" if r["canone"] > 0 else " — gratuito"
            _scrivi(out, f"  · **{r['denominazione'][:50]}** — {r['comune']} — {r['patrimonio_immobili']} immobili{can}")
        _scrivi(out, "")

    # 6. Top ETS per capacità progettuale
    _scrivi(out, "## 6. 🏆 Top ETS per capacità progettuale")
    _scrivi(out, "")
    for r in vista["top_ets"]:
        _scrivi(out, f"  · **{r['capacita']}** {r['denominazione'][:50]} "
               f"— {r['comune']} — 5x1000: {fmt_euro(r.get('importo_5x1000_2025'))}")
    _scrivi(out, "")

    # 6b. ETS con appalti pubblici (solo comune)
    if vista["comune"]:
        _scrivi(out, "## 6. 📊 ETS con appalti pubblici (ANAC)")
        _scrivi(out, "")
        if vista["ets_appalti"]:
            for r in vista["ets_appalti"]:
                imp = f"€{float(r['importo']):,.0f}" if r["importo"] and float(r["importo"]) > 0 else "-"
                _scrivi(out, f"  · **{r['denominazione'][:45]}** [{r['capacita']}] — appalti: {imp}")
        else:
            _scrivi(out, "_Nessun ETS con appalti pubblici._")
        _scrivi(out, "")

        # 7. Gap nei comuni limitrofi
        _scrivi(out, "## 7. 📍 Gap nei comuni limitrofi")
        _scrivi(out, "")
        if vista["gap_limitrofi"]:
            for r in vista["gap_limitrofi"]:
                s = r["segnale"] or ""
                _scrivi(out, f"  · **{r['comune'][:20]}** ({r['provincia']}) "
                       f"— {r['ets_tot']} ETS, RdC {r['rd_pct']}%, reddito €{int(r['reddito']):,} {s}")
        else:
            _scrivi(out, "_Tutti i comuni limitrofi hanno ETS sufficienti._")

    return "\n".join(out)


# ── Radar latest ────────────────────────────────────────────────────

def render_latest(vista):
    out = []
    oggi = datetime.fromisoformat(vista["generato"]).strftime("%d/%m/%Y")

    _scrivi(out, f"# 📡 Radar bandi — {oggi}")
    _scrivi(out, "")
    _scrivi(out, f"Bandi operativi in scadenza nei prossimi {vista['giorni']}gg: **{vista['tot_bandi']}**")
    if vista["territorio"]:
        _scrivi(out, f"Filtro territorio: **{vista['territorio']}**")
    _scrivi(out, "")

    for b in vista["bandi"]:
        _scrivi(out, f"## {b['titolo'][:80]}")
        _scrivi(out, f"- **Ente**: {b['ente'] or '?'}")
        _scrivi(out, f"- **Scadenza**: {b['scadenza']} ({b['gg']} giorni)")
        _scrivi(out, f"- **Link**: {b.get('url', '?')}")
        _scrivi(out, f"- **Stato**: {b['status']}")
        _scrivi(out, f"- **Territorio**: {', '.join(b['territorio'])}")
        _scrivi(out, f"- **Tag**: {fmt_tags(b['tags'])}")
        _scrivi(out, "")
        for c in b["candidati"]:
            cap = c.get("capacita", c.get("capacita_progettuale", "?"))
            _scrivi(out, f"  · **{cap}** {c['denominazione'][:55]} "
                   f"— {fmt_text(c.get('comune'), '')} ({fmt_text(c.get('provincia'))}) "
                   f"— score {int(c.get('score', 0))}, {c['motivo']} "
                   f"— 5x1000: {fmt_euro(c.get('importo_5x1000_2025'))}")
        _scrivi(out, "")

    if vista["top_budget"]:
        _scrivi(out, "---")
        _scrivi(out, "## TOP OPPORTUNITÀ (bandi con budget)")
        _scrivi(out, "")
        _scrivi(out, "| Budget | GG | Ente | Bando | Link |")
        _scrivi(out, "|--------|----|------|-------|------|")
        for r in vista["top_budget"]:
            urg = " (🔴)" if r["gg"] <= 30 else (" (🟡)" if r["gg"] <= 60 else "")
            _scrivi(out, f"| {fmt_euro(r.get('budget'))}{urg} | {r['gg']}gg "
                   f"| {fmt_text(r['ente'], '?')[:30]} | {r['titolo'][:40]} | [link]({r.get('url', '?')[:50]}) |")
        _scrivi(out, "")

    _scrivi(out, "---")
    _scrivi(out, "## Gap territoriali (appalti ANAC + ETS + contesto sociale)")
    _scrivi(out, "")
    _scrivi(out, "| Comune | Prov | Appalti riservati | ETS ok | RdC% | Reddito | Segnale |")
    _scrivi(out, "|--------|------|------------------|--------|------|---------|---------|")
    for g in vista["gap"]:
        segnale = g.get("gap_segnale", "") or ""
        _scrivi(out, f"| {g['denominazione'][:20]} | {g['sigla_provincia']} "
               f"| {g['appalti']} app. €{g['importo_M']}M | {g['ets_ok']} | {g['rd_pct']}% "
               f"| €{g['reddito']:,} | {segnale} |")
    _scrivi(out, "")
    _scrivi(out, f"_Vista latest da scan condiviso: {vista['tot_bandi']} bandi operativi matchati._")
    return "\n".join(out)


# ── Radar completo ──────────────────────────────────────────────────

def render_completo(scan):
    bandi = scan["bandi"]
    resultados = scan["resultados"]
    sin_match = scan["sin_match"]
    skipped = scan["skipped"]
    stats_ets = scan["stats_ets"]

    lines = []
    _scrivi(lines, "# 📡 Radar Completo — Tutti i Bandi vs ETS")
    _scrivi(lines, f"Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    _scrivi(lines, "")
    _scrivi(lines, f"**{len(resultados)}** bandi operativi con ETS candidabili  |  "
           f"**{len(sin_match)}** operativi senza match  |  "
           f"**{len(skipped)}** esclusi  |  **{len(stats_ets)}** ETS unici coinvolti")
    _scrivi(lines, "")
    _scrivi(lines, "---")
    _scrivi(lines, "")

    urgenti = [r for r in resultados if r["gg"] <= 30]
    if urgenti:
        _scrivi(lines, "## 🔴 Bandi urgenti (≤30gg) con ETS candidabili")
        _scrivi(lines, "")
        for r in sorted(urgenti, key=lambda x: x["gg"]):
            urgenza = "🔴" if r["gg"] <= 14 else "🟡"
            _scrivi(lines, f"### {urgenza} {r['titolo'][:80]}")
            _scrivi(lines, f"- **Scadenza**: {r['scadenza']} ({r['gg']} giorni)")
            _scrivi(lines, f"- **Ente**: {r['ente']}")
            _scrivi(lines, f"- **Stato**: {r['status']}")
            _scrivi(lines, f"- **Territorio**: {', '.join(r['territorio'])}")
            _scrivi(lines, f"- **Tag**: {fmt_tags(r['tags'])}")
            _scrivi(lines, "")
            _scrivi(lines, "| ETS | Comune | Prov | Capacità | Score | Motivo | 5x1000 2025 |")
            _scrivi(lines, "|-----|--------|------|----------|-------|--------|-------------|")
            for c in r["candidati"]:
                cinque = fmt_euro(c.get("importo_5x1000_2025"))
                comune = fmt_text(c.get("comune"), "")[:20]
                provincia = fmt_text(c.get("provincia"))
                _scrivi(lines, f"| {c['denominazione'][:45]} | {comune} | {provincia} | "
                       f"{c['capacita_progettuale']} | {int(c.get('score', 0))} | "
                       f"{fmt_match_reason_local(c)} | {cinque} |")
            _scrivi(lines, "")

    non_urgenti = [r for r in resultados if r["gg"] > 30]
    if non_urgenti:
        _scrivi(lines, "## 🟢 Bandi con ETS candidabili (>30gg)")
        _scrivi(lines, "")
        for r in sorted(non_urgenti, key=lambda x: x["gg"]):
            _scrivi(lines, f"### {r['titolo'][:80]}")
            _scrivi(lines, f"- **Scadenza**: {r['scadenza']} ({r['gg']} giorni)")
            _scrivi(lines, f"- **Ente**: {r['ente']}")
            _scrivi(lines, f"- **Stato**: {r['status']}")
            _scrivi(lines, f"- **Territorio**: {', '.join(r['territorio'])}")
            _scrivi(lines, f"- **Tag**: {fmt_tags(r['tags'])}")
            _scrivi(lines, "")
            for c in r["candidati"]:
                cinque = fmt_euro(c.get("importo_5x1000_2025"))
                comune = fmt_text(c.get("comune"), "")
                provincia = fmt_text(c.get("provincia"))
                _scrivi(lines, f"  · **{c['capacita_progettuale']}** {c['denominazione'][:50]} "
                       f"— {comune} ({provincia}) — score {int(c.get('score', 0))}, "
                       f"{fmt_match_reason_local(c)} — 5x1000: {cinque}")
            _scrivi(lines, "")

    if sin_match:
        _scrivi(lines, "---")
        _scrivi(lines, "## ⚠️ Bandi senza ETS candidabili")
        _scrivi(lines, "")
        for titolo, url, ente, scad, gg, tags, territorio, status, motivo in sorted(sin_match, key=lambda x: x[4]):
            emoji = "🔴" if gg <= 30 else "🟡" if gg <= 60 else "⚪"
            _scrivi(lines, f"- {emoji} **{titolo[:70]}** — {ente} — scad. {scad} ({gg}gg) — _{motivo}_")
            _scrivi(lines, f"  Stato: {status} | Territorio: {', '.join(territorio)} | Tag: {fmt_tags(tags)}")

    if skipped:
        _scrivi(lines, "")
        _scrivi(lines, "---")
        _scrivi(lines, "## Esclusi dal matching")
        _scrivi(lines, "")
        counts = {}
        for s in skipped:
            counts[s["status"]] = counts.get(s["status"], 0) + 1
        _scrivi(lines, ", ".join(f"**{status}**: {count}" for status, count in sorted(counts.items())))
        _scrivi(lines, "")
        for s in skipped[:20]:
            _scrivi(lines, f"- **{s['titolo'][:80]}** — {s['status']} — {s['motivo']}")

    _scrivi(lines, "")
    _scrivi(lines, "---")
    _scrivi(lines, f"_{len(bandi)} bandi processati, {len(resultados)} match trovati, "
           f"{len(sin_match)} gap operativi, {len(skipped)} esclusi._")
    return "\n".join(lines)


def fmt_match_reason_local(c):
    from lib.format import fmt_match_reason
    return fmt_match_reason(c)
