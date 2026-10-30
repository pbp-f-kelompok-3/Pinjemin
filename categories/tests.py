
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from .models import Category


class CategoryModelTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Elektronik",
            icon_url="https://example.com/electronics.png"
        )

    def test_category_creation(self):
        self.assertEqual(self.category.name, "Elektronik")
        self.assertEqual(
            self.category.icon_url,
            "https://example.com/electronics.png"
        )

    def test_category_string_representation(self):
        self.assertEqual(str(self.category), "Elektronik")

    def test_category_nama_property(self):
        self.assertEqual(self.category.nama, "Elektronik")

    def test_category_name_is_unique(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="Elektronik")


class CategoryListViewTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Elektronik",
            icon_url="https://example.com/electronics.png"
        )

        self.url = reverse("categories:show_categories")

    def test_category_page_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_category_is_displayed(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Elektronik")

    def test_category_icon_is_displayed(self):
        response = self.client.get(self.url)

        self.assertContains(
            response,
            "https://example.com/electronics.png"
        )

    def test_empty_category_page(self):
        Category.objects.all().delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kategori belum dibuat.")

    def test_category_links_to_homepage(self):
        response = self.client.get(self.url)

        expected_url = (
            f'/?kategori={self.category.pk}#barang'
        )

        self.assertContains(response, expected_url)


class CategoryCreateViewTest(TestCase):

    def setUp(self):
        self.url = reverse("categories:create_category")

        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="testpassword123"
        )

        self.regular_user = User.objects.create_user(
            username="user",
            password="testpassword123"
        )

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_regular_user_cannot_create_category(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_create_category(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_superuser_can_create_category(self):
        self.client.force_login(self.superuser)

        response = self.client.post(self.url, {
            "name": "Elektronik",
            "icon_url": "https://example.com/electronics.png"
        })

        self.assertRedirects(
            response,
            reverse("categories:show_categories")
        )

        self.assertTrue(
            Category.objects.filter(name="Elektronik").exists()
        )

    def test_invalid_category_is_not_created(self):
        self.client.force_login(self.superuser)
        initial_count = Category.objects.count()

        response = self.client.post(self.url, {
            "name": "",
            "icon_url": ""
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Category.objects.count(), initial_count)


class CategoryUpdateViewTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Elektronik"
        )

        self.url = reverse(
            "categories:update_category",
            args=[self.category.pk]
        )

        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="testpassword123"
        )

        self.regular_user = User.objects.create_user(
            username="user",
            password="testpassword123"
        )

    def test_superuser_can_access_update_category(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_superuser_can_update_category(self):
        self.client.force_login(self.superuser)

        response = self.client.post(self.url, {
            "name": "Komputer",
            "icon_url": "https://example.com/computer.png"
        })

        self.assertRedirects(
            response,
            reverse("categories:show_categories")
        )
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Komputer")
        self.assertEqual(
            self.category.icon_url,
            "https://example.com/computer.png"
        )

    def test_regular_user_cannot_update_category(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_update_nonexistent_category_returns_404(self):
        self.client.force_login(self.superuser)

        url = reverse(
            "categories:update_category",
            args=[99999]
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class CategoryDeleteViewTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Elektronik"
        )

        self.url = reverse(
            "categories:delete_category",
            args=[self.category.pk]
        )

        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="testpassword123"
        )

        self.regular_user = User.objects.create_user(
            username="user",
            password="testpassword123"
        )

    def test_superuser_can_access_delete_confirmation(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Elektronik")

    def test_superuser_can_delete_category(self):
        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertRedirects(
            response,
            reverse("categories:show_categories")
        )

        self.assertFalse(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_get_request_does_not_delete_category(self):
        self.client.force_login(self.superuser)

        self.client.get(self.url)

        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_regular_user_cannot_delete_category(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_delete_nonexistent_category_returns_404(self):
        self.client.force_login(self.superuser)

        url = reverse(
            "categories:delete_category",
            args=[99999]
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
