# Сборка и публикация документации

## Расположение файлов

Конфигурация `mkdocs.yml`, зависимости `requirements-docs.txt` и workflow
`.github/workflows/docs.yml` находятся в корне форка.
Страницы отчёта — в корневой папке `docs/`, как в инструкции курса:
`index.md` содержит главную страницу, `lr1/` — отчёт о ЛР 1.
Путь указан в `docs_dir` конфигурации MkDocs.

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

После отправки изменений в ветку `main` workflow **Publish MkDocs** собирает сайт,
загружает содержимое `site/` и публикует его через GitHub Actions. В настройках
**Settings → Pages → Build and deployment** выбран источник **GitHub Actions**.

В инструкции курса показан другой способ — `mkdocs gh-deploy` с веткой `gh-pages`.
Для этого форка настроен автоматический деплой через Actions: результатом служит
тот же опубликованный MkDocs-сайт. Смешивать эти два способа в одном репозитории не нужно.

В Git исключены результат сборки `site/`, виртуальное окружение и `__pycache__/`.
При изменении Markdown, исходного кода ЛР 1 или настроек сборки workflow запустится
после `git push origin main`. Статус можно посмотреть на вкладке **Actions** репозитория.

GitHub Pages содержит статический отчёт. Серверы из лабораторной работы запускаются
локально по инструкциям на страницах заданий.
