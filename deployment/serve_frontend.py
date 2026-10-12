import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote

from wsgiref.util import FileWrapper


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def application(environ, start_response):
    if not FRONTEND_DIST.exists():
        body = b"Frontend build directory was not found."
        start_response(
            "500 Internal Server Error",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]

    frontend_root = FRONTEND_DIST.resolve()
    request_path = unquote(environ.get("PATH_INFO", "/")).lstrip("/")

    try:
        requested_file = (frontend_root / request_path).resolve()
        requested_file.relative_to(frontend_root)
    except (OSError, RuntimeError, ValueError):
        body = b"Requested path is invalid."
        start_response(
            "404 Not Found",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]

    if request_path and requested_file.exists() and requested_file.is_file():
        file_path = requested_file
    else:
        file_path = frontend_root / "index.html"

    if not file_path.exists():
        body = b"Frontend entry file was not found."
        start_response(
            "404 Not Found",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]

    content_type, _ = mimetypes.guess_type(str(file_path))
    content_type = content_type or "application/octet-stream"

    file_size = file_path.stat().st_size

    start_response(
        "200 OK",
        [
            ("Content-Type", content_type),
            ("Content-Length", str(file_size)),
            ("Cache-Control", "no-cache"),
        ],
    )

    return FileWrapper(open(file_path, "rb"))