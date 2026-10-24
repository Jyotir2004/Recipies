from io import BytesIO
import os
import tempfile

from fastapi.testclient import TestClient
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from PIL import Image

from main import app

from .models import Recipe, RecipeNotification


class RecipeUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cook",
            email="cook@example.com",
            password="Strong-test-password-472!",
        )
        self.client.force_login(self.user)

    def test_upload_page_renders_form(self):
        response = self.client.get(reverse("upload_recipe"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, "Upload recipe")
        self.assertContains(response, "sauces, dips, or side dishes")

    def test_home_page_does_not_display_api_details(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "python manage.py runserver")
        self.assertNotContains(response, "API documentation")
        self.assertNotContains(response, "API is online")
        self.assertNotContains(response, "FastAPI server")
        self.assertNotContains(response, "uvicorn main:app")

    def test_valid_recipe_upload_is_saved(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "recipe.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("upload_recipe"),
                {
                    "recipe_name": "Garden soup",
                    "recipe_type": "Dinner",
                    "recipe_description": "Simmer vegetables until tender.",
                    "recipe_image": image,
                    "is_shared": "on",
                },
            )

            self.assertRedirects(response, reverse("home"))
            self.assertTrue(Recipe.objects.filter(recipe_name="Garden soup").exists())

    def test_uploaded_recipe_appears_in_list_with_image(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "recipe.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.client.post(
                reverse("upload_recipe"),
                {
                    "recipe_name": "Garden soup",
                    "recipe_type": "Dinner",
                    "recipe_description": "Simmer vegetables until tender.",
                    "recipe_image": image,
                    "is_shared": "on",
                },
            )

            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Garden soup")
        self.assertContains(response, 'src="/media/recipe/recipe.png"')
        self.assertContains(response, 'id="recipe-search"')
        self.assertContains(response, "Search food by name or description...")

    def test_recipe_can_be_deleted(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "recipe.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            recipe = Recipe.objects.create(
                user=self.user,
                recipe_name="Garden soup",
                recipe_type="Dinner",
                recipe_description="Simmer vegetables until tender.",
                recipe_image=image,
            )
            image_path = recipe.recipe_image.path

            response = self.client.post(reverse("delete_recipe", args=[recipe.pk]))

            self.assertRedirects(response, reverse("home"))
            self.assertFalse(Recipe.objects.filter(pk=recipe.pk).exists())
            self.assertFalse(os.path.exists(image_path))

    def test_recipe_can_be_updated_without_replacing_image(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            recipe = Recipe.objects.create(
                user=self.user,
                recipe_name="Garden soup",
                recipe_type="Dinner",
                recipe_description="Original description.",
            )

            response = self.client.post(
                reverse("update_recipe", args=[recipe.pk]),
                {
                    "recipe_name": "Updated garden soup",
                    "recipe_description": "Updated description.",
                },
            )

            self.assertRedirects(response, reverse("home"))
            recipe.refresh_from_db()
            self.assertEqual(recipe.recipe_name, "Updated garden soup")
            self.assertEqual(recipe.recipe_description, "Updated description.")
            self.assertEqual(recipe.recipe_type, "Dinner")

    def test_recipe_image_can_be_replaced_when_updated(self):
        def uploaded_image(filename):
            image_buffer = BytesIO()
            Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
            return SimpleUploadedFile(
                filename,
                image_buffer.getvalue(),
                content_type="image/png",
            )

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            recipe = Recipe.objects.create(
                user=self.user,
                recipe_name="Garden soup",
                recipe_type="Dinner",
                recipe_description="Original description.",
                recipe_image=uploaded_image("original.png"),
            )
            original_image_path = recipe.recipe_image.path

            response = self.client.post(
                reverse("update_recipe", args=[recipe.pk]),
                {
                    "recipe_name": "Updated garden soup",
                    "recipe_description": "Updated description.",
                    "recipe_image": uploaded_image("updated.png"),
                },
            )

            self.assertRedirects(response, reverse("home"))
            recipe.refresh_from_db()
            self.assertEqual(recipe.recipe_image.name, "recipe/updated.png")
            self.assertTrue(os.path.exists(recipe.recipe_image.path))
            self.assertFalse(os.path.exists(original_image_path))

    def test_registration_then_email_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("register"),
            {
                "username": "newcook",
                "email": "newcook@example.com",
                "password": "Strong-new-password-684!",
                "confirm_password": "Strong-new-password-684!",
            },
        )
        self.assertRedirects(response, reverse("login"))
        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"identity": "newcook@example.com", "password": "Strong-new-password-684!"},
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(username="newcook").pk)

    def test_registration_accepts_password_without_strength_rules(self):
        self.client.logout()
        response = self.client.post(
            reverse("register"),
            {
                "username": "simplepass",
                "email": "simplepass@example.com",
                "password": "x",
                "confirm_password": "x",
            },
        )
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(User.objects.filter(username="simplepass").exists())

    def test_login_and_registration_do_not_offer_google_signin(self):
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertNotContains(response, "Continue with Google")
        response = self.client.get(reverse("register"))
        self.assertNotContains(response, "Continue with Google")

    def test_recipe_actions_require_owner(self):
        other_user = User.objects.create_user(username="other", password="Other-test-password-472!")
        recipe = Recipe.objects.create(
            user=other_user,
            recipe_name="Private soup",
            recipe_type="Dinner",
            recipe_description="Secret recipe.",
        )

        response = self.client.get(reverse("update_recipe", args=[recipe.pk]))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("delete_recipe", args=[recipe.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_private_recipes_are_visible_only_to_their_owner(self):
        recipe = Recipe.objects.create(
            user=self.user,
            recipe_name="Private soup",
            recipe_type="Dinner",
            recipe_description="Only for my kitchen.",
            is_shared=False,
        )
        self.assertContains(self.client.get(reverse("home")), "Private soup")
        other_user = User.objects.create_user(username="other", password="Other-test-password-472!")
        self.client.force_login(other_user)
        self.assertNotContains(self.client.get(reverse("home")), "Private soup")
        self.assertTrue(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_recipe_ranks_and_emojis_are_visible_on_cards_and_details(self):
        Recipe.objects.create(
            user=self.user,
            recipe_name="Diamond soup",
            recipe_type="Dinner",
            recipe_description="A top-ranked recipe.",
            rank="diamond",
        )
        Recipe.objects.create(
            user=self.user,
            recipe_name="New soup",
            recipe_type="Lunch",
            recipe_description="Not ranked yet.",
        )

        response = self.client.get(reverse("home"))

        self.assertContains(response, "💎 Diamond")
        self.assertContains(response, "⚪ Unranked")
        self.assertContains(response, f'data-rank="💎 Diamond"')
        self.assertContains(response, f'data-rank="⚪ Unranked"')

    def test_logout_requires_post_and_returns_to_login(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_admin_star_creates_user_notification_and_rank_can_be_updated(self):
        recipe = Recipe.objects.create(
            user=self.user,
            recipe_name="Starred soup",
            recipe_type="Dinner",
            recipe_description="Bright tomato soup.",
        )
        admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="Strong-admin-password-432!"
        )
        self.client.force_login(admin_user)
        response = self.client.post(reverse("admin_star_recipe", args=[recipe.pk]))
        self.assertRedirects(response, reverse("admin_dashboard"))
        recipe.refresh_from_db()
        self.assertEqual(recipe.admin_stars, 1)
        self.assertEqual(RecipeNotification.objects.filter(recipe=recipe).count(), 1)
        response = self.client.post(
            reverse("admin_update_recipe", args=[recipe.pk]),
            {"rank": "diamond"},
        )
        self.assertRedirects(response, reverse("admin_dashboard"))
        recipe.refresh_from_db()
        self.assertEqual(recipe.rank, "diamond")

    def test_account_deletion_removes_owned_recipes(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
        image = SimpleUploadedFile("owned.png", image_buffer.getvalue(), content_type="image/png")
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            recipe = Recipe.objects.create(
                user=self.user,
                recipe_name="Goodbye soup",
                recipe_type="Dinner",
                recipe_description="Removed with its owner.",
                recipe_image=image,
            )
            image_path = recipe.recipe_image.path
            response = self.client.post(
                reverse("profile"),
                {"delete_account": "1", "password": "Strong-test-password-472!"},
            )
            self.assertRedirects(response, reverse("login"))
            self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
            self.assertFalse(Recipe.objects.filter(pk=recipe.pk).exists())
            self.assertFalse(os.path.exists(image_path))

    def test_admin_route_accepts_only_staff_login(self):
        self.client.logout()
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin sign in")
        response = self.client.post(
            reverse("admin_dashboard"),
            {"identity": "cook@example.com", "password": "Strong-test-password-472!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid admin credentials.")
        User.objects.create_superuser(
            username="admin", email="admin@example.com", password="Strong-admin-password-432!"
        )
        response = self.client.post(
            reverse("admin_dashboard"),
            {"identity": "admin@example.com", "password": "Strong-admin-password-432!"},
        )
        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_anonymous_home_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")


class RecipeApiTests(TransactionTestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_settings.enable()
        self.api_client = TestClient(app)

    def tearDown(self):
        self.media_settings.disable()
        self.media_directory.cleanup()

    def test_health_check(self):
        response = self.api_client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_recipe_can_be_created_and_retrieved(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
        response = self.api_client.post(
            "/recipes",
            data={
                "recipe_name": "Garden soup",
                "recipe_type": "Dinner",
                "recipe_description": "Simmer vegetables until tender.",
            },
            files={"recipe_image": ("recipe.png", image_buffer.getvalue(), "image/png")},
        )

        self.assertEqual(response.status_code, 201, response.text)
        recipe = response.json()
        self.assertEqual(recipe["recipe_name"], "Garden soup")
        self.assertEqual(recipe["recipe_type"], "Dinner")

        detail_response = self.api_client.get(f"/recipes/{recipe['id']}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json(), recipe)

    def test_api_documentation_uses_port_5000(self):
        response = self.api_client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["servers"][0]["url"],
            "http://127.0.0.1:5000",
        )

    def test_unknown_recipe_returns_404(self):
        response = self.api_client.get("/recipes/999")

        self.assertEqual(response.status_code, 404)
