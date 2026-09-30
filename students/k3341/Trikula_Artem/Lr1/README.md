# Лабораторная работа №1. Работа с сокетами

**Трикула Артём, K3341.** Выполнены задания 1–5:

1. Обмен приветствиями по UDP.
2. Вычисление гипотенузы через TCP — вариант 1 для №33 в журнале.
3. Раздача HTML-страницы через TCP-сокет по HTTP.
4. Многопользовательский TCP-чат с потоками, именами и командой `/quit`.
5. HTTP-сервер журнала оценок с GET/POST и сохранением в JSON.

**[Открыть отчёт MkDocs](https://asmoorr.github.io/ITMO_ICT_WebDevelopment_2026-2027/)**

## Запуск

Нужен Python 3.10+. Внешние зависимости для самих приложений не требуются.
Команды выполняются из `students/k3341/Trikula_Artem`.
Сначала запустите сервер, затем клиент в другом терминале.

```powershell
# Задание 1
python Lr1/task1_udp/server.py
python Lr1/task1_udp/client.py

# Задание 2
python Lr1/task2_tcp/server.py
python Lr1/task2_tcp/client.py

# Задание 3 — http://127.0.0.1:8080/
python Lr1/task3_http/server.py

# Задание 4 — каждый клиент в отдельном терминале
python Lr1/task4_chat/server.py
python Lr1/task4_chat/client.py --username Artem
python Lr1/task4_chat/client.py --username Anna
python Lr1/task4_chat/client.py --username Ivan

# Задание 5 — http://127.0.0.1:8081/
python Lr1/task5_grades/server.py
```

При использовании Poetry выполните `poetry install` и добавляйте `poetry run` перед `python`.
Сервер UDP завершится после одного обмена; остальные останавливаются через `Ctrl+C`.
В чате для выхода введите `/quit`.

`task5_grades/grades.json` создаётся при сохранении первой оценки и не включается в Git.

## Документация

Страницы отчёта находятся в [корневой папке `docs/`](../../../../docs/index.md), конфигурация — в корневом `mkdocs.yml`.
Из корня репозитория:

```powershell
python -m venv .venv-docs
.venv-docs/Scripts/python -m pip install -r requirements-docs.txt
.venv-docs/Scripts/python -m mkdocs serve
```

Публикация на GitHub Pages выполняется автоматически после push изменений в `main`.
Подробности — в [инструкции по сборке](../../../../docs/publishing.md).
