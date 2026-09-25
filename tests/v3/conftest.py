from __future__ import annotations

from collections.abc import Iterator

import pytest

from agentwatch import instrument as aw
from agentwatch.runtime.engine import Engine
from agentwatch.sensors.base import ListSink
from agentwatch.storage.store import Store


@pytest.fixture
def store(tmp_path) -> Iterator[Store]:
    s = Store(f"sqlite:///{(tmp_path / 'aw.db').as_posix()}")
    yield s
    s.close()


@pytest.fixture
def engine(store: Store) -> Engine:
    return Engine(store)


@pytest.fixture
def sink() -> Iterator[ListSink]:
    s = ListSink()
    aw.configure(s)
    yield s
    aw.configure(None)
