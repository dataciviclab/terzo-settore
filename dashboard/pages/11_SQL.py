"""Query SQL — usa render_sql_query() da lab_connectors."""

from pathlib import Path

from lab_connectors.duckdb.sql_page import render_sql_query
from lab_connectors.registry.client import load_registry

registry = load_registry(Path(__file__).parent.parent.parent / "registry" / "registry.json")
render_sql_query(registry=registry, prefix="terzo_settore/", default_slug="ets_unified")
