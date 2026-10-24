import os
import sys
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict

from vege.forms import RecipeForm
from vege.models import Recipe

app = FastAPI(
    title="Recipis API",
    description=(
        "Browse, view, and upload recipes. "
        "Run locally with `uvicorn main:app --reload --port 5000`."
    ),
    version="1.0.0",
    servers=[
        {
            "url": os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:5000"),
        }
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

media_path = Path(settings.MEDIA_ROOT)
media_path.mkdir(parents=True, exist_ok=True)
app.mount(
    f"/{settings.MEDIA_URL.lstrip('/')}",
    StaticFiles(directory=media_path),
    name="media",
)


class RecipeResponse(BaseModel):
    id: int
    recipe_name: str
    recipe_type: str
    recipe_description: str
    recipe_image: str | None


def serialize_recipe(recipe: Recipe) -> RecipeResponse:
    return RecipeResponse(
        id=recipe.pk,
        recipe_name=recipe.recipe_name,
        recipe_type=recipe.recipe_type,
        recipe_description=recipe.recipe_description,
        recipe_image=recipe.recipe_image.url if recipe.recipe_image else None,
    )


@app.get("/", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recipes", response_model=list[RecipeResponse], tags=["recipes"])
def list_recipes() -> list[RecipeResponse]:
    return [serialize_recipe(recipe) for recipe in Recipe.objects.order_by("id")]


@app.get(
    "/recipes/{recipe_id}",
    response_model=RecipeResponse,
    tags=["recipes"],
)
def get_recipe(recipe_id: int) -> RecipeResponse:
    try:
        recipe = Recipe.objects.get(pk=recipe_id)
    except Recipe.DoesNotExist as exc:
        raise HTTPException(status_code=404, detail="Recipe not found.") from exc
    return serialize_recipe(recipe)


@app.post(
    "/recipes",
    response_model=RecipeResponse,
    status_code=201,
    tags=["recipes"],
)
def create_recipe(
    recipe_name: Annotated[str, Form()],
    recipe_type: Annotated[str, Form()],
    recipe_description: Annotated[str, Form()],
    recipe_image: Annotated[UploadFile, File()],
) -> RecipeResponse:
    uploaded_image = SimpleUploadedFile(
        recipe_image.filename or "recipe-image",
        recipe_image.file.read(),
        content_type=recipe_image.content_type or "application/octet-stream",
    )
    uploaded_files = MultiValueDict()
    uploaded_files.setlist("recipe_image", [uploaded_image])
    form = RecipeForm(
        data={
            "recipe_name": recipe_name,
            "recipe_type": recipe_type,
            "recipe_description": recipe_description,
        },
        files=uploaded_files,
    )
    if not form.is_valid():
        raise HTTPException(status_code=422, detail=form.errors.get_json_data())

    return serialize_recipe(form.save())
