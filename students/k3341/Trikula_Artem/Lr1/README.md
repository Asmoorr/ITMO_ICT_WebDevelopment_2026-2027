# Лабораторная работа №1. Работа с сокетами

Выполнены практические задания 1–3:

1. обмен сообщениями по UDP;
2. вычисление гипотенузы по теореме Пифагора через TCP (вариант 1 для №33 в журнале);
3. раздача HTML-страницы по HTTP через TCP-сокет.

## Подготовка окружения

Команды выполняются из корневого каталога `Trikula_Artem`. Конфигурация Poetry и
локальное виртуальное окружение `.venv` находятся там же.

```powershell
poetry install
```

Poetry настроен на создание виртуального окружения в каталоге `.venv`.

## Запуск

Сначала запустите сервер нужного задания, затем в другом терминале — клиент.

```powershell
# Задание 1
poetry run python Lr1/task1_udp/server.py
poetry run python Lr1/task1_udp/client.py

# Задание 2
poetry run python Lr1/task2_tcp/server.py
poetry run python Lr1/task2_tcp/client.py

# Задание 3
poetry run python Lr1/task3_http/server.py
```

Для задания 3 откройте в браузере <http://127.0.0.1:8080/>. Остановка серверов — `Ctrl+C`.
