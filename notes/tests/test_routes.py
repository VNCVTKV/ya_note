from http import HTTPStatus

from django.test import TestCase, Client
from django.urls import reverse
from notes.models import Note
from django.contrib.auth import get_user_model

User = get_user_model()


class TestRoutes(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Лев Толстой',)
        cls.note = Note.objects.create(title='Заголовок', text='Текст', slug='test', author=cls.author)
        cls.auth_author = Client()
        cls.auth_author.force_login(cls.author)
        cls.auth_reader = Client()
        cls.reader = User.objects.create(username='Пушкинс',)
        cls.auth_reader.force_login(cls.reader)

    def test_pages_availability(self):
        urls = (
            'notes:home',
            'users:login',
            'users:logout',
            'users:signup',
        )
        for name in urls:
            with self.subTest(name=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_availability_auth_user(self):
        urls = (
            'notes:add',
            'notes:list',
            'notes:success',
        )
        for name in urls:
            with self.subTest(name=name):
                url = reverse(name)
                response = self.auth_reader.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)
        
    def test_redirect_for_anonymous_client(self):
        # Сохраняем адрес страницы логина:
        login_url = reverse('users:login')
        # В цикле перебираем имена страниц, с которых ожидаем редирект:
        for name, args in (
                ('notes:edit', [self.note.slug]),
                ('notes:delete', [self.note.slug]),
                ('notes:detail', [self.note.slug]), 
                ('notes:list', None),
                ('notes:add', None),
                ('notes:success', None),
        ):
            with self.subTest(name=name):
                # Получаем адрес страницы редактирования или удаления комментария:
                url = reverse(name, args=args)
                # Получаем ожидаемый адрес страницы логина, 
                # на который будет перенаправлен пользователь.
                # Учитываем, что в адресе будет параметр next, в котором передаётся
                # адрес страницы, с которой пользователь был переадресован.
                redirect_url = f'{login_url}?next={url}'
                response = self.client.get(url)
                # Проверяем, что редирект приведёт именно на указанную ссылку.
                self.assertRedirects(response, redirect_url) 

    def test_availability_for_comment_edit_and_delete(self):
        users_statuses = (
            (self.auth_author, HTTPStatus.OK),
            (self.auth_reader, HTTPStatus.NOT_FOUND),
        )
        for user, status in users_statuses:
            # Логиним пользователя в клиенте:
            # Для каждой пары "пользователь - ожидаемый ответ"
            # перебираем имена тестируемых страниц:
            for name, args in (
                ('notes:edit', [self.note.slug]),
                ('notes:delete', [self.note.slug]),
                ('notes:detail', [self.note.slug]), 
            ):
                with self.subTest(user=user, name=name):        
                    url = reverse(name, args=args)
                    response = user.get(url)
                    self.assertEqual(response.status_code, status)
        
    