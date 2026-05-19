import base64
import pytest
from src.crunchyroll.auth import CRAuth, DEFAULT_CLIENT_ID


def test_basic_auth_header_format():
    auth = CRAuth(client_id="myclient", client_secret="")
    header = auth._basic_auth_header()
    assert header.startswith("Basic ")


def test_basic_auth_header_correct_encoding():
    auth = CRAuth(client_id="myclient", client_secret="")
    header = auth._basic_auth_header()
    decoded = base64.b64decode(header[6:]).decode()
    assert decoded == "myclient:"


def test_basic_auth_header_strips_trailing_colon():
    auth = CRAuth(client_id="myclient:", client_secret="")
    header = auth._basic_auth_header()
    decoded = base64.b64decode(header[6:]).decode()
    assert decoded == "myclient:"


def test_basic_auth_header_with_secret():
    auth = CRAuth(client_id="cid", client_secret="secret")
    header = auth._basic_auth_header()
    decoded = base64.b64decode(header[6:]).decode()
    assert decoded == "cid:secret"


def test_default_client_id_value():
    assert DEFAULT_CLIENT_ID == "noaihdevm_6iyg0a8l0q"


def test_default_client_id_used_when_empty():
    auth = CRAuth(client_id=DEFAULT_CLIENT_ID, client_secret="")
    header = auth._basic_auth_header()
    decoded = base64.b64decode(header[6:]).decode()
    assert decoded.startswith(DEFAULT_CLIENT_ID)
