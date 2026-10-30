import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from conferences.models import Conference, Registration, Review, Topic, Venue


class Command(BaseCommand):
    help = "Создать вымышленные конференции, участников и организатора"

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("DJANGO_DEMO_PASSWORD")
        if not password:
            raise CommandError("Укажите DJANGO_DEMO_PASSWORD в Lr2/.env")
        user_model = get_user_model()
        today = timezone.localdate()
        admin, created = user_model.objects.get_or_create(
            username="admin", defaults={"is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password(password)
            admin.save()
        group, _ = Group.objects.get_or_create(name="Организаторы")
        group.permissions.set(
            Permission.objects.filter(content_type__app_label="conferences")
        )
        organizer, created = user_model.objects.get_or_create(
            username="organizer",
            defaults={
                "first_name": "Мария",
                "last_name": "Организаторова",
                "is_staff": True,
                "email": "organizer@example.test",
            },
        )
        if created:
            organizer.set_password(password)
            organizer.save()
            organizer.groups.add(group)
        authors = []
        names = [
            ("Артём", "Соколов"),
            ("Анна", "Морозова"),
            ("Иван", "Орлов"),
            ("Мария", "Волкова"),
            ("Павел", "Лебедев"),
            ("Ольга", "Белова"),
            ("Денис", "Зайцев"),
            ("Елена", "Кузнецова"),
        ]
        for index, (first, last) in enumerate(names, 1):
            author, created = user_model.objects.get_or_create(
                username="researcher" if index == 1 else f"author{index}",
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"author{index}@example.test",
                    "organization": "Учебная исследовательская группа",
                },
            )
            if created:
                author.set_password(password)
                author.save()
            authors.append(author)
        topic_names = [
            "Информатика",
            "Искусственный интеллект",
            "Инженерия",
            "Биотехнологии",
            "Образование",
        ]
        topics = [Topic.objects.get_or_create(name=name)[0] for name in topic_names]
        places = [
            ("Научный центр на Неве", "Санкт-Петербург", "Учебный проспект, 12"),
            ("Центр инженерных исследований", "Москва", "Исследовательская улица, 8"),
            ("Университетский конгресс-холл", "Казань", "Университетская улица, 4"),
        ]
        venues = [
            Venue.objects.get_or_create(
                name=name,
                city=city,
                defaults={
                    "address": address,
                    "description": "Учебная площадка с лекционными залами, проектором и пространством для обсуждений. Доступна безбарьерная среда.",
                },
            )[0]
            for name, city, address in places
        ]
        titles = [
            "Распределённые системы и данные",
            "Машинное обучение в науке",
            "Инженерия программных систем",
            "Биотехнологии и вычисления",
            "Цифровая среда образования",
            "Безопасность информационных систем",
            "Робототехника и управление",
            "Человек и интеллектуальные системы",
            "Открытая наука и воспроизводимость",
            "Компьютерное зрение в исследованиях",
            "Математические методы моделирования",
            "Новые материалы и цифровое производство",
            "Прикладной искусственный интеллект",
            "Данные в университетских исследованиях",
            "Системы реального времени",
        ]
        conferences = []
        for index, title in enumerate(titles):
            offset = (
                8 + index * 5
                if index < 12
                else (-40 if index == 12 else -20 if index == 13 else 0)
            )
            start = today + timedelta(days=offset)
            conference, created = Conference.objects.get_or_create(
                title=title,
                defaults={
                    "description": f"Конференция «{title}» объединяет исследователей для обсуждения методов, экспериментальных результатов и практических задач. В программе — секционные доклады, разбор исследований и открытые дискуссии. Все сведения приведены для демонстрации учебного приложения.",
                    "start_date": start,
                    "end_date": start + timedelta(days=2),
                    "venue": venues[index % len(venues)],
                    "participation_terms": "Для выступления подайте название доклада и аннотацию. Участие бесплатное. Один автор может подать одну заявку на конференцию. Заявку можно изменить или отменить до дня начала. Результаты выступлений публикует организатор.",
                },
            )
            if created:
                conference.topics.set(
                    [topics[index % len(topics)], topics[(index + 1) % len(topics)]]
                )
            conferences.append(conference)
        for conference in conferences[12:14]:
            for index, author in enumerate(authors):
                Registration.objects.get_or_create(
                    author=author,
                    conference=conference,
                    defaults={
                        "title": f"Методы анализа экспериментальных данных: исследование {index + 1}",
                        "abstract": "В докладе представлены постановка задачи, методика эксперимента и результаты сравнения подходов. Все данные вымышлены.",
                        "result": Registration.Result.RECOMMENDED
                        if index % 2 == 0
                        else Registration.Result.PENDING,
                    },
                )
                if conference == conferences[12] or index < 4:
                    Review.objects.get_or_create(
                        author=author,
                        conference=conference,
                        defaults={
                            "text": "Полезные обсуждения и содержательные доклады. Особенно понравилась возможность обсудить методику исследований с участниками секции.",
                            "rating": 7 + index % 4,
                            "conference_start": conference.start_date,
                            "conference_end": conference.end_date,
                        },
                    )
        Registration.objects.get_or_create(
            author=authors[0],
            conference=conferences[0],
            defaults={
                "title": "Воспроизводимый эксперимент в распределённой среде",
                "abstract": "Сравнение стратегий обработки данных и способы проверки воспроизводимости результатов.",
            },
        )
        Registration.objects.get_or_create(
            author=authors[0],
            conference=conferences[14],
            defaults={
                "title": "Наблюдаемость систем реального времени",
                "abstract": "Обзор методов измерения задержек и контроля качества сервиса.",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {Conference.objects.count()} конференций, {Registration.objects.count()} заявок, {Review.objects.count()} отзывов. Логины: admin, organizer, researcher; пароль — DJANGO_DEMO_PASSWORD из .env."
            )
        )
