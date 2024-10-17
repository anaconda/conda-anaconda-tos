# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import contextlib
import http.server
import queue
import shutil
import socket
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import os
    from typing import Iterator

    from pytest import TempPathFactory

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing.fixtures",
)

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CHANNEL_DIR = DATA_DIR / "sample_channel"
TOS_DIR = DATA_DIR / "tos"


# See https://github.com/conda/conda/blob/c2fd056e93341a20ef7ffc33215f8aa2eb302f1d/tests/http_test_server.py
def run_test_server(
    directory: str | os.PathLike | Path,
) -> http.server.ThreadingHTTPServer:
    """
    Run a test server on a random port. Inspect returned server to get port,
    shutdown etc.
    """

    class DualStackServer(http.server.ThreadingHTTPServer):
        daemon_threads = False  # These are per-request threads
        allow_reuse_address = True  # Good for tests
        request_queue_size = 64  # Should be more than the number of test packages

        def server_bind(self):  # noqa: ANN101, ANN202
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request, client_address):  # noqa: ANN001, ANN101, ANN202
            self.RequestHandlerClass(request, client_address, self, directory=directory)

    def start_server(queue):  # noqa: ANN001, ANN202
        with DualStackServer(
            ("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler
        ) as httpd:
            host, port = httpd.socket.getsockname()[:2]
            queue.put(httpd)
            url_host = f"[{host}]" if ":" in host else host
            print(
                f"Serving HTTP on {host} port {port} "
                f"(http://{url_host}:{port}/) ..."
            )
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received, exiting.")

    started: queue.Queue[http.server.ThreadingHTTPServer] = queue.Queue()

    threading.Thread(target=start_server, args=(started,), daemon=True).start()

    return started.get(timeout=1)


@contextlib.contextmanager
def serve_channel(path: Path) -> Iterator[str]:
    http = run_test_server(path)
    host, port = http.server_address
    if isinstance(host, bytes):
        host = host.decode()
    url_host = f"[{host}]" if ":" in host else host
    yield f"http://{url_host}:{port}"
    http.shutdown()


@pytest.fixture(scope="session")
def tos_channel(tmp_path_factory: TempPathFactory) -> Iterator[str]:
    # Copy the sample channel to a temporary directory and add ToS files
    path = tmp_path_factory.mktemp("tos_channel")
    shutil.copytree(SAMPLE_CHANNEL_DIR, path, dirs_exist_ok=True)
    shutil.copytree(TOS_DIR, path, dirs_exist_ok=True)

    with serve_channel(path) as url:
        yield url


@pytest.fixture(scope="session")
def sample_channel() -> Iterator[str]:
    # Serve the sample channel as-is
    with serve_channel(SAMPLE_CHANNEL_DIR) as url:
        yield url


@pytest.fixture(scope="session")
def tos_full_text() -> str:
    return (TOS_DIR / "tos.txt").read_text().rstrip()
