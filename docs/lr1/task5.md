# Задание 5. Веб-сервер журнала оценок

## Назначение и устройство

Сервер на `127.0.0.1:8081` принимает дисциплину и оценку через HTML-форму,
сохраняет данные и показывает общий журнал

`MyHTTPServer` из `http_server.py` отвечает за TCP, чтение запроса, заголовки и ответ. <br>
`GradesServer` из `server.py` наследует его и реализует маршруты, проверку формы,
работу с JSON и заполнение HTML-шаблонов.

## Разбор HTTP

1. `accept()` принимает соединение
2. `parse_request()` разбирает метод, путь, query string и версию HTTP
3. `parse_headers()` читает заголовки до пустой строки и приводит имена к нижнему регистру
4. Тело считывается из того же буферизированного потока `makefile("rb")` по `Content-Length`
5. `handle_request()` выбирает обработчик
6. `send_response()` кодирует HTML в UTF-8, вычисляет длину в байтах и отправляет ответ

## Маршруты

| Метод                     | Путь             | Действие                                    | Статус             |
|---------------------------|------------------|---------------------------------------------|--------------------|
| GET                       | `/`              | Форма и таблица всех дисциплин и оценок     | `200 OK`           |
| POST                      | `/grades`        | Проверка и сохранение оценки; `Location: /` | `303 See Other`    |
| GET                       | `/teapot`        | Демонстрационная HTML-страница              | `418 I'm a teapot` |
| Любой                     | Неизвестный путь | Страница ошибки                             | `404 Not Found`    |
| Неподдерживаемый для пути | Известный путь   | Страница ошибки                             | `400 Bad Request`  |

## Форма и модель данных

Браузер отправляет поля `subject` и `grade` методом POST в формате
`application/x-www-form-urlencoded`.

| Поле      | Проверка                                         |
|-----------|--------------------------------------------------|
| `subject` | От 1 до 120 символов после нормализации пробелов |
| `grade`   | Целое число из множества `2, 3, 4, 5`            |

Хранилище — словарь дисциплин со списками оценок

```json
{
  "Mathematics": [
    5,
    4
  ],
  "Physics": [
    5
  ]
}
```

## Сохранение

Данные загружаются из `grades.json` при запуске. Отсутствующий файл означает пустой журнал;
повреждённая структура приводит к сообщению об ошибке запуска.

Новая оценка сначала добавляется в копию словаря. `save_grades()` записывает её во временный
файл в том же каталоге, вызывает `flush()` и `os.fsync()`, затем заменяет `grades.json`
через `os.replace()`. Только после успешной записи обновляется состояние в памяти и выдаётся `303`.
При ошибке диска сервер не подтверждает сохранение: пишет ошибку в терминал и закрывает соединение.

## Запуск и примеры запросов

```powershell
python Lr1/task5_grades/server.py
```

Откройте `http://127.0.0.1:8081/`. Введите дисциплину и оценку, нажмите «Добавить оценку».
Повторите действие для того же предмета: в таблице должна остаться одна строка с двумя оценками.

Те же запросы можно отправить из другого терминала:

```powershell
curl.exe -i --data "subject=Mathematics&grade=5" http://127.0.0.1:8081/grades
curl.exe -i --data "subject=Mathematics&grade=4" http://127.0.0.1:8081/grades
curl.exe -i http://127.0.0.1:8081/
```

На корректный POST сервер возвращает проверенный ответ:

```http
HTTP/1.1 303 See Other
Location: /
Server: GradesServer
Content-Type: text/html; charset=utf-8
Content-Length: 0
Connection: close
Cache-Control: no-store
```

После двух запросов в `grades.json` находится одна запись
`{"Mathematics": [5, 4]}`. При перезапуске сервера обе оценки остаются в таблице.
Оценка `6` приводит к `400 Bad Request`:

```powershell
curl.exe -i --data "subject=Mathematics&grade=6" http://127.0.0.1:8081/grades
```

## Исходный код

??? note "task5_grades/http_server.py"

    ```python
    --8<-- "Lr1/task5_grades/http_server.py"
    ```

??? note "task5_grades/server.py"

    ```python
    --8<-- "Lr1/task5_grades/server.py"
    ```

??? note "task5_grades/templates/grades.html"

    ```html
    --8<-- "Lr1/task5_grades/templates/grades.html"
    ```

??? note "task5_grades/templates/error.html"

    ```html
    --8<-- "Lr1/task5_grades/templates/error.html"
    ```

??? note "task5_grades/templates/teapot.html"

    ```html
    --8<-- "Lr1/task5_grades/templates/teapot.html"
    ```

??? note "task5_grades/templates/styles.css"

    ```css
    --8<-- "Lr1/task5_grades/templates/styles.css"
    ```
