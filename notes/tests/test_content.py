from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from notes.models import Note
from django.contrib.auth import get_user_model
from notes.forms import NoteForm

User = get_user_model()


class TestContent1(TestCase):

    @classmethod
    def setUpTestData(cls):
        # cls.author = User.objects.create(username='Автор заметки')
        # cls.author_client = Client()
        # cls.author_client.force_login(cls.author)
        cls.author = User.objects.create(username='Лев Толстой')
        all_notes = [
            Note(title=f'Новость {index}', text='Просто текст.', slug=f'{index}', author=cls.author)
            for index in range(1, 11)
        ]
        Note.objects.bulk_create(all_notes)
        
    def test_notes_order(self):
        self.client.force_login(self.author)
        response = self.client.get(reverse('notes:list'))
        object_list = response.context['object_list']
        # Получаем даты новостей в том порядке, как они выведены на странице.
        all_id = [notes.id for notes in object_list]
        # Сортируем полученный список по убыванию.
        expected_order = sorted(all_id, reverse=False)
        # Проверяем, что исходный список был отсортирован правильно.
        self.assertEqual(all_id, expected_order) 

    def test_authorized_client_has_form(self):
        # Авторизуем клиент при помощи ранее созданного пользователя.
        self.client.force_login(self.author)
        urls = (
            ('notes:add', None),
            ('notes:edit', '1'),
        )
        for name, arg in urls:
            with self.subTest(name=name):
                url = reverse(name, args=arg)
                response = self.client.get(url)
                self.assertIn('form', response.context)
                # Проверим, что объект формы соответствует нужному классу формы.
                self.assertIsInstance(response.context['form'], NoteForm)

    def test_note_in_list_for_author(self):
        """Заметка передаётся на страницу со списком заметок."""
        self.client.force_login(self.author)
        response = self.client.get(reverse('notes:list'))
        self.assertEqual(Note.objects.count(), 10)
        notes, ex = Note.objects.all(), response.context['object_list']
        for note in notes:
            for e in ex:
                if note.slug == e.slug:
                    self.assertEqual(note.text, e.text)
                    self.assertEqual(note.author, e.author)
                    self.assertEqual(note.title, e.title)
                    self.assertEqual(note.slug, e.slug)


class TestContent2(TestCase):

    @classmethod
    def setUpTestData(cls):
        
        cls.author = User.objects.create(username='Лев Толстой')
        cls.note = Note.objects.create(title="title", text="text", slug="slug", author=cls.author)
        cls.reader = User.objects.create(username='Пушкин')
     
    def test_note_in_list_for_author(self):
        """Заметка передаётся на страницу со списком заметок."""
        self.client.force_login(self.author)
        response = self.client.get(reverse('notes:list'))
        self.assertEqual(Note.objects.count(), len(response.context['object_list']))
        note_db, note_web = Note.objects.get(slug=self.note.slug), response.context['object_list'][0]
        self.assertEqual(note_db.text, note_web.text)
        self.assertEqual(note_db.title, note_web.title)
        self.assertEqual(note_db.slug, note_web.slug)
        self.assertEqual(note_db.author, note_web.author)

    def test_note_not_in_list_for_another_user(self):
        url = reverse('notes:list')
        self.client.force_login(self.reader)
        response = self.client.get(url)
        object_list = response.context['object_list']
        # Проверяем, что заметки нет в контексте страницы:
        print(self.note)
        self.assertNotIn(self.note, object_list)
