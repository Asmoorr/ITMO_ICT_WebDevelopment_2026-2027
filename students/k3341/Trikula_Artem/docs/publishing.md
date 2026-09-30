# Сборка и публикация документации

## Расположение файлов

Конфигурация `mkdocs.yml` зависимости `requirements-docs.txt` и workflow
`.github/workflows/docs.yml` находятся в корне форка.
Страницы отчёта — в `students/k3341/Trikula_Artem/docs/`:
этот путь задан в `docs_dir`.

Полные листинги включаются через `pymdownx.snippets` из `Lr1/`.
Поэтому сборку нужно запускать из корня репозитория, где расположен `mkdocs.yml`.
Не копируйте фрагменты исходников вручную: после изменения Python-файла сайт обновит листинг при сборке.

## Локальный запуск

Из корня репозитория в PowerShell:

```powershell
python -m venv .venv-docs
.venv-docs/Scripts/python -m pip install -r requirements-docs.txt
.venv-docs/Scripts/python -m mkdocs serve
```

Откройте `http://127.0.0.1:8000/`. Изменения Markdown автоматически обновляют локальную страницу.
Для остановки нажмите `Ctrl+C`.

Проверка перед публикацией:

```powershell
.venv-docs/Scripts/python -m mkdocs build --strict
```


## GitHub Pages

[asmoorr.github.io/ITMO_ICT_WebDevelopment_2026-2027](https://asmoorr.github.io/ITMO_ICT_WebDevelopment_2026-2027/)
