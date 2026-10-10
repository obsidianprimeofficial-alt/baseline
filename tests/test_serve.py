import http.client
import socket
import threading

import pytest

from baseline import serve
from baseline.serve import WEB, address_lines, make_server


def can_bind_ipv6_loopback() -> bool:
    """socket.has_ipv6 can be True where ::1 still cannot be bound, e.g. containers with IPv6 disabled."""
    if not socket.has_ipv6:
        return False
    try:
        with socket.socket(socket.AF_INET6) as s:
            s.bind(("::1", 0))
        return True
    except OSError:
        return False


@pytest.mark.parametrize("family, host", [
    (socket.AF_INET, "127.0.0.1"),
    pytest.param(socket.AF_INET6, "::1", marks=pytest.mark.skipif(not can_bind_ipv6_loopback(), reason="cannot bind to ::1")),
])
def test_busy_port_falls_back_to_the_next(family, host):
    with socket.socket(family) as busy:
        busy.bind((host, 0))
        busy.listen()
        taken = busy.getsockname()[1]
        server = make_server([taken, 0])  # 0 lets the system pick a free port
        try:
            assert server.server_address[1] != taken
        finally:
            server.server_close()


def test_serves_the_web_folder():
    assert (WEB / "index.html").is_file()


@pytest.mark.parametrize("lan, ip, expected", [
    (False, "192.168.1.20", ["Open http://localhost:8000"]),
    (True, "192.168.1.20", ["Open http://localhost:8000",
                            "On your phone (same wifi), open http://192.168.1.20:8000"]),
    (True, None, ["Open http://localhost:8000",
                  "On your phone (same wifi), open http://your laptop's IP:8000"]),
])
def test_printed_addresses(monkeypatch, lan, ip, expected):
    monkeypatch.setattr(serve, "lan_ip", lambda: ip)
    assert address_lines(8000, lan) == expected


def test_responses_are_never_cached():
    server = make_server([0])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)  # no proxy
        conn.request("GET", "/")
        assert conn.getresponse().getheader("Cache-Control") == "no-store"
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
