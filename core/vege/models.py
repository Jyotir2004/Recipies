from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    AVATAR_CHOICES = [
        ("👩‍🍳", "Chef"),
        ("🧑‍🍳", "Cook"),
        ("🥑", "Avocado"),
        ("🍓", "Strawberry"),
        ("🍋", "Lemon"),
        ("🍄", "Mushroom"),
        ("🐱", "Cat"),
        ("🐼", "Panda"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar_emoji = models.CharField(max_length=12, choices=AVATAR_CHOICES, default="👩‍🍳")
    avatar_image = models.ImageField(upload_to="avatars", blank=True)


class Recipe(models.Model):
    RECIPE_TYPES = [
        ("Breakfast", "Breakfast"),
        ("Lunch", "Lunch"),
        ("Dinner", "Dinner"),
        ("Snack", "Snack"),
        ("Dessert", "Dessert"),
        ("Other", "Other"),
    ]

    RANK_CHOICES = [
        ("", "⚪ Unranked"),
        ("diamond", "💎 Diamond"),
        ("gold", "🥇 Gold"),
        ("silver", "🥈 Silver"),
        ("bronze", "🥉 Bronze"),
        ("copper", "🟤 Copper"),
        ("iron", "⚙️ Iron"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    recipe_name  = models.CharField(max_length=100)
    recipe_type = models.CharField(
        max_length=20,
        choices=RECIPE_TYPES,
        default="Other",
    )
    recipe_description = models.TextField()
    recipe_image = models.ImageField(upload_to='recipe')
    is_shared = models.BooleanField(default=True)
    admin_stars = models.PositiveIntegerField(default=0)
    rank = models.CharField(max_length=10, choices=RANK_CHOICES, blank=True, default="")


class RecipeNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipe_notifications")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
