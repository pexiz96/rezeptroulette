import os
import random
from dataclasses import asdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import Database
from models import Rezept


class RezeptCreate(BaseModel):
    name: str
    kueche: str = "Unbekannt"
    bild: str = ""
    portionen: int = 2
    kochzeit: int = 30
    schwierigkeit: str = "Einfach"
    tags: list[str] = Field(default_factory=list)
zutaten: list[str] = Field(default_factory=list)
    anleitung: str = "Keine Anleitung vorhanden."


app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
BILDER_DIR = os.path.join(BASE_DIR, "bilder")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/bilder", StaticFiles(directory=BILDER_DIR), name="bilder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    return Database()

@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/rezepte")
def get_rezepte():
    db = get_db()
    return [asdict(r) for r in db.all_recipes()]

@app.post("/rezept-erstellen")
def rezept_erstellen(daten: RezeptCreate):
    db = get_db()

if not daten.name.strip():
        return {"error": "Name fehlt"}

    rezept = Rezept(
        name=daten.name.strip(),
        kueche=daten.kueche.strip() or "Unbekannt",
        bild=daten.bild.strip(),
        portionen=max(1, daten.portionen),
        kochzeit=max(1, daten.kochzeit),
        schwierigkeit=daten.schwierigkeit or "Einfach",
        tags=daten.tags,
        favorit=False,
        zutaten=daten.zutaten,
        anleitung=daten.anleitung.strip() or "Keine Anleitung vorhanden.",
    )

    recipe_id = db.save_recipe(rezept)
    saved = db.get_recipe(recipe_id)

    return asdict(saved)

@app.get("/roulette")
def roulette():
    db = get_db()
    rezepte = db.all_recipes()

    if not rezepte:
        return {"error": "Keine Rezepte vorhanden"}

    rezept = random.choice(rezepte)
    daten = asdict(rezept)

    daten["bild_url"] = f"/bilder/{daten['bild']}"

    return daten


@app.get("/wochenplan")
def wochenplan():
    db = get_db()
    plan = db.weekly_plan()
    result = {}

    for day, recipe_id in plan.items():
        if recipe_id:
            recipe = db.get_recipe(recipe_id)
            result[day] = asdict(recipe) if recipe else None
        else:
            result[day] = None

    return result


@app.post("/wochenplan/reset")
def reset_wochenplan():
    db = get_db()
    plan = db.weekly_plan()

    for day in plan:
        plan[day] = None

    db.set_weekly_plan(plan)
    return {"message": "Wochenplan zurückgesetzt"}


@app.post("/wochenplan/clear/{day}")
def loesche_tag(day: str):
    db = get_db()
    plan = db.weekly_plan()

    if day not in plan:
        return {"error": "Tag nicht gefunden"}

    plan[day] = None
    db.set_weekly_plan(plan)
    return {"message": f"{day} wurde gelöscht"}


@app.post("/wochenplan/{day}/{recipe_id}")
def setze_wochenplan(day: str, recipe_id: int):
    db = get_db()
    plan = db.weekly_plan()
    plan[day] = recipe_id
    db.set_weekly_plan(plan)

        if day not in plan:
        return {"error": "Tag nicht gefunden"}

    return {"message": "Gespeichert", "day": day, "recipe_id": recipe_id}


def shopping_list(recipes):
    categories = {}
    pantry = []

    for recipe in recipes:
        zutaten = getattr(recipe, "zutaten", None) or getattr(recipe, "ingredients", None) or []

        if isinstance(zutaten, str):
            zutaten = [z.strip() for z in zutaten.split(",") if z.strip()]

        for zutat in zutaten:
            categories.setdefault("Zutaten", []).append(zutat)

    return categories, pantry


@app.get("/einkaufsliste")
def einkaufsliste():
    db = get_db()
    plan = db.weekly_plan()

    recipes = []
    for recipe_id in plan.values():
        if recipe_id:
            recipe = db.get_recipe(recipe_id)
            if recipe:
                recipes.append(recipe)

    categories, pantry = shopping_list(recipes)

    return {
        "categories": categories,
        "pantry": pantry,
    }