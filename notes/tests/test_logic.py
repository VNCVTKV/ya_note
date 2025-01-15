from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertFormError
from notes.forms import WARNING
from pytils.translit import slugify

# Импортируем из файла с формами список стоп-слов и предупреждение формы.
# Загляните в news/forms.py, разберитесь с их назначением.
from notes.models import Note

User = get_user_model()


class TestCommentCreation(TestCase):
    # Текст комментария понадобится в нескольких местах кода, 
    # поэтому запишем его в атрибуты класса.
    NOTE_TEXT = 'Текст комментария'
    NOTE_TITLE = 'Заголовок комментария'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='Мимо Крокодил')
        # Адрес страницы с новостью.
        #cls.url = reverse('news:detail', args=(cls.news.id,))
        # Создаём пользователя и клиент, логинимся в клиенте.
        cls.auth_client = Client()
        cls.auth_client.force_login(cls.user)
        # Данные для POST-запроса при создании комментария.
        cls.form_data = {'title': cls.NOTE_TITLE, 'slug': 'new-slug', 'text': cls.NOTE_TEXT}
        cls.url = reverse('notes:add')

    def test_user_can_create_note(self):
        url = reverse('notes:add')
        # В POST-запросе отправляем данные, полученные из фикстуры form_data:
        response = self.auth_client.post(url, data=self.form_data)
        # Проверяем, что был выполнен редирект на страницу успешного добавления заметки:
        self.assertRedirects(response, reverse('notes:success'))
        # Считаем общее количество заметок в БД, ожидаем 1 заметку.
        self.assertEqual(Note.objects.count(), 1)
        # Чтобы проверить значения полей заметки - 
        # получаем её из базы при помощи метода get():
        new_note = Note.objects.get()
        # Сверяем атрибуты объекта с ожидаемыми.
        self.assertEqual(new_note.title, self.form_data['title'])
        self.assertEqual(new_note.text, self.form_data['text'])
        self.assertEqual(new_note.slug, self.form_data['slug'])
        self.assertEqual(new_note.author, self.user)
    
    def test_anonymous_user_cant_create_note(self):
        url = reverse('notes:add')
        # Через анонимный клиент пытаемся создать заметку:
        client = Client()
        response = client.post(url, data=self.form_data)
        login_url = reverse('users:login')
        expected_url = f'{login_url}?next={url}'
        # Проверяем, что произошла переадресация на страницу логина:
        self.assertRedirects(response, expected_url)
        # Считаем количество заметок в БД, ожидаем 0 заметок.
        self.assertEqual(Note.objects.count(), 0)

    def test_empty_slug(self):
        url = reverse('notes:add')
        # Убираем поле slug из словаря:
        self.form_data.pop('slug')
        response = self.auth_client.post(url, data=self.form_data)
        # Проверяем, что даже без slug заметка была создана:
        self.assertRedirects(response, reverse('notes:success'))
        self.assertEqual(Note.objects.count(), 1)
        # Получаем созданную заметку из базы:
        new_note = Note.objects.get()
        # Формируем ожидаемый slug:
        expected_slug = slugify(self.form_data['title'])
        # Проверяем, что slug заметки соответствует ожидаемому:
        self.assertEqual(new_note.slug, expected_slug)


class TestWithNote(TestCase):
    NOTE_TEXT = 'Текст комментария'
    NOTE_TITLE = 'Заголовок комментария'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='Мимо Крокодил')
        cls.reader = User.objects.create(username='Пушкин')
        # Адрес страницы с новостью.
        #cls.url = reverse('news:detail', args=(cls.news.id,))
        # Создаём пользователя и клиент, логинимся в клиенте.
        cls.auth_client = Client()
        cls.auth_client.force_login(cls.user)
        cls.not_auther_client = Client()
        cls.not_auther_client.force_login(cls.reader)
        # Данные для POST-запроса при создании комментария.
        cls.form_data = {'title': cls.NOTE_TITLE, 'slug': 'new-slug', 'text': cls.NOTE_TEXT}
        cls.url = reverse('notes:add')
        cls.note = Note.objects.create(title='Заголовок', text='Текст', slug='test', author=cls.user)

    def test_not_unique_slug(self):
        url = reverse('notes:add')
        # Подменяем slug новой заметки на slug уже существующей записи:
        self.form_data['slug'] = self.note.slug
        # Пытаемся создать новую заметку:
        response = self.auth_client.post(url, data=self.form_data)
        # Проверяем, что в ответе содержится ошибка формы для поля slug:
        self.assertFormError(response, 'form', 'slug', errors=(self.note.slug + WARNING))
        # Убеждаемся, что количество заметок в базе осталось равным 1:
        self.assertEqual(Note.objects.count(), 1)

    def test_author_can_edit_note(self):
    # Получаем адрес страницы редактирования заметки:
        url = reverse('notes:edit', args=(self.note.slug,))
        # В POST-запросе на адрес редактирования заметки
        # отправляем form_data - новые значения для полей заметки:
        response = self.auth_client.post(url, self.form_data)
        # Проверяем редирект:
        self.assertRedirects(response, reverse('notes:success'))
        # Обновляем объект заметки note: получаем обновлённые данные из БД:
        self.note.refresh_from_db()
        # Проверяем, что атрибуты заметки соответствуют обновлённым:
        self.assertEqual(self.note.title, self.form_data['title'])
        self.assertEqual(self.note.text, self.form_data['text'])
        self.assertEqual(self.note.slug, self.form_data['slug'])

    def test_other_user_cant_edit_note(self):
        url = reverse('notes:edit', args=(self.note.slug,))
        response = self.not_auther_client.post(url, self.form_data)
        # Проверяем, что страница не найдена:
        assert response.status_code == HTTPStatus.NOT_FOUND
        # Получаем новый объект запросом из БД.
        note_from_db = Note.objects.get(id=self.note.id)
        # Проверяем, что атрибуты объекта из БД равны атрибутам заметки до запроса.
        self.assertEqual(self.note.title, note_from_db.title)
        self.assertEqual(self.note.text, note_from_db.text)
        self.assertEqual(self.note.slug, note_from_db.slug)

    def test_author_can_delete_note(self):

        url = reverse('notes:delete', args=(self.note.slug,))
        response = self.auth_client.post(url)
        self.assertRedirects(response, reverse('notes:success'))
        self.assertEqual(Note.objects.count(), 0)

    def test_other_user_cant_delete_note(self):
        url = reverse('notes:delete', args=(self.note.slug,))
        response = self.not_auther_client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(Note.objects.count(), 1) 
