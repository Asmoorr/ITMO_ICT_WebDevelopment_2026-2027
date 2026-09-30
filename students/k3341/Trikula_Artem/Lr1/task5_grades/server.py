import json
import os
import tempfile
from html import escape
from pathlib import Path
from urllib.parse import parse_qs

from http_server import HTTPError, MyHTTPServer, Request, Response


HOST = "127.0.0.1"
PORT = 8081
DATA_PATH = Path(__file__).with_name("grades.json")
TEMPLATES_PATH = Path(__file__).with_name("templates")

GRADES_TEMPLATE = (TEMPLATES_PATH / "grades.html").read_text(encoding="utf-8")
TEAPOT_PAGE = (TEMPLATES_PATH / "teapot.html").read_text(encoding="utf-8")
ROW_TEMPLATE = "<tr><td>{subject}</td><td>{grades}</td></tr>"
EMPTY_ROW = '<tr><td colspan="2">Оценок пока нет.</td></tr>'


def validate_grade_form(request: Request) -> tuple[str, int]:
    try:
        fields = parse_qs(request.body.decode("utf-8"), errors="strict")
        subject = " ".join(fields["subject"][0].split())
        grade = int(fields["grade"][0])

        if not 1 <= len(subject) <= 120 or grade not in {2, 3, 4, 5}:
            raise ValueError
    except (ValueError, KeyError) as error:
        raise HTTPError(400, "Некорректные данные формы.") from error

    return subject, grade


def load_grades(path: Path) -> dict[str, list[int]]:
    try:
        with path.open(encoding="utf-8") as file:
            grades = json.load(file)
    except FileNotFoundError:
        return {}
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"Повреждён файл журнала: {path}") from error

    if not isinstance(grades, dict):
        raise ValueError("Журнал должен быть объектом JSON.")

    for subject, values in grades.items():
        if (
            not 1 <= len(subject) <= 120
            or subject != " ".join(subject.split())
            or not isinstance(values, list)
            or not values
            or any(type(value) is not int or value not in {2, 3, 4, 5} for value in values)
        ):
            raise ValueError(f"Некорректная запись в журнале: {subject!r}")

    return grades


def save_grades(path: Path, grades: dict[str, list[int]]) -> None:
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f"{path.name}.", suffix=".tmp", delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(grades, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def render_page(grades: dict[str, list[int]]) -> str:
    rows = "\n".join(
        ROW_TEMPLATE.format(
            subject=escape(subject),
            grades=", ".join(map(str, values)),
        )
        for subject, values in sorted(grades.items(), key=lambda item: item[0].casefold())
    )

    if not rows:
        rows = EMPTY_ROW

    return GRADES_TEMPLATE.format(rows=rows)


class GradesServer(MyHTTPServer):
    def __init__(self, host: str, port: int, name: str, path: Path = DATA_PATH):
        super().__init__(host, port, name)

        self.path = path
        self.grades = load_grades(path)

    def handle_request(self, request: Request) -> Response:
        if request.path == "/teapot" and request.method == "GET":
            return Response(418, TEAPOT_PAGE)

        if request.path not in {"/", "/grades", "/teapot"}:
            raise HTTPError(404, "Страница не найдена.")

        if request.path == "/" and request.method == "GET":
            return Response(200, render_page(self.grades))

        if request.path == "/grades" and request.method == "POST":
            subject, grade = validate_grade_form(request)

            updated = {name: values.copy() for name, values in self.grades.items()}
            updated.setdefault(subject, []).append(grade)

            # При ошибке записи serve_client закроет соединение без подтверждения.
            save_grades(self.path, updated)
            self.grades = updated

            return Response(303, headers={"Location": "/"})

        raise HTTPError(400, "Некорректный запрос.")


def main() -> None:
    try:
        server = GradesServer(HOST, PORT, "GradesServer")
        server.serve_forever()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Не удалось запустить журнал: {error}") from error
    except KeyboardInterrupt:
        print("\nСервер остановлен")


if __name__ == "__main__":
    main()
