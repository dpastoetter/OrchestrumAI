"""URL safety helpers used to reduce SSRF risk."""

from __future__ import annotations

import pytest

from orchestrumai.safe_url import UnsafeUrlError, validate_http_url


def test_accepts_public_https_ip() -> None:
    assert validate_http_url("https://8.8.8.8/dns") == "https://8.8.8.8/dns"


def test_rejects_metadata_ip() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_http_url("http://169.254.169.254/latest/meta-data/", allow_private=True)


def test_rejects_loopback_when_private_disallowed() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_http_url("http://127.0.0.1:8000/secret", allow_private=False)


def test_allows_loopback_when_private_allowed() -> None:
    assert validate_http_url("http://127.0.0.1:11434", allow_private=True) == "http://127.0.0.1:11434"


def test_rejects_private_lan_when_disallowed() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_http_url("http://192.168.1.1/", allow_private=False)


def test_rejects_credentials_in_url() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_http_url("https://user:pass@example.com/")


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_http_url("file:///etc/passwd")


def test_rejects_hostname_resolving_to_private(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(host, *args, **kwargs):  # noqa: ANN001
        return [(None, None, None, None, ("10.0.0.5", 0))]

    monkeypatch.setattr("orchestrumai.safe_url.socket.getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeUrlError):
        validate_http_url("http://evil.example/", allow_private=False)
