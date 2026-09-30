import argparse
import logging
import socket
import threading
from dataclasses import dataclass, field

from protocol import HOST, MAX_TEXT, PORT, close_connection, receive_messages, send_message

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class ClientSession:
    connection: socket.socket
    username: str = ""
    ready: bool = False
    send_lock: threading.Lock = field(default_factory=threading.Lock)


class ChatServer:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.listener.bind((host, port))
            self.listener.listen()
            self.listener.settimeout(0.2)
        except OSError:
            self.listener.close()
            raise
        self.address = self.listener.getsockname()
        self.clients: dict[str, ClientSession] = {}
        self.workers: dict[ClientSession, threading.Thread] = {}
        self.clients_lock = threading.Lock()
        self.stop_event = threading.Event()

    def serve_forever(self) -> None:
        logger.info(f"Чат запущен на {self.address[0]}:{self.address[1]}")
        try:
            while not self.stop_event.is_set():
                try:
                    connection, address = self.listener.accept()
                except socket.timeout:
                    continue
                connection.settimeout(1)
                logger.info(f"Новое подключение: {address[0]}:{address[1]}")
                session = ClientSession(connection)
                worker = threading.Thread(target=self.handle_client, args=(session,))
                with self.clients_lock:
                    self.workers[session] = worker
                worker.start()
        finally:
            logger.info("Остановка сервера: закрываем подключения")
            self.stop_event.set()
            self.listener.close()
            with self.clients_lock:
                workers = list(self.workers.items())
            for session, _ in workers:
                close_connection(session.connection)
            for _, worker in workers:
                worker.join()
            logger.info("Сервер остановлен")

    def send(self, session: ClientSession, message: dict) -> None:
        send_message(session.connection, message, session.send_lock)

    def register(self, session: ClientSession, message: dict) -> None:
        username = message.get("username")
        if message.get("type") != "join":
            raise ValueError("Первое сообщение должно быть join")
        if not isinstance(username, str) or not 1 <= len(username) <= 24:
            raise ValueError("Имя должно содержать от 1 до 24 символов")
        if not all(character.isalnum() or character == "_" for character in username):
            raise ValueError("В имени разрешены только буквы, цифры и _")
        with self.clients_lock:
            if username.casefold() in self.clients:
                raise ValueError("Имя уже занято")
            session.username = username
            self.clients[username.casefold()] = session
        self.send(session, {"type": "welcome", "username": username})
        with self.clients_lock:
            session.ready = True
        logger.info(f"[{username}] Вошёл в чат")
        self.broadcast({"type": "system", "text": f"{username} вошёл в чат"}, session)

    def broadcast(self, message: dict, sender: ClientSession) -> None:
        pending = [(message, sender)]
        while pending and not self.stop_event.is_set():
            current, excluded = pending.pop()
            with self.clients_lock:
                recipients = [client for client in self.clients.values()
                              if client.ready and client is not excluded]
            for recipient in recipients:
                try:
                    self.send(recipient, current)
                except OSError as error:
                    if not self.stop_event.is_set():
                        logger.warning(f"[{recipient.username}] Ошибка доставки: {error}")
                    if self.remove_client(recipient):
                        pending.append(({
                                            "type": "system", "text": f"{recipient.username} вышел из чата"
                                        }, recipient))

    def remove_client(self, session: ClientSession) -> bool:
        with self.clients_lock:
            key = session.username.casefold()
            if self.clients.get(key) is not session:
                return False
            del self.clients[key]
            was_ready = session.ready
            session.ready = False
        close_connection(session.connection)
        logger.info(f"[{session.username}] Удалён из списка участников")
        return was_ready

    def handle_client(self, session: ClientSession) -> None:
        try:
            messages = receive_messages(session.connection)
            first = next(messages, None)
            if first is None:
                return
            self.register(session, first)
            for message in messages:
                if self.stop_event.is_set():
                    break
                if message.get("type") == "quit":
                    logger.info(f"[{session.username}] Запросил выход /quit")
                    break
                if message.get("type") != "chat":
                    raise ValueError("Неизвестный тип сообщения")
                text = message.get("text")
                if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
                    raise ValueError(f"Текст должен содержать от 1 до {MAX_TEXT} символов")
                log_text = text.replace("\r", "\\r").replace("\n", "\\n")
                logger.info(f"[{session.username}] Сообщение: {log_text}")
                self.broadcast({"type": "chat", "username": session.username, "text": text}, session)
        except ValueError as error:
            logger.warning(f"[{session.username or 'Гость'}] Ошибка запроса: {error}")
            try:
                self.send(session, {"type": "error", "text": str(error)})
            except OSError:
                pass
        except OSError as error:
            if not self.stop_event.is_set():
                logger.warning(f"[{session.username or 'Гость'}] Ошибка соединения: {error}")
        finally:
            if self.remove_client(session):
                self.broadcast({"type": "system", "text": f"{session.username} вышел из чата"}, session)
            close_connection(session.connection)
            logger.info(f"[{session.username or 'Гость'}] Соединение закрыто")
            with self.clients_lock:
                self.workers.pop(session, None)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host", "-h", default=HOST)
    parser.add_argument("--port", "-p", type=int, default=PORT)
    parser.add_argument("--help", action="help")
    args = parser.parse_args()
    try:
        ChatServer(args.host, args.port).serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as error:
        logger.error(f"Ошибка сервера: {error}")


if __name__ == "__main__":
    main()
