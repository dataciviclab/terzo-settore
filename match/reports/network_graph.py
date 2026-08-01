#!/usr/bin/env python3
"""Grafo relazionale di un territorio — ETS e connessioni.

Uso:
    /home/gabry/dev/dataciviclab-workspace/.venv/bin/python3 match/reports/network_graph.py --territorio MO
    /home/gabry/dev/dataciviclab-workspace/.venv/bin/python3 match/reports/network_graph.py --territorio MO --comune Carpi
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

import duckdb
import networkx as nx
from pyvis.network import Network
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ETS_FILE = str(ROOT / "data/unified_ets.parquet")


def build_graph(territorio: str, comune: str = None, max_ets: int = 30):
    con = duckdb.connect()

    where = f"AND provincia = upper('{territorio}')"
    if comune:
        where += " AND lower(comune) = lower('" + comune + "')"

    # ETS del territorio
    ets = con.sql(f"""
        SELECT codice_fiscale, denominazione, sezione, comune, provincia,
               capacita_progettuale, numero_appalti
        FROM '{ETS_FILE}'
        WHERE 1=1 {where}
        ORDER BY numero_appalti DESC
        LIMIT {max_ets}
    """).fetchdf()

    if ets.empty:
        print(f"❌ Nessun ETS trovato per {territorio} {comune or ''}")
        return

    cfs = set(ets['codice_fiscale'])
    labels = dict(zip(ets['codice_fiscale'], ets['denominazione']))
    sezioni = dict(zip(ets['codice_fiscale'], ets['sezione']))
    appalti = dict(zip(ets['codice_fiscale'], ets['numero_appalti']))

    G = nx.Graph()

    for cf in cfs:
        G.add_node(cf)

    # Archi ATI
    ati = con.sql(f"""
        SELECT a1.codice_fiscale as cf1, a2.codice_fiscale as cf2, count(*) as peso
        FROM read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet', union_by_name=true) a1
        JOIN read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet', union_by_name=true) a2
          ON a1.cig = a2.cig AND a1.codice_fiscale < a2.codice_fiscale
        WHERE a1.codice_fiscale IN ({','.join(f"'{c}'" for c in cfs)})
          AND a2.codice_fiscale IN ({','.join(f"'{c}'" for c in cfs)})
        GROUP BY a1.codice_fiscale, a2.codice_fiscale
        HAVING count(*) >= 2
    """).fetchdf()

    for _, row in ati.iterrows():
        G.add_edge(row['cf1'], row['cf2'], weight=min(row['peso'], 10))

    # Mappa sezioni → colore
    color_map = {
        'IMPRESI SOCIALI': '#2196F3',
        'ASSOCIAZIONI DI PROMOZIONE SOCIALE': '#4CAF50',
        'ORGANIZZAZIONI DI VOLONTARIATO': '#FF9800',
        'ALTRI ENTI DEL TERZO SETTORE': '#9E9E9E',
        'ENTI FILANTROPICI': '#9C27B0',
        'SOCIETA\' DI MUTUO SOCCORSO': '#00BCD4',
    }

    colors = [color_map.get(sezioni.get(n, ''), '#cccccc') for n in G.nodes()]
    sizes = [max(50, min((appalti.get(n, 1) or 1) * 10, 500)) for n in G.nodes()]

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    pos = nx.spring_layout(G, k=2, iterations=50)

    nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=sizes, alpha=0.8)
    edges = G.edges(data=True)
    if edges:
        weights = [d['weight'] for _, _, d in edges]
        nx.draw_networkx_edges(G, pos, width=weights, alpha=0.3, edge_color='#666666')

    # Label solo per nodi con connessioni
    labels_subset = {}
    for n in G.nodes():
        if G.degree(n) > 0:
            labels_subset[n] = labels.get(n, '')[:30]
        else:
            labels_subset[n] = ''
    nx.draw_networkx_labels(G, pos, labels_subset, font_size=7)

    titolo = f"ETS {territorio}"
    if comune:
        titolo += f" — {comune}"
    ax.set_title(titolo, fontsize=14)
    ax.axis('off')

    # Legenda
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=c,
                   label=l, markersize=8)
        for l, c in color_map.items()
        if any(sezioni.get(n, '') == l for n in G.nodes())
    ]
    if legend_elements:
        ax.legend(handles=legend_elements, loc='lower right', fontsize=8)

    out_png = ROOT / f"cruscotto/network-{territorio.lower()}.png"
    fig.savefig(out_png, dpi=150, bbox_inches='tight')
    print(f"✅ Grafo statico: {out_png}")

    # Interactive HTML via pyvis
    net = Network(height="700px", width="100%", directed=False, bgcolor="#ffffff", font_color="#333333")
    net.barnes_hut(gravity=-3000, spring_strength=0.001)

    for n in G.nodes():
        label = labels.get(n, '')[:40]
        sez = sezioni.get(n, '')
        col = color_map.get(sez, '#cccccc')
        size = max(10, min((appalti.get(n, 1) or 1) * 2, 80))
        net.add_node(n, label=label, title=f"{label}\\n{sez}\\n{int(appalti.get(n, 1) or 1)} appalti",
                     color=col, size=size)

    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, value=min(d.get('weight', 1), 5), title=f"{int(d.get('weight', 1))} CIG")

    out_html = ROOT / f"cruscotto/network-{territorio.lower()}.html"
    net.save_graph(str(out_html))
    print(f"✅ Grafo interattivo: {out_html}")
    print(f"   {len(G.nodes)} ETS, {len(G.edges)} connessioni ATI")

    con.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--territorio", required=True)
    parser.add_argument("--comune")
    parser.add_argument("--max-ets", type=int, default=30)
    args = parser.parse_args()
    build_graph(args.territorio.upper(), args.comune, args.max_ets)
