from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Recipe, UserProfile


class RegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "Choose a username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Create a password"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Enter it again"}),
        label="Confirm password",
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("That email address is already in use.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            self.add_error("confirm_password", "The passwords do not match.")
        return cleaned_data


class LoginForm(forms.Form):
    identity = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "Username or email"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "Password"})
    )

    def clean_identity(self):
        return self.cleaned_data["identity"].strip()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("avatar_emoji", "avatar_image")


class AdminRecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ("rank",)


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ("recipe_name", "recipe_type", "recipe_description", "recipe_image", "is_shared")
        widgets = {
            "recipe_name": forms.TextInput(attrs={"placeholder": "e.g. Garden Veggie Bowl"}),
            "recipe_description": forms.Textarea(
                attrs={"placeholder": "Share the ingredients and steps...", "rows": 6}
            ),
        }
        help_texts = {
            "recipe_type": "Choose Other for recipes like sauces, dips, or side dishes.",
        }


class RecipeUpdateForm(forms.ModelForm):
    recipe_image = forms.ImageField(required=False)

    class Meta:
        model = Recipe
        fields = ("recipe_name", "recipe_description", "recipe_image", "is_shared")
        widgets = {
            "recipe_name": forms.TextInput(attrs={"placeholder": "e.g. Garden Veggie Bowl"}),
            "recipe_description": forms.Textarea(
                attrs={"placeholder": "Share the ingredients and steps...", "rows": 6}
            ),
        }
