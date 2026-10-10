"""Serve web/ for the offline demo and open it in the default browser: python -m baseline.serve [--lan]"""

import argparse
import functools
import socket
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
PORTS = range(8000, 8011)


class Server(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second server bind a port that is already in use,
    # which would hide a busy port instead of falling back to the next one.
    allow_reuse_address = sys.platform != "win32"


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")  # phones must never show stale cards after an update
        super().end_headers()


def in_use(port: int) -> bool:
    """True if anything answers on this port at 127.0.0.1 or ::1, the two addresses a browser tries for
    localhost. Binding alone misses a server on [::], e.g. a leftover `python -m http.server 8000`."""
    for host in ("127.0.0.1", "::1"):
        try:
            socket.create_connection((host, port), timeout=0.3).close()
            return True
        except OSError:
            pass
    return False


def make_server(ports=PORTS, host: str = "127.0.0.1") -> Server:
    handler = functools.partial(Handler, directory=str(WEB))
    for port in ports:
        if in_use(port):
            continue
        try:
            return Server((host, port), handler)
        except OSError:
            continue
    raise SystemExit(f"Ports {ports[0]} to {ports[-1]} are all busy. Close the other server and try again.")


def lan_ip() -> str | None:
    """This laptop's address on the local network, or None. Connecting a UDP socket only asks the system
    which interface would route there; no packet is sent."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except OSError:
        return None
    return None if ip.startswith(("127.", "0.")) else ip


def address_lines(port: int, lan: bool) -> list[str]:
    lines = [f"Open http://localhost:{port}"]
    if lan:
        ip = lan_ip() or "your laptop's IP"
        lines.append(f"On your phone (same wifi), open http://{ip}:{port}")
    return lines


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m baseline.serve")
    parser.add_argument("--lan", action="store_true", help="also serve to phones on the same wifi (binds 0.0.0.0)")
    args = parser.parse_args(argv)
    server = make_server(host="0.0.0.0" if args.lan else "127.0.0.1")
    port = server.server_address[1]
    print("\n".join(address_lines(port, args.lan)), flush=True)
    webbrowser.open(f"http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
