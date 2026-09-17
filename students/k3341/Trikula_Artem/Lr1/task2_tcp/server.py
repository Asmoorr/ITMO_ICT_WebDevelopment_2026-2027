import json
import socket


HOST = "127.0.0.1"
PORT = 9002
BUFFER_SIZE = 4096


def calculate_hypotenuse(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        raise ValueError("Длины катетов должны быть положительными")
    return (a**2 + b**2) ** 0.5


def receive_all(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while chunk := connection.recv(BUFFER_SIZE):
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    return b"".join(chunks)


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"TCP-сервер запущен на {HOST}:{PORT}. Для остановки нажмите Ctrl+C")

        try:
            while True:
                connection, address = server_socket.accept()
                with connection:
                    try:
                        request = json.loads(receive_all(connection).decode("utf-8"))
                        hypotenuse = calculate_hypotenuse(request["a"], request["b"])
                        response = {"ok": True, "hypotenuse": hypotenuse}
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                        response = {"ok": False, "error": str(error)}

                    connection.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
                    print(f"Обработан запрос от {address}")
        except KeyboardInterrupt:
            print("\nСервер остановлен")


if __name__ == "__main__":
    main()
