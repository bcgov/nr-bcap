from __future__ import annotations

import re
import socket
import threading


def relay(
    src: socket.socket,
    dst: socket.socket,
    label: str,
    rewrite_request: bool = False,
    rewrite_response: bool = False
) -> None:
    try:
        first = True

        while True:
            data = src.recv(65536)

            if not data:
                break

            if first:
                first = False

                if rewrite_request:
                    text = data.decode("utf-8", errors="surrogateescape")
                    text = re.sub(r"Host: [^\r\n]+", "Host: localhost:9222", text)
                    data = text.encode("utf-8", errors="surrogateescape")

                if rewrite_response:
                    text = data.decode("utf-8", errors="surrogateescape")
                    text = text.replace("ws://localhost:9222", "ws://host.docker.internal:9223")
                    text = text.replace("localhost:9222", "host.docker.internal:9223")
                    length_match = re.search(r"Content-Length:\s*(\d+)", text)

                    if length_match:
                        body_start = text.find("\r\n\r\n")

                        if body_start >= 0:
                            body = text[body_start + 4:]
                            text = text[:body_start] + "\r\n\r\n" + body
                            text = re.sub(r"Content-Length:\s*\d+", f"Content-Length:{len(body.encode('utf-8'))}", text)

                    data = text.encode("utf-8", errors="surrogateescape")

            dst.sendall(data)
    except Exception:
        pass

    src.close()
    dst.close()


def main() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 9223))
    server.listen(5)
    print("CDP proxy listening on 0.0.0.0:9223 -> 127.0.0.1:9222")

    while True:
        client, _ = server.accept()
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect(("127.0.0.1", 9222))
        threading.Thread(target=relay, args=(client, remote, "req", True, False), daemon=True).start()
        threading.Thread(target=relay, args=(remote, client, "res", False, True), daemon=True).start()


main()
