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
from itertools import repeat
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
    from typing import Any, Self, TypeAlias

    MetadataType: TypeAlias = RemoteToSMetadata | str | None

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CHANNEL_DIR = DATA_DIR / "sample_channel"


def run_test_server(
    directory: str | os.PathLike | Path,
    metadata: MetadataType | Iterator[MetadataType],
    port: int = 0,
) -> http.server.ThreadingHTTPServer:
    """
    Run a test server on a random port. Inspect returned server to get port,
    shutdown etc.
    """

    # convert single metadata to an infinite iterator
    metadatas: Iterator[MetadataType]
    if isinstance(metadata, (RemoteToSMetadata, str)) or metadata is None:
        metadatas = repeat(metadata)
    else:
        metadatas = metadata

    class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self: Self) -> None:
            if (metadata := next(metadatas)) and self.path.startswith(f"/{ENDPOINT}"):
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

        def server_bind(self: Self) -> None:
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            super().server_bind()

        def finish_request(
            self: Self,
            request: socket.socket | tuple[bytes, socket.socket],
            client_address: Any,  # noqa: ANN401
        ) -> None:
            self.RequestHandlerClass(request, client_address, self, directory=directory)  # type: ignore [call-arg]

    def start_server(queue: queue.Queue[http.server.ThreadingHTTPServer]) -> None:
        with CustomHTTPServer(("127.0.0.1", port), CustomRequestHandler) as http:
            queue.put(http)
            http.serve_forever()

    started: queue.Queue[http.server.ThreadingHTTPServer] = queue.Queue()

    threading.Thread(target=start_server, args=(started,), daemon=True).start()

    return started.get(timeout=1)


class MutableToSMetadata(RemoteToSMetadata):
    model_config = ConfigDict(frozen=False)

    def __eq__(self: Self, other: object) -> bool:
        return (
            isinstance(other, (MutableToSMetadata, RemoteToSMetadata))
            and self.model_dump() == other.model_dump()
        )


def generate_metadata() -> RemoteToSMetadata:
    return MutableToSMetadata(
        version=datetime.now(tz=timezone.utc),
        text=f"Terms of Service Text\n\n{uuid4().hex}",
        support="support.com",
    )


@contextlib.contextmanager
def serve_channel(
    path: Path,
    metadata: MetadataType | Iterator[MetadataType],
    port: int = 0,
) -> Iterator[str]:
    http = run_test_server(path, metadata, port)
    host, port = http.server_address  # type: ignore[misc]
    if isinstance(host, bytes):
        host = host.decode()
    host = f"[{host}]" if ":" in host else host
    yield f"http://{host}:{port}"
    http.shutdown()


def main() -> None:
    # demo server for testing purposes
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0, help="Port to serve on.")
    action_mutex = parser.add_mutually_exclusive_group()
    action_mutex.add_argument(
        "--tos",
        action="store_true",
        help="Serve the sample channel with a `terms.json` endpoint.",
    )
    action_mutex.add_argument(
        "--invalid-json",
        action="store_true",
        help="Serve the sample channel with an invalid JSON `terms.json` endpoint.",
    )
    action_mutex.add_argument(
        "--invalid-schema",
        action="store_true",
        help="Serve the sample channel with an invalid schema `terms.json` endpoint.",
    )
    parser.add_argument(
        "--missing-start",
        action="store_true",
        help="Initially serve without a `terms.json` endpoint.",
    )
    args = parser.parse_args()

    metadata: MetadataType | None = None

    def serve_metadata() -> Iterator[MetadataType]:
        nonlocal metadata
        while True:
            yield metadata

    metadata_iterator = iter(
        [
            *([None] if args.missing_start else []),
            *(["?"] if args.invalid_json else []),
            *(["{'version': null}"] if args.invalid_schema else []),
            *([generate_metadata()] if args.tos else []),
        ]
    )
    with serve_channel(SAMPLE_CHANNEL_DIR, serve_metadata(), args.port) as url:
        print(f"Serving HTTP at {url}...")
        while True:
            try:
                metadata = next(metadata_iterator)
            except StopIteration:
                # StopIteration: metadata iterator exhausted, reuse previous metadata
                if isinstance(metadata, RemoteToSMetadata):
                    metadata.version = datetime.now(tz=timezone.utc)
            version = "n/a"
            if isinstance(metadata, RemoteToSMetadata):
                version = timestamp_mapping(metadata.version)
            input(
                f"Current Terms of Service version: {version}\n"
                f"Press Enter to increment Terms of Service version, Ctrl-C to exit.\n"
            )


if __name__ == "__main__":
    main()
