import os
import random
import re
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import Database
from models import Rezept


DAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
BILDER_DIR = BASE_DIR / "bilder"

# Verhindert Startfehler, falls Ordner noch nicht existieren.
STATIC_DIR.mkdir(exist_ok=True)
BILDER_DIR.mkdir(exist_ok=True)


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


app = FastAPI(title="Rezeptroulette API")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/bilder", StaticFiles(directory=str(BILDER_DIR)), name="bilder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Database:
    return Database()

DEFAULT_USER_ID = 1

def get_weekly_plan(db):
    try:
        return db.weekly_plan(DEFAULT_USER_ID)
    except TypeError:
        return get_weekly_plan(db)

def save_weekly_plan(db, plan):
    try:
        return db.set_weekly_plan(DEFAULT_USER_ID, plan)
    except TypeError:
        return save_weekly_plan(db, plan)


def clean_text(text):
    if not text:
        return ""

    text = str(text)
    replacements = {
        "Ã¤": "ä",
        "Ã¶": "ö",
        "Ã¼": "ü",
        "ÃŸ": "ß",
        "â€“": "-",
        "â€œ": '"',
        "â€\u009d": '"',
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    return re.sub(r"\s+", " ", text).strip()


def normalize_day(day: str) -> str:
    """Akzeptiert z. B. montag, Montag oder ' Montag '."""
    cleaned = day.strip().lower()
    for valid_day in DAYS:
        if valid_day.lower() == cleaned:
            return valid_day
    raise HTTPException(status_code=404, detail="Tag nicht gefunden")


def recipe_to_dict(recipe: Rezept | None) -> dict | None:
    if recipe is None:
        return None

    data = asdict(recipe)
    if data.get("bild"):
        data["bild_url"] = f"/bilder/{data['bild']}"
    else:
        data["bild_url"] = ""
    return data


@app.get("/")
def home():
    static_index = STATIC_DIR / "index.html"
    root_index = BASE_DIR / "index.html"

    if static_index.exists():
        return FileResponse(static_index)
    if root_index.exists():
        return FileResponse(root_index)

    raise HTTPException(status_code=404, detail="index.html nicht gefunden")


@app.get("/rezepte")
def get_rezepte():
    db = get_db()
    return [recipe_to_dict(recipe) for recipe in db.all_recipes()]


@app.post("/rezept-erstellen")
def rezept_erstellen(daten: RezeptCreate):
    db = get_db()

    if not daten.name.strip():
        raise HTTPException(status_code=400, detail="Name fehlt")

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
    return recipe_to_dict(saved)


@app.post("/rezept-aus-link")
def rezept_aus_link(daten: dict):
    db = get_db()
    url = daten.get("url", "").strip()

    if not url:
        raise HTTPException(status_code=400, detail="Kein Link angegeben")

    rezept = Rezept(
        name="Importiertes Rezept",
        kueche="Link Import",
        bild="",
        portionen=2,
        kochzeit=30,
        schwierigkeit="Einfach",
        tags=["Import"],
        favorit=False,
        zutaten=["Bitte Zutaten prüfen"],
        anleitung=f"Quelle:\n{url}\n\nBitte Zutaten und Anleitung ergänzen.",
    )

    recipe_id = db.save_recipe(rezept)
    saved = db.get_recipe(recipe_id)
    return recipe_to_dict(saved)


@app.delete("/delete-pdf-recipes")
def delete_pdf_recipes():
    db = get_db()
    deleted = db.delete_pdf_imports()
    return {"deleted": deleted}


@app.delete("/rezepte/importierte")
def importierte_rezepte_loeschen():
    db = get_db()
    db.conn.execute("DELETE FROM recipes WHERE kueche = ?", ("Link Import",))
    db.conn.commit()
    return {"message": "Importierte Rezepte gelöscht"}


@app.delete("/rezepte/{recipe_id}")
def rezept_loeschen(recipe_id: int):
    db = get_db()
    recipe = db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")

    db.delete_recipe(recipe_id)
    return {"message": "Rezept gelöscht"}


@app.get("/roulette")
def roulette():
    db = get_db()
    rezepte = db.all_recipes()

    if not rezepte:
        raise HTTPException(status_code=404, detail="Keine Rezepte vorhanden")

    return recipe_to_dict(random.choice(rezepte))


@app.get("/wochenplan")
def wochenplan():
    db = get_db()
    plan = get_weekly_plan(db)
    result = {}

    for day, value in plan.items():
        recipe_id = None

        if isinstance(value, dict):
            recipe_id = value.get(1) or value.get("1")
        else:
            recipe_id = value

        if recipe_id:
            recipe = db.get_recipe(recipe_id)
            result[day] = asdict(recipe) if recipe else None
        else:
            result[day] = None

    return result


DEFAULT_USER_ID = 1
DEFAULT_SLOT = 1


@app.post("/wochenplan/reset")
def reset_wochenplan():
    db = get_db()

    for day in DAYS:
        for slot in [1, 2, 3]:
            db.set_weekly_plan_slot(DEFAULT_USER_ID, day, slot, None)

    return {"message": "Wochenplan zurückgesetzt"}


@app.post("/wochenplan/clear/{day}")
def loesche_tag(day: str):
    db = get_db()
    valid_day = normalize_day(day)

    for slot in [1, 2, 3]:
        db.set_weekly_plan_slot(DEFAULT_USER_ID, valid_day, slot, None)

    return {"message": f"{valid_day} wurde gelöscht", "day": valid_day}


@app.post("/wochenplan/{day}/{recipe_id}")
def setze_wochenplan(day: str, recipe_id: int):
    db = get_db()
    valid_day = normalize_day(day)

    recipe = db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")

    db.set_weekly_plan_slot(
        DEFAULT_USER_ID,
        valid_day,
        DEFAULT_SLOT,
        recipe_id
    )

    return {
        "message": "Gespeichert",
        "day": valid_day,
        "slot": DEFAULT_SLOT,
        "recipe_id": recipe_id,
        "recipe": recipe_to_dict(recipe),
    }
@app.post("/wochenplan/auto")
def wochenplan_auto():
    db = get_db()
    recipes = db.all_recipes()

    if not recipes:
        raise HTTPException(status_code=404, detail="Keine Rezepte vorhanden")

    plan = get_weekly_plan(db)
    used_ids = set()
    used_tags = set()

    # Bereits geplante Rezepte sammeln
    for day_plan in plan.values():
        if isinstance(day_plan, dict):
            for recipe_id in day_plan.values():
                if recipe_id:
                    used_ids.add(recipe_id)
        elif day_plan:
            used_ids.add(day_plan)

    # Tags der bereits geplanten Rezepte sammeln
    for recipe in recipes:
        if recipe.id in used_ids:
            used_tags.update(recipe.tags or [])

    available = [recipe for recipe in recipes if recipe.id not in used_ids]

    for day in DAYS:
        current = plan.get(day)

        if isinstance(current, dict):
            occupied = current.get(1) or current.get("1")
        else:
            occupied = current

        if occupied:
            continue

        if not available:
            available = recipes.copy()

        preferred = [
            recipe for recipe in available
            if not any(tag in used_tags for tag in (recipe.tags or []))
        ]

        if preferred:
            recipe = random.choice(preferred)
        else:
            recipe = random.choice(available)

        db.set_weekly_plan_slot(
            DEFAULT_USER_ID,
            day,
            DEFAULT_SLOT,
            recipe.id
        )

        used_ids.add(recipe.id)
        used_tags.update(recipe.tags or [])
        available = [r for r in available if r.id != recipe.id]

    return {"message": "Woche automatisch geplant"}

def category_for_ingredient(text: str) -> str:
    t = text.lower()

    if any(w in t for w in ["apfel", "banane", "tomate", "gurke", "paprika", "zwiebel", "kartoffel", "salat", "zucchini", "karotte", "möhre", "knoblauch"]):
        return "Obst & Gemüse"

    if any(w in t for w in ["hack", "fleisch", "hähnchen", "huhn", "rind", "schwein", "lachs", "fisch", "speck", "schinken"]):
        return "Fleisch & Fisch"

    if any(w in t for w in ["milch", "sahne", "käse", "mozzarella", "joghurt", "quark", "butter", "ei"]):
        return "Kühlregal"

    if any(w in t for w in ["nudel", "pasta", "reis", "mehl", "zucker", "brot", "tortilla", "lasagne"]):
        return "Trockenwaren & Backwaren"

    if any(w in t for w in ["dose", "tomaten", "bohnen", "mais", "passata", "sauce", "brühe", "pesto"]):
        return "Konserven & Saucen"

    if any(w in t for w in ["salz", "pfeffer", "öl", "essig", "paprika", "oregano", "curry", "chili"]):
        return "Gewürze & Vorrat"

    return "Sonstiges"


def shopping_list(recipes: list[Rezept]):
    categories: dict[str, list[str]] = {}
    pantry: list[str] = []

    for recipe in recipes:
        zutaten = recipe.zutaten or []

        if isinstance(zutaten, str):
            zutaten = [z.strip() for z in zutaten.split(",") if z.strip()]

        for zutat in zutaten:
            zutat = str(zutat).strip()
            if not zutat:
                continue

            category = category_for_ingredient(zutat)
            categories.setdefault(category, []).append(zutat)

    order = [
        "Obst & Gemüse",
        "Fleisch & Fisch",
        "Kühlregal",
        "Trockenwaren & Backwaren",
        "Konserven & Saucen",
        "Gewürze & Vorrat",
        "Sonstiges",
    ]

    sorted_categories = {}

    for category in order:
        items = categories.get(category, [])
        if items:
            sorted_categories[category] = list(dict.fromkeys(items))

    return sorted_categories, pantry


@app.get("/einkaufsliste")
def einkaufsliste():
    db = get_db()
    plan = get_weekly_plan(db)

    recipes = []

    for day_plan in plan.values():
        if isinstance(day_plan, dict):
            recipe_ids = day_plan.values()
        else:
            recipe_ids = [day_plan]

        for recipe_id in recipe_ids:
            if recipe_id:
                recipe = db.get_recipe(int(recipe_id))
                if recipe:
                    recipes.append(recipe)

    categories, pantry = shopping_list(recipes)

    return {
        "recipes": [recipe_to_dict(recipe) for recipe in recipes],
        "categories": categories,
        "pantry": pantry,
        "ingredients": [
            item
            for items in categories.values()
            for item in items
        ],
    }