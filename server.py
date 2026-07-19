#!/usr/bin/env python3
"""Веб-интерфейс управления громкостью: python server.py [--port 8000]

Отдаёт фронтенд из папки static/ и JSON-API:

    GET  /api/volume                     -> {"volume": 50, "max": 300, "backend": "pactl"}
    POST /api/volume  {"volume": 150}    установить громкость
    POST /api/volume  {"delta": 10}      изменить на N процентов

Если на машине нет звуковой подсистемы, сервер запускается в демо-режиме
(громкость хранится в памяти), чтобы интерфейс можно было посмотреть.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from volume import pick_backend

STATIC_DIR = Path(__file__).resolve().parent / "static"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

backend = pick_backend(allow_demo=True)


class Handler(BaseHTTPRequestHandler):

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, code: int = 200) -> None:
        self._send(code, json.dumps(payload).encode(), "application/json; charset=utf-8")

    def _state(self) -> dict:
        return {"volume": backend.get(), "max": backend.max_volume,
                "backend": backend.name}

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/volume":
            try:
                self._send_json(self._state())
            except Exception as exc:
                self._send_json({"error": str(exc)}, 500)
            return

        # статика; защита от выхода за пределы каталога
        rel = path.lstrip("/") or "index.html"
        file = (STATIC_DIR / rel).resolve()
        if not file.is_relative_to(STATIC_DIR) or not file.is_file():
            self._send(404, "404".encode(), "text/plain; charset=utf-8")
            return
        ctype = CONTENT_TYPES.get(file.suffix, "application/octet-stream")
        self._send(200, file.read_bytes(), ctype)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/volume":
            self._send_json({"error": "не найдено"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            if "volume" in data:
                backend.set(int(data["volume"]))
            elif "delta" in data:
                backend.set(backend.get() + int(data["delta"]))
            else:
                self._send_json({"error": "нужно поле volume или delta"}, 400)
                return
            self._send_json(self._state())
        except (ValueError, TypeError) as exc:
            self._send_json({"error": f"неверный запрос: {exc}"}, 400)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)

    def log_message(self, fmt: str, *args) -> None:
        pass  # не засорять консоль построчным логом запросов


def main() -> None:
    parser = argparse.ArgumentParser(description="Веб-интерфейс управления громкостью")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1",
                        help="слушать на этом адресе (по умолчанию только локально)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    mode = " (ДЕМО-РЕЖИМ: звуковая подсистема не найдена)" if backend.name == "demo" else ""
    print(f"Бэкенд: {backend.name}, максимум {backend.max_volume}%{mode}")
    print(f"Открой в браузере: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено")


if __name__ == "__main__":
    main()
