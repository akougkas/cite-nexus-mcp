import json
import socket
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def records():
    return json.loads((FIXTURES / "records.json").read_text())


@pytest.fixture
def arxiv_xml():
    return (FIXTURES / "arxiv.xml").read_bytes()


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    original = socket.socket.connect

    def connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("Tests must not contact external services")
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
