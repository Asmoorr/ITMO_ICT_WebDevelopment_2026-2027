import json
import socket
import threading
from collections.abc import Iterator


HOST = "127.0.0.1"
PORT = 9004
MAX_FRAME = 16 * 1024
MAX_TEXT = 2000


def send_message(connection: socket.socket, message: dict, lock: threading.Lock) -> None:
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if len(payload) > MAX_FRAME:
        raise ValueError("Сообщение слишком длинное")
    with lock:
        connection.sendall(payload + b"\n")


def receive_messages(connection: socket.socket) -> Iterator[dict]:
    buffer = bytearray()
    while True:
        try:
            chunk = connection.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            if buffer:
                raise ValueError("Соединение закрыто посреди сообщения")
            return
        buffer.extend(chunk)
        while (boundary := buffer.find(b"\n")) != -1:
            if boundary > MAX_FRAME:
                raise ValueError("Сообщение слишком длинное")
            frame = bytes(buffer[:boundary])
            del buffer[:boundary + 1]
            try:
                message = json.loads(frame.decode("utf-8"))
            except (ValueError, RecursionError) as error:
                raise ValueError("Некорректный JSON или UTF-8") from error
            if not isinstance(message, dict):
                raise ValueError("Ожидается JSON-объект")
            yield message
        if len(buffer) > MAX_FRAME:
            raise ValueError("Сообщение слишком длинное")


def close_connection(connection: socket.socket) -> None:
    try:
        connection.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    connection.close()
