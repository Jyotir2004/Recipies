from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AdminRecipeForm, LoginForm, ProfileForm, RecipeForm, RecipeUpdateForm, RegistrationForm
from .models import Recipe, RecipeNotification, UserProfile


@login_required
def upload_recipe(request):
    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            return redirect("home")
    else:
        form = RecipeForm()

    return render(
        request,
        "vege/upload.html",
        {"form": form, "api_base_url": settings.RECIPIS_API_URL},
    )


@login_required
def recipis(request):
    notifications = list(
        RecipeNotification.objects.filter(user=request.user, is_read=False)
        .select_related("recipe")
        .order_by("-created_at")[:10]
    )
    if notifications:
        RecipeNotification.objects.filter(
            pk__in=[notification.pk for notification in notifications]
        ).update(is_read=True)
    return render(
        request,
        "vege/recipis.html",
        {
            "api_base_url": settings.RECIPIS_API_URL,
            "recipes": Recipe.objects.filter(
                Q(is_shared=True) | Q(user=request.user)
            ).select_related("user").order_by("-pk"),
            "recipe_types": Recipe.RECIPE_TYPES,
            "notifications": notifications,
        },
    )


@login_required
def update_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    previous_image_name = recipe.recipe_image.name

    if request.method == "POST":
        form = RecipeUpdateForm(request.POST, request.FILES, instance=recipe)
        if form.is_valid():
            updated_recipe = form.save()
            if (
                previous_image_name
                and updated_recipe.recipe_image
                and updated_recipe.recipe_image.name != previous_image_name
            ):
                default_storage.delete(previous_image_name)
            return redirect("home")
    else:
        form = RecipeUpdateForm(instance=recipe)

    return render(
        request,
        "vege/upload.html",
        {"form": form, "recipe": recipe},
    )


@require_POST
@login_required
def delete_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    recipe_image = recipe.recipe_image
    recipe.delete()
    if recipe_image:
        recipe_image.delete(save=False)
    return redirect("home")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if request.user.is_staff else "home")
    form = LoginForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        identity = form.cleaned_data["identity"]
        user_model = get_user_model()
        user = user_model.objects.filter(email__iexact=identity).first()
        username = user.get_username() if user else identity
        authenticated_user = authenticate(request, username=username, password=form.cleaned_data["password"])
        if authenticated_user is not None:
            login(request, authenticated_user)
            return redirect("admin_dashboard" if authenticated_user.is_staff else "home")
        form.add_error(None, "Invalid username/email or password.")
    return render(request, "vege/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if request.user.is_staff else "home")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user_model = get_user_model()
        with transaction.atomic():
            user = user_model.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            UserProfile.objects.create(user=user)
        messages.success(request, "Account created. Please log in.")
        return redirect("login")
    return render(request, "vege/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        if "delete_account" in request.POST:
            password = request.POST.get("password", "")
            if not request.user.check_password(password):
                messages.error(request, "Enter your password to confirm account deletion.")
                return redirect("profile")
            image_names = list(
                Recipe.objects.filter(user=request.user)
                .exclude(recipe_image="")
                .values_list("recipe_image", flat=True)
            )
            if profile.avatar_image:
                image_names.append(profile.avatar_image.name)
            with transaction.atomic():
                request.user.delete()
            for image_name in image_names:
                default_storage.delete(image_name)
            logout(request)
            return redirect("login")
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            old_image_name = profile.avatar_image.name if profile.avatar_image else ""
            updated_profile = form.save()
            if old_image_name and updated_profile.avatar_image.name != old_image_name:
                default_storage.delete(old_image_name)
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "vege/profile.html", {"form": form})


def _is_admin(user):
    return user.is_authenticated and user.is_staff


def admin_dashboard(request):
    if not _is_admin(request.user):
        if request.method == "POST":
            form = LoginForm(request.POST)
            if form.is_valid():
                identity = form.cleaned_data["identity"]
                user_model = get_user_model()
                user = user_model.objects.filter(email__iexact=identity).first()
                username = user.get_username() if user else identity
                authenticated_user = authenticate(
                    request, username=username, password=form.cleaned_data["password"]
                )
                if authenticated_user is not None and authenticated_user.is_staff:
                    login(request, authenticated_user)
                    return redirect("admin_dashboard")
                form.add_error(None, "Invalid admin credentials.")
        else:
            form = LoginForm()
        return render(request, "vege/admin.html", {"form": form, "is_admin": False})

    recipes = Recipe.objects.select_related("user").order_by("-pk")
    users = get_user_model().objects.prefetch_related("recipe_set").order_by("username")
    return render(
        request,
        "vege/admin.html",
        {
            "is_admin": True,
            "recipes": recipes,
            "users": users,
            "rank_choices": Recipe.RANK_CHOICES,
        },
    )


@require_POST
@user_passes_test(_is_admin, login_url="admin_dashboard")
def admin_update_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    form = AdminRecipeForm(request.POST, instance=recipe)
    if form.is_valid():
        form.save()
        messages.success(request, f"Rank updated for {recipe.recipe_name}.")
    else:
        messages.error(request, "Choose a valid recipe rank.")
    return redirect("admin_dashboard")


@require_POST
@user_passes_test(_is_admin, login_url="admin_dashboard")
def admin_star_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    Recipe.objects.filter(pk=recipe.pk).update(admin_stars=F("admin_stars") + 1)
    if recipe.user is not None:
        RecipeNotification.objects.create(user=recipe.user, recipe=recipe)
    messages.success(request, f"Admin star added to {recipe.recipe_name}.")
    return redirect("admin_dashboard")


@require_POST
@user_passes_test(_is_admin, login_url="admin_dashboard")
def admin_delete_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    image = recipe.recipe_image
    recipe.delete()
    if image:
        image.delete(save=False)
    messages.success(request, "Recipe deleted.")
    return redirect("admin_dashboard")