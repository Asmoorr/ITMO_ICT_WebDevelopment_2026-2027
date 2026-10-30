# Лабораторная работа №2

**Трикула Артём, K3341.** Практики 2.1–2.3 объединены в один Django-проект: это последовательное развитие реестра владельцев автомобилей.

```text
Lr2/
    practical_works/       # единый проект практик 2.1–2.3
    variant5/              # отдельный проект научных конференций
    screenshots/           # снимки экранов для отчёта
    .env                   # локальные настройки, исключены из Git
    .env.example           # пример настроек
    architecture-report.md
```

[Подробная инструкция и соответствие заданиям](practical_works/README.md). [Архитектурные рекомендации](architecture-report.md).

## Быстрый запуск

Из папки студента:

```powershell
poetry install
poetry run python Lr2/practical_works/manage.py migrate
poetry run python Lr2/practical_works/manage.py seed_demo
poetry run python Lr2/practical_works/manage.py runserver 127.0.0.1:8001
```

[Реестр](http://127.0.0.1:8001/), [Admin](http://127.0.0.1:8001/admin/). Администратор — `admin`, обычные пользователи — `owner1`–`owner6`; начальный пароль указан в `DJANGO_DEMO_PASSWORD` локального `.env`.

Общее окружение Poetry, пользователи и данные итогового этапа сохранены. Рабочая база — `lr2_practices`, тестовая — `test_lr2_practices`; их имена изолированы от `lr2_conferences` для `variant5`.

На другом компьютере заполните `.env` по примеру, создайте базы и отдельные роли PostgreSQL. Не перезаписывайте существующий `.env` примером. Роль приложения не должна быть superuser. Миграция требует `btree_gist`; при ограниченной политике сервера его предварительно устанавливает администратор.

## Проверки

```powershell
poetry run python Lr2/practical_works/manage.py test project_first_app --settings=django_project_trikula.test_settings --keepdb --noinput
poetry run ruff check Lr2/practical_works
```

Для тестов база `test_lr2_practices` заранее создаётся с владельцем `lr2_test`. Эта роль не имеет `CREATEDB`, поэтому используется `--keepdb`.

Отчёт в корневом `docs/lr2/` содержит общий обзор и три страницы по практикам. Все страницы ссылаются на один набор исходников. Вариант 5 реализован в отдельном проекте: [научные конференции — запуск, функции, модель и проверки](variant5/README.md). Сайт работает на порту 8005, практики — на 8001. Основная часть содержит 31 тест; практики — 20.
