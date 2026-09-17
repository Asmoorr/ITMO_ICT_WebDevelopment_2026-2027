import json
import socket


SERVER_ADDRESS = ("127.0.0.1", 9002)
BUFFER_SIZE = 4096

def read_request() -> dict[str, float]:
    print("Вариант 1 — вычисление гипотенузы по теореме Пифагора. Введите длины катетов:\n")
    return {
        "a": float(input("Катет a: ")),
        "b": float(input("Катет b: ")),
    }


def main() -> None:
    try:
        request = read_request()
    except ValueError as error:
        print(f"Ошибка ввода: {error}")
        return

    with socket.create_connection(SERVER_ADDRESS, timeout=5) as client_socket:
        client_socket.sendall((json.dumps(request) + "\n").encode("utf-8"))
        response = json.loads(client_socket.recv(BUFFER_SIZE).decode("utf-8"))

    if response["ok"]:
        print(f"Гипотенуза: {response['hypotenuse']}")
    else:
        print("Ошибка сервера:", response["error"])


if __name__ == "__main__":
    main()
