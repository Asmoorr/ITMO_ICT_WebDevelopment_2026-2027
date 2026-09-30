import socket
import sys
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import BinaryIO
from urllib.parse import parse_qs


TEMPLATES_PATH = Path(__file__).with_name("templates")
ERROR_TEMPLATE = (TEMPLATES_PATH / "error.html").read_text(encoding="utf-8")


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    version: str
    headers: dict[str, str]
    body: bytes


@dataclass
class Response:
    status: int
    body: str = ""
    headers: dict[str, str] = field(default_factory=dict)


class HTTPError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class MyHTTPServer:
    TIMEOUT = 5
    MAX_HEADER_SIZE = 16 * 1024
    MAX_BODY_SIZE = 64 * 1024
    STATUS = {
        200: "OK",
        303: "See Other",
        400: "Bad Request",
        404: "Not Found",
        418: "I'm a teapot"
    }

    def __init__(self, host: str, port: int, name: str):
        if not name.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise ValueError("Имя сервера должно содержать печатные ASCII-символы.")

        self.host = host
        self.port = port
        self.name = name

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind((self.host, self.port))
            server.listen()

            print(f"{self.name}: http://{self.host}:{self.port}/")

            while True:
                connection, address = server.accept()

                with connection:
                    print(f"Подключение: {address}")
                    self.serve_client(connection)

    def serve_client(self, connection: socket.socket) -> None:
        connection.settimeout(self.TIMEOUT)
        request = None

        try:
            # Один буферизированный поток для заголовков и тела запроса.
            with connection.makefile("rb") as reader:
                request = self.parse_request(reader)

            response = self.handle_request(request)
        except (HTTPError, ValueError, socket.timeout) as error:
            status = error.status if isinstance(error, HTTPError) else 400
            message = str(error) if isinstance(error, HTTPError) else "Некорректный запрос."

            page = ERROR_TEMPLATE.format(status=status, message=escape(message))
            response = Response(status, page)
        except OSError as error:
            # Не выдаём ошибку сервера за неверный запрос или успешное сохранение.
            print(f"Ошибка соединения или хранилища: {error}", file=sys.stderr)
            return

        try:
            self.send_response(connection, response, head_only=request is not None and request.method == "HEAD")
        except OSError as error:
            print(f"Не удалось отправить ответ: {error}", file=sys.stderr)

    def parse_request(self, reader: BinaryIO) -> Request:
        line = reader.readline(self.MAX_HEADER_SIZE + 1)
        method, target, version = line.decode("iso-8859-1").split()
        if len(line) > self.MAX_HEADER_SIZE or not target.startswith("/") or version not in {"HTTP/1.0", "HTTP/1.1"}:
            raise ValueError

        path, _, query_string = target.partition("?")
        query = parse_qs(query_string, keep_blank_values=True)

        headers = self.parse_headers(reader)
        # Поддерживается обычное тело с Content-Length, без потоковой передачи.
        if "transfer-encoding" in headers or "expect" in headers:
            raise ValueError

        length = int(headers.get("content-length", "0"))
        if not 0 <= length <= self.MAX_BODY_SIZE:
            raise ValueError

        body = reader.read(length)
        if len(body) != length:
            raise ValueError

        return Request(method, path, query, version, headers, body)

    def parse_headers(self, reader: BinaryIO) -> dict[str, str]:
        headers = {}
        remaining = self.MAX_HEADER_SIZE

        while True:
            line = reader.readline(remaining + 1)
            remaining -= len(line)
            if remaining < 0 or not line.endswith(b"\r\n"):
                raise ValueError
            if line == b"\r\n":
                return headers

            name, value = line.decode("iso-8859-1").split(":", 1)
            name = name.strip().lower()
            if not name or name in headers:
                raise ValueError
            headers[name] = value.strip()

    def handle_request(self, request: Request) -> Response:
        # Прикладной сервер переопределяет маршруты в наследнике.
        raise HTTPError(404, "Страница не найдена.")

    def send_response(self, connection: socket.socket, response: Response, head_only: bool = False) -> None:
        body = response.body.encode("utf-8")

        headers = {
            **response.headers,
            "Server": self.name,
            "Content-Type": "text/html; charset=utf-8",
            "Content-Length": str(len(body)),
            "Connection": "close",
            "Cache-Control": "no-store",
        }

        head = f"HTTP/1.1 {response.status} {self.STATUS[response.status]}\r\n"
        head += "".join(f"{name}: {value}\r\n" for name, value in headers.items())

        connection.sendall((head + "\r\n").encode("ascii") + (b"" if head_only else body))


if __name__ == "__main__":
    serv = MyHTTPServer("127.0.0.1", 8081, "MyHTTPServer")

    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        pass
