# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# see https://github.com/conda/conda/blob/c2fd056e93341a20ef7ffc33215f8aa2eb302f1d/tests/http_test_server.py

from __future__ import annotations

import argparse
import contextlib
import http.server
import queue
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import ConfigDict

from conda_anaconda_tos.console.mappers import timestamp_mapping
from conda_anaconda_tos.models import RemoteToSMetadata
from conda_anaconda_tos.remote import ENDPOINT

if TYPE_CHECKING:
    import os
    from collections.abc import Iterator

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CHANNEL_DIR = DATA_DIR / "sample_channel"


def run_test_server(
    directory: str | os.PathLike | Path,
    metadata: RemoteToSMetadata | str | None,
    port: int = 0,
) -> http.server.ThreadingHTTPServer:
    """
    Run a test server on a random port. Inspect returned server to get port,
    shutdown etc.
    """

    class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):  # noqa: ANN101, ANN202, N802
            if metadata and self.path.startswith(f"/{ENDPOINT}"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if isinstance(metadata, RemoteToSMetadata):
                    self.wfile.write(metadata.model_dump_json().encode())
                else:
                    self.wfile.write(metadata.encode())
            else:
                super().do_GET()

    class CustomHTTPServer(http.server.ThreadingHTTPServer):
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
        with CustomHTTPServer(("127.0.0.1", port), CustomRequestHandler) as http:
            queue.put(http)
            http.serve_forever()

    started: queue.Queue[http.server.ThreadingHTTPServer] = queue.Queue()

    threading.Thread(target=start_server, args=(started,), daemon=True).start()

    return started.get(timeout=1)


class MutableToSMetadata(RemoteToSMetadata):
    model_config = ConfigDict(frozen=False)


def generate_metadata() -> RemoteToSMetadata:
    return MutableToSMetadata(
        version=datetime.now(tz=timezone.utc),
        text=f"ToS Text\n\n{uuid4().hex}",
        support="support.com",
    )


@contextlib.contextmanager
def serve_channel(
    path: Path,
    metadata: RemoteToSMetadata | str | None,
    port: int = 0,
) -> Iterator[str]:
    http = run_test_server(path, metadata, port)
    host, port = http.server_address
    if isinstance(host, bytes):
        host = host.decode()
    host = f"[{host}]" if ":" in host else host
    yield f"http://{host}:{port}"
    http.shutdown()


if __name__ == "__main__":
    # demo server for testing purposes
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0, help="Port to serve on.")
    action_mutex = parser.add_mutually_exclusive_group()
    action_mutex.add_argument(
        "--tos",
        action="store_true",
        help="Serve the sample channel with a `tos.json` endpoint.",
    )
    action_mutex.add_argument(
        "--invalid-json",
        action="store_true",
        help="Serve the sample channel with an invalid JSON `tos.json` endpoint.",
    )
    action_mutex.add_argument(
        "--invalid-schema",
        action="store_true",
        help="Serve the sample channel with an invalid schema `tos.json` endpoint.",
    )
    args = parser.parse_args()

    metadata: RemoteToSMetadata | str | None
    if args.tos:
        with serve_channel(
            SAMPLE_CHANNEL_DIR, metadata := generate_metadata(), args.port
        ) as url:
            print(f"Serving HTTP at {url}...")
            while not input(
                f"Current ToS version: {timestamp_mapping(metadata.version)}\n"
                f"Press Enter to increment ToS version, Ctrl-C to exit."
            ):
                metadata.version = datetime.now(tz=timezone.utc)
    else:
        metadata = None
        if args.invalid_json:
            metadata = "?"  # not JSON
        elif args.invalid_schema:
            metadata = "{'version': null}"  # missing keys and invalid value
        with serve_channel(SAMPLE_CHANNEL_DIR, metadata, args.port) as url:
            print(f"Serving HTTP at {url}...")
            input("Press Enter or Ctrl-C to exit.")
