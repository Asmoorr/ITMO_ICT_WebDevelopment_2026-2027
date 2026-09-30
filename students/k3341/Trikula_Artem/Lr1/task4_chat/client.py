import argparse
import queue
import socket
import threading

from protocol import HOST, MAX_TEXT, PORT, close_connection, receive_messages, send_message


def read_console(lines: queue.Queue, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            text = input()
        except EOFError:
            text = "/quit"
        while not stop_event.is_set():
            try:
                lines.put(text, timeout=0.1)
                break
            except queue.Full:
                continue
        if text == "/quit":
            return


def receive_loop(connection: socket.socket, stop_event: threading.Event,
                 registered: threading.Event) -> None:
    try:
        for message in receive_messages(connection):
            kind = message.get("type")
            if kind == "welcome":
                print(f"* Вы вошли как {message['username']}. Для выхода введите /quit.", flush=True)
                registered.set()
            elif kind == "chat":
                print(f"[{message['username']}] {message['text']}", flush=True)
            elif kind == "system":
                print(f"* {message['text']}", flush=True)
            elif kind == "error":
                print(f"Ошибка: {message['text']}", flush=True)
                return
            else:
                raise ValueError("Неизвестный ответ сервера")
        if not stop_event.is_set():
            print("Соединение с сервером закрыто", flush=True)
    except (OSError, ValueError, KeyError) as error:
        if not stop_event.is_set():
            print(f"Ошибка соединения: {error}", flush=True)
    finally:
        stop_event.set()


def run_client(host: str, port: int, username: str) -> None:
    connection = socket.create_connection((host, port), timeout=5)
    connection.settimeout(1)
    stop_event = threading.Event()
    registered = threading.Event()
    send_lock = threading.Lock()
    receiver = threading.Thread(target=receive_loop, args=(connection, stop_event, registered))
    receiver.start()
    try:
        send_message(connection, {"type": "join", "username": username}, send_lock)
        while not registered.wait(timeout=0.1):
            if stop_event.is_set():
                return
        lines = queue.Queue(maxsize=100)
        threading.Thread(target=read_console, args=(lines, stop_event), daemon=True).start()
        while not stop_event.is_set():
            try:
                text = lines.get(timeout=0.1)
            except queue.Empty:
                continue
            if stop_event.is_set():
                break
            if text == "/quit":
                stop_event.set()
                send_message(connection, {"type": "quit"}, send_lock)
                print("* Вы вышли из чата", flush=True)
                break
            if not text.strip():
                continue
            if len(text) > MAX_TEXT:
                print(f"Максимальная длина сообщения: {MAX_TEXT} символов", flush=True)
                continue
            send_message(connection, {"type": "chat", "text": text}, send_lock)
    finally:
        stop_event.set()
        close_connection(connection)
        receiver.join()


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host", "-h", default=HOST)
    parser.add_argument("--port", "-p", type=int, default=PORT)
    parser.add_argument("--username", "-u")
    parser.add_argument("--help", action="help")
    args = parser.parse_args()
    try:
        username = args.username if args.username is not None else input("Ваше имя: ").strip()
        run_client(args.host, args.port, username)
    except (KeyboardInterrupt, EOFError):
        print("\nВы вышли из чата")
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}")


if __name__ == "__main__":
    main()
