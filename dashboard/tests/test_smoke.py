"""Smoke test — verifica che tutte le pagine siano syntatticamente valide."""

import py_compile
from pathlib import Path

PAGES_DIR = Path(__file__).parent.parent / "pages"


def test_all_pages_compile():
    """Ogni pagina deve essere syntatticamente corretta."""
    errors = []
    for page in sorted(PAGES_DIR.glob("*.py")):
        try:
            py_compile.compile(str(page), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(str(e))
    assert not errors, "Errori di sintassi:\n" + "\n".join(errors)
