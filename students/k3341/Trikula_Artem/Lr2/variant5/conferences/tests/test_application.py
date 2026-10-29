from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from conferences import services
from conferences.forms import RegistrationAdminForm
from conferences.models import Conference, Registration, Review, Topic, Venue


class ConferenceApplicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.author = get_user_model().objects.create_user(
            username="author",
            first_name="Анна",
            last_name="Морозова",
            password="Strong-Research-2026",
        )
        cls.other = get_user_model().objects.create_user(
            username="other", password="Strong-Research-2026"
        )
        cls.organizer = get_user_model().objects.create_user(
            username="organizer", is_staff=True, password="Strong-Research-2026"
        )
        cls.organizer.user_permissions.set(
            Permission.objects.filter(content_type__app_label="conferences")
        )
        cls.staff_without_permissions = get_user_model().objects.create_user(
            username="staff", is_staff=True
        )
        cls.topic = Topic.objects.create(name="Информатика")
        cls.other_topic = Topic.objects.create(name="Биология")
        cls.venue = Venue.objects.create(
            name="Учебный центр",
            city="Тестовый город",
            address="Вымышленный адрес",
            description="Описание площадки",
        )
        cls.upcoming = cls.conference("Будущая конференция", 10)
        cls.past = cls.conference("Прошедшая конференция", -10)
        cls.ongoing = cls.conference("Конференция сегодня", 0)
        cls.past_registration = Registration.objects.create(
            author=cls.author,
            conference=cls.past,
            title="Завершённый доклад",
            abstract="Аннотация",
        )

    @classmethod
    def conference(cls, title, offset):
        conference = Conference.objects.create(
            title=title,
            description="Исследования и эксперименты",
            start_date=cls.today + timedelta(days=offset),
            end_date=cls.today + timedelta(days=offset + 2),
            participation_terms="Открытые доклады",
            venue=cls.venue,
        )
        conference.topics.add(cls.topic)
        return conference

    def login(self, user=None):
        self.client.force_login(user or self.author)

    def registration_data(self):
        return {
            "title": "Исследование данных",
            "abstract": "Описание метода и результатов",
        }

    def test_jinja_catalog_detail_and_login_render(self):
        for url in (
            reverse("conferences:catalog"),
            self.upcoming.get_absolute_url(),
            reverse("login"),
            reverse("accounts:signup"),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'lang="ru"')
            self.assertNotContains(response, "{{")
        self.assertContains(
            self.client.get(reverse("accounts:signup")), 'name="csrfmiddlewaretoken"'
        )
        self.assertContains(
            self.client.get(self.upcoming.get_absolute_url()), "Вымышленный адрес"
        )
        self.assertContains(
            self.client.get(self.upcoming.get_absolute_url()), "Открытые доклады"
        )

    def test_signup_hashes_password_and_cannot_set_privileges(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "newauthor",
                "first_name": "Иван",
                "last_name": "Орлов",
                "email": "ivan@example.test",
                "organization": "Университет",
                "password1": "Research-Secure-739!",
                "password2": "Research-Secure-739!",
                "is_staff": "on",
                "is_superuser": "on",
            },
        )
        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="newauthor")
        self.assertTrue(user.check_password("Research-Secure-739!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "weak",
                "first_name": "Имя",
                "last_name": "Фамилия",
                "email": "weak@example.test",
                "password1": "123",
                "password2": "123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="weak").exists())

    def test_login_and_logout(self):
        self.assertRedirects(
            self.client.post(
                reverse("login"),
                {"username": "author", "password": "Strong-Research-2026"},
            ),
            reverse("conferences:catalog"),
        )
        self.assertContains(
            self.client.get(reverse("conferences:my_registrations")),
            "Завершённый доклад",
        )
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))

    def test_catalog_search_topic_venue_and_phase_combined(self):
        self.upcoming.topics.add(self.other_topic)
        response = self.client.get(
            reverse("conferences:catalog"),
            {
                "q": "Будущая",
                "topic": self.topic.pk,
                "venue": self.venue.pk,
                "phase": "upcoming",
            },
        )
        self.assertContains(response, "Будущая конференция")
        self.assertNotContains(response, "Прошедшая конференция</a>")
        self.assertContains(
            response, "Найдено конференций: <strong>1</strong>", html=True
        )

    def test_pagination_preserves_filters_and_invalid_page_is_safe(self):
        for number in range(8):
            self.conference(f"Новый доклад {number}", 20 + number)
        response = self.client.get(
            reverse("conferences:catalog"), {"q": "Новый", "phase": "upcoming"}
        )
        self.assertContains(response, "Страница 1 из 2")
        self.assertContains(response, "phase=upcoming")
        self.assertEqual(
            self.client.get(
                reverse("conferences:catalog"), {"page": "bad"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("conferences:catalog"), {"topic": "not-an-id"}
            ).status_code,
            200,
        )

    def test_guest_cannot_submit(self):
        response = self.client.post(
            reverse("conferences:registration_create", args=[self.upcoming.pk]),
            self.registration_data(),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Registration.objects.filter(conference=self.upcoming).exists())

    def test_registration_create_edit_and_cancel(self):
        self.login()
        response = self.client.post(
            reverse("conferences:registration_create", args=[self.upcoming.pk]),
            self.registration_data()
            | {"author": self.other.pk, "result": "recommended"},
        )
        self.assertRedirects(response, reverse("conferences:my_registrations"))
        registration = Registration.objects.get(
            author=self.author, conference=self.upcoming
        )
        self.assertEqual(registration.result, Registration.Result.PENDING)
        self.client.post(
            reverse("conferences:registration_edit", args=[registration.pk]),
            self.registration_data() | {"title": "Обновлённый доклад"},
        )
        registration.refresh_from_db()
        self.assertEqual(registration.title, "Обновлённый доклад")
        delete_url = reverse("conferences:registration_delete", args=[registration.pk])
        self.assertEqual(self.client.get(delete_url).status_code, 200)
        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())
        self.assertRedirects(
            self.client.post(delete_url), reverse("conferences:my_registrations")
        )
        self.assertFalse(Registration.objects.filter(pk=registration.pk).exists())

    def test_registration_duplicate_handled_without_server_error(self):
        self.login()
        url = reverse("conferences:registration_create", args=[self.upcoming.pk])
        self.client.post(url, self.registration_data())
        self.assertEqual(
            self.client.post(url, self.registration_data()).status_code, 200
        )
        self.assertEqual(
            Registration.objects.filter(
                author=self.author, conference=self.upcoming
            ).count(),
            1,
        )

    def test_registration_closed_on_start_day(self):
        self.login()
        response = self.client.post(
            reverse("conferences:registration_create", args=[self.ongoing.pk]),
            self.registration_data(),
        )
        self.assertContains(response, "конференция уже началась")
        self.assertFalse(Registration.objects.filter(conference=self.ongoing).exists())

    def test_existing_registration_cannot_change_or_cancel_after_start(self):
        self.login()
        edit_url = reverse(
            "conferences:registration_edit", args=[self.past_registration.pk]
        )
        self.assertEqual(
            self.client.post(edit_url, self.registration_data()).status_code, 200
        )
        self.past_registration.refresh_from_db()
        self.assertEqual(self.past_registration.title, "Завершённый доклад")
        delete_url = reverse(
            "conferences:registration_delete", args=[self.past_registration.pk]
        )
        self.assertEqual(self.client.post(delete_url).status_code, 200)
        self.assertTrue(
            Registration.objects.filter(pk=self.past_registration.pk).exists()
        )

    def test_foreign_registration_cannot_be_read_edited_or_cancelled(self):
        self.login(self.other)
        for name in ("registration_edit", "registration_delete"):
            self.assertEqual(
                self.client.post(
                    reverse(f"conferences:{name}", args=[self.past_registration.pk]),
                    self.registration_data(),
                ).status_code,
                404,
            )
        self.assertNotContains(
            self.client.get(reverse("conferences:my_registrations")),
            "Завершённый доклад",
        )

    def test_unique_registration_enforced_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Registration.objects.create(
                author=self.author, conference=self.past, **self.registration_data()
            )

    def test_conference_dates_enforced_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Conference.objects.filter(pk=self.upcoming.pk).update(
                end_date=self.upcoming.start_date - timedelta(days=1)
            )

    def test_review_by_participant_after_end(self):
        self.login()
        response = self.client.post(
            reverse("conferences:review_create", args=[self.past.pk]),
            {
                "rating": 9,
                "text": "Содержательные доклады",
                "author": self.other.pk,
                "conference_start": "1900-01-01",
            },
        )
        self.assertRedirects(response, self.past.get_absolute_url())
        review = Review.objects.get(author=self.author, conference=self.past)
        self.assertEqual(review.conference_start, self.past.start_date)
        self.assertEqual(review.conference_end, self.past.end_date)

    def test_review_requires_participation_and_finished_conference(self):
        with self.assertRaises(ValidationError):
            services.save_review(
                author=self.other,
                conference_id=self.past.pk,
                data={"rating": 8, "text": "Нет участия"},
            )
        Registration.objects.create(
            author=self.author, conference=self.upcoming, **self.registration_data()
        )
        with self.assertRaises(ValidationError):
            services.save_review(
                author=self.author,
                conference_id=self.upcoming.pk,
                data={"rating": 8, "text": "Слишком рано"},
            )

    def test_review_cannot_be_added_on_last_day(self):
        Registration.objects.create(
            author=self.author, conference=self.ongoing, **self.registration_data()
        )
        with patch(
            "conferences.rules.timezone.localdate", return_value=self.ongoing.end_date
        ):
            with self.assertRaises(ValidationError):
                services.save_review(
                    author=self.author,
                    conference_id=self.ongoing.pk,
                    data={"rating": 8, "text": "Ещё идёт"},
                )

    def test_review_edit_preserves_snapshot(self):
        review = services.save_review(
            author=self.author,
            conference_id=self.past.pk,
            data={"rating": 8, "text": "Первый отзыв"},
        )
        snapshot = (review.conference_start, review.conference_end)
        Conference.objects.filter(pk=self.past.pk).update(
            start_date=self.past.start_date - timedelta(days=2)
        )
        self.login()
        response = self.client.post(
            reverse("conferences:review_edit", args=[review.pk]),
            {"rating": 10, "text": "Уточнённый отзыв"},
        )
        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertEqual((review.conference_start, review.conference_end), snapshot)
        self.assertEqual(review.rating, 10)

    def test_review_duplicate_and_foreign_edit(self):
        review = services.save_review(
            author=self.author,
            conference_id=self.past.pk,
            data={"rating": 8, "text": "Отзыв"},
        )
        self.login()
        response = self.client.post(
            reverse("conferences:review_create", args=[self.past.pk]),
            {"rating": 7, "text": "Дубликат"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 1)
        self.login(self.other)
        self.assertEqual(
            self.client.post(
                reverse("conferences:review_edit", args=[review.pk]),
                {"rating": 1, "text": "Чужой"},
            ).status_code,
            404,
        )

    def test_review_rating_and_result_enforced_by_database(self):
        for rating in (0, 11):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Review.objects.create(
                    author=self.author,
                    conference=self.past,
                    rating=rating,
                    text="Ошибка",
                    conference_start=self.past.start_date,
                    conference_end=self.past.end_date,
                )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Registration.objects.filter(pk=self.past_registration.pk).update(
                result="unexpected"
            )

    def test_organizer_can_change_result_in_client_interface(self):
        self.login(self.organizer)
        response = self.client.post(
            reverse("conferences:publication_result", args=[self.past_registration.pk]),
            {"result": "recommended"},
        )
        self.assertRedirects(response, reverse("conferences:participants"))
        self.past_registration.refresh_from_db()
        self.assertEqual(self.past_registration.result, Registration.Result.RECOMMENDED)

    def test_staff_flag_does_not_grant_business_permissions(self):
        for user in (self.author, self.staff_without_permissions):
            self.login(user)
            for name in ("participants", "conference_create"):
                self.assertEqual(
                    self.client.get(reverse(f"conferences:{name}")).status_code, 403
                )
            self.assertEqual(
                self.client.post(
                    reverse(
                        "conferences:publication_result",
                        args=[self.past_registration.pk],
                    ),
                    {"result": "recommended"},
                ).status_code,
                403,
            )
            with self.assertRaises(PermissionDenied):
                services.set_publication_result(
                    actor=user,
                    registration_id=self.past_registration.pk,
                    result="recommended",
                )

    def test_participants_filter_and_permissions_in_navigation(self):
        self.login()
        self.assertNotContains(
            self.client.get(reverse("conferences:catalog")),
            "Участники и результаты</a>",
        )
        self.login(self.organizer)
        response = self.client.get(
            reverse("conferences:participants"),
            {"conference": self.past.pk, "q": "Морозова"},
        )
        self.assertContains(response, "Завершённый доклад")
        self.assertContains(response, "Указать результат")

    def test_conference_create_and_edit_with_topics(self):
        self.login(self.organizer)
        payload = {
            "title": "Новая конференция",
            "description": "Описание",
            "start_date": str(self.today + timedelta(days=30)),
            "end_date": str(self.today + timedelta(days=32)),
            "participation_terms": "Условия",
            "venue": self.venue.pk,
            "topics": [self.topic.pk],
        }
        response = self.client.post(reverse("conferences:conference_create"), payload)
        conference = Conference.objects.get(title="Новая конференция")
        self.assertRedirects(response, conference.get_absolute_url())
        self.assertEqual(list(conference.topics.all()), [self.topic])
        payload["title"] = "Обновлённая конференция"
        payload["topics"] = [self.other_topic.pk]
        self.assertEqual(
            self.client.post(
                reverse("conferences:conference_edit", args=[conference.pk]), payload
            ).status_code,
            302,
        )
        conference.refresh_from_db()
        self.assertEqual(conference.title, payload["title"])
        self.assertEqual(list(conference.topics.all()), [self.other_topic])

    def test_admin_can_set_result_after_conference_finished(self):
        self.login(self.organizer)
        response = self.client.post(
            reverse(
                "admin:conferences_registration_change",
                args=[self.past_registration.pk],
            ),
            {
                "title": self.past_registration.title,
                "abstract": self.past_registration.abstract,
                "result": "not_recommended",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.past_registration.refresh_from_db()
        self.assertEqual(
            self.past_registration.result, Registration.Result.NOT_RECOMMENDED
        )

    def test_admin_cannot_create_late_registration_or_edit_closed_talk(self):
        form = RegistrationAdminForm(
            data={
                "author": self.other.pk,
                "conference": self.past.pk,
                "title": "Поздняя заявка",
                "abstract": "Текст",
                "result": "pending",
            }
        )
        self.assertFalse(form.is_valid())
        form = RegistrationAdminForm(
            instance=self.past_registration,
            data={
                "author": self.author.pk,
                "conference": self.past.pk,
                "title": "Изменённый доклад",
                "abstract": "Текст",
                "result": "pending",
            },
        )
        self.assertFalse(form.is_valid())

    def test_csrf_and_user_content_escaping(self):
        self.upcoming.title = "<script>alert(1)</script>"
        self.upcoming.save()
        response = self.client.get(self.upcoming.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.author)
        self.assertEqual(
            client.post(
                reverse("conferences:registration_create", args=[self.upcoming.pk]),
                self.registration_data(),
            ).status_code,
            403,
        )

    def test_demo_command_repeatable_and_preserves_password(self):
        with patch.dict("os.environ", {"DJANGO_DEMO_PASSWORD": "Demo-Strong-123!"}):
            call_command("seed_demo", stdout=StringIO())
            counts = (
                Conference.objects.count(),
                Registration.objects.count(),
                Review.objects.count(),
            )
            user = get_user_model().objects.get(username="researcher")
            user.set_password("Changed-Strong-123!")
            user.save()
            call_command("seed_demo", stdout=StringIO())
            self.assertEqual(
                counts,
                (
                    Conference.objects.count(),
                    Registration.objects.count(),
                    Review.objects.count(),
                ),
            )
            user.refresh_from_db()
            self.assertTrue(user.check_password("Changed-Strong-123!"))

    def test_personal_registration_filters_and_pagination(self):
        self.login()
        for index in range(8):
            conference = self.conference(f"Секция {index}", 40 + index)
            Registration.objects.create(
                author=self.author,
                conference=conference,
                title=f"Фильтруемый доклад {index}",
                abstract="Текст",
            )
        response = self.client.get(
            reverse("conferences:my_registrations"),
            {"q": "Фильтруемый", "result": "pending"},
        )
        self.assertContains(response, "Страница 1 из 2")
        self.assertContains(response, "result=pending")
        self.assertNotContains(response, "Завершённый доклад")
        response = self.client.get(
            reverse("conferences:my_registrations"), {"result": "recommended"}
        )
        self.assertNotContains(response, "Фильтруемый доклад")

    def test_review_search_and_rating_filters(self):
        services.save_review(
            author=self.author,
            conference_id=self.past.pk,
            data={"rating": 9, "text": "Полезные методы"},
        )
        Registration.objects.create(
            author=self.other, conference=self.past, **self.registration_data()
        )
        services.save_review(
            author=self.other,
            conference_id=self.past.pk,
            data={"rating": 6, "text": "Другое впечатление"},
        )
        response = self.client.get(
            self.past.get_absolute_url(), {"q": "методы", "rating": 9}
        )
        self.assertContains(response, "Полезные методы")
        self.assertNotContains(response, "Другое впечатление")
        self.assertContains(response, "Средняя оценка 7.5/10")
        self.assertEqual(
            self.client.get(
                self.past.get_absolute_url(), {"rating": "invalid"}
            ).status_code,
            200,
        )

    def test_unique_review_enforced_by_database(self):
        review = services.save_review(
            author=self.author,
            conference_id=self.past.pk,
            data={"rating": 8, "text": "Первый"},
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(
                author=self.author,
                conference=self.past,
                rating=9,
                text="Дубликат",
                conference_start=review.conference_start,
                conference_end=review.conference_end,
            )
