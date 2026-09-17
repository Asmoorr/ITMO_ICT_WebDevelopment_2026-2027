import socket
from pathlib import Path


HOST = "127.0.0.1"
PORT = 8080
BUFFER_SIZE = 4096
HTML_PATH = Path(__file__).with_name("index.html")


def build_response(status: str, body: bytes, content_type: str) -> bytes:
    headers = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")
    return headers + body


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"HTTP-сервер запущен: http://{HOST}:{PORT}/")

        try:
            while True:
                connection, address = server_socket.accept()
                with connection:
                    request = connection.recv(BUFFER_SIZE).decode("iso-8859-1")
                    request_line = request.split("\r\n", maxsplit=1)[0]
                    print(f"{address}: {request_line}")

                    if request_line.startswith("GET / "):
                        body = HTML_PATH.read_bytes()
                        response = build_response("200 OK", body, "text/html; charset=utf-8")
                    else:
                        body = "Страница не найдена".encode("utf-8")
                        response = build_response("404 Not Found", body, "text/plain; charset=utf-8")

                    connection.sendall(response)
        except KeyboardInterrupt:
            print("\nСервер остановлен")


if __name__ == "__main__":
    main()
