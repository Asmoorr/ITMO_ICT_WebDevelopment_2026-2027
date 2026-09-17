import socket


SERVER_ADDRESS = ("127.0.0.1", 9001)
BUFFER_SIZE = 1024
TIMEOUT_SECONDS = 5


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.settimeout(TIMEOUT_SECONDS)
        message = "Hello, server"
        client_socket.sendto(message.encode("utf-8"), SERVER_ADDRESS)
        print(f"Отправлено: {message}")

        try:
            data, _ = client_socket.recvfrom(BUFFER_SIZE)
        except TimeoutError:
            print("Сервер не ответил вовремя")
            return

        print(f"Получено: {data.decode('utf-8')}")


if __name__ == "__main__":
    main()
