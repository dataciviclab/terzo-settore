import duckdb
import pytest


@pytest.fixture(scope="session")
def con():
    c = duckdb.connect()
    yield c
    c.close()
