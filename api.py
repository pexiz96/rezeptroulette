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

import re

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
        "â€œ": "\"",
        "â€": "\"",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def normalize_ingredient_name(text):
    text = str(text).lower().strip()

    text = clean_text(text)

    text = text.replace("–", "-")
    text = text.replace("oder", " ")
    text = text.replace("nach wahl", "")
    text = text.replace("optional", "")
    text = text.replace("belieben", "")

    text = re.sub(r"\d+\s*[-–]\s*\d+", "", text)
    text = re.sub(r"\d+[.,]?\d*", "", text)

    text = re.sub(
        r"\b(g|kg|ml|l|el|tl|stück|stk|dose|dosen|tüte|packung|päckchen|prise|bund|glas|becher)\b",
        "",
        text
    )

    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^a-zäöüß\s-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    replacements = {
        "tomaten": "tomate",
        "gehackte tomaten": "tomate",
        "tomatensauce": "tomate",
        "tomatenmark": "tomatenmark",

        "zwiebel": "zwiebel",
        "zwiebeln": "zwiebel",

        "eier": "ei",
        "eigelb": "ei",

        "hähnchenbrust": "hähnchen",
        "hähnchen": "hähnchen",
        "hähnchen oder hackfleisch": "hähnchen/hackfleisch",

        "käse": "käse",
        "geriebener käse": "käse",
        "light-reibekäse": "käse",

        "skyr": "skyr",
        "magerquark": "magerquark",
        "frischkäse": "frischkäse",

        "nudeln": "nudeln",
        "wraps": "wrap",
        "low-carb-wrap": "wrap",
        "bagels": "bagel",

        "olivenöl": "öl",
        "öl": "öl",

        "zucker": "zucker",
        "erythrit": "zuckerersatz",

        "mehl": "mehl",
        "dinkelmehl": "mehl",

        "backpulver": "backpulver",
        "zimt": "zimt",
        "salz": "salz",
        "pfeffer": "pfeffer",
        "oregano": "oregano",
    }

    return replacements.get(text, text)

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

@app.delete("/delete-pdf-recipes")
def delete_pdf_recipes():
    db = get_db()
    deleted = db.delete_pdf_imports()
    return {"deleted": deleted}

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
@app.post("/rezept-aus-link")
def rezept_aus_link(daten: dict):
    db = get_db()
    url = daten.get("url", "").strip()

    if not url:
        return {"error": "Kein Link angegeben"}

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
        anleitung=f"Quelle:\n{url}\n\nBitte Zutaten und Anleitung ergänzen."
    )

    recipe_id = db.save_recipe(rezept)
    saved = db.get_recipe(recipe_id)

    return asdict(saved)
@app.delete("/rezepte/{recipe_id}")
def rezept_loeschen(recipe_id: int):
    db = get_db()
    db.delete_recipe(recipe_id)
    return {"message": "Rezept gelöscht"}

@app.delete("/rezepte/importierte")
def importierte_rezepte_loeschen():
    db = get_db()
    db.conn.execute("DELETE FROM recipes WHERE kueche = ?", ("Link Import",))
    db.conn.commit()
    return {"message": "Importierte Rezepte gelöscht"}
    
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
    return db.weekly_plan()
    



@app.post("/wochenplan/reset")
def reset_wochenplan():
    db = get_db()

    days = [
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag"
    ]

    for day in days:
        for slot in [1, 2, 3]:
            db.set_weekly_plan_slot(day, slot, None)

    return {"message": "Wochenplan geleert"}


@app.post("/wochenplan/clear/{day}")
def loesche_tag(day: str):
    db = get_db()

    for slot in [1, 2, 3]:
        db.set_weekly_plan_slot(day, slot, None)

    return {"message": f"{day} wurde gelöscht"}


@app.post("/wochenplan/{day}/{slot}/{recipe_id}")
def set_weekly_plan(day: str, slot: int, recipe_id: int):
    db = get_db()
    db.set_weekly_plan_slot(day, slot, recipe_id)
    return {"ok": True}

def parse_ingredient(text):
    original = str(text).strip()
    cleaned = clean_text(original).lower()

    cleaned = cleaned.replace("–", "-")
    cleaned = cleaned.replace(" ca. ", " ")
    cleaned = cleaned.replace("ca. ", "")
    cleaned = cleaned.replace("optional", "")
    cleaned = cleaned.replace("nach wahl", "")
    cleaned = cleaned.replace("nach belieben", "")
    cleaned = cleaned.replace("nach belieben", "")

    match = re.match(
        r"^(\d+(?:[.,]\d+)?)(?:\s*-\s*\d+(?:[.,]\d+)?)?\s*(g|kg|ml|l|el|tl|stück|stk|dose|dosen|scheiben|tüte|packung|päckchen)?\s+(.+)$",
        cleaned
    )

    if not match:
        name = normalize_ingredient_name(cleaned)
        return {
            "original": original,
            "amount": None,
            "unit": "",
            "name": name,
        }

    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2) or ""
    name = normalize_ingredient_name(match.group(3))

    unit_map = {
        "stk": "stück",
        "dose": "dose",
        "dosen": "dose",
    }

    unit = unit_map.get(unit, unit)

    name_map = {
    # Eier
    "ei": "ei",
    "eier": "ei",
    "eigelb": "ei",

    # Zwiebeln
    "zwiebel": "zwiebel",
    "zwiebeln": "zwiebel",
    "rote zwiebel": "zwiebel",
    "kleine zwiebel": "zwiebel",

    # Knoblauch
    "knoblauch": "knoblauch",
    "knoblauchzehe": "knoblauch",
    "knoblauchzehen": "knoblauch",

    # Tomaten
    "tomate": "tomate",
    "tomaten": "tomate",
    "gehackte tomaten": "tomate",
    "dose tomaten": "tomate",

    # Paprika
    "paprika": "paprika",
    "rote paprika": "paprika",
    "kleine paprika": "paprika",

    # Käse
    "käse": "käse",
    "geriebener käse": "käse",
    "scheiben käse": "käse",
    "light-reibekäse": "käse",

    # Backwaren
    "wrap": "wrap",
    "wraps": "wrap",
    "low-carb-wrap": "wrap",

    "bagel": "bagel",
    "bagels": "bagel",

    # Gewürze
    "salz": "salz",
    "pfeffer": "pfeffer",
    "muskat": "muskat",
    "oregano": "oregano",

    # Öle
    "öl": "öl",
    "olivenöl": "öl",
    "butter": "butter",

    # Backzutaten
    "backpulver": "backpulver",
    "mehl": "mehl",
    "dinkelmehl": "mehl",
    "weizenmehl": "mehl",

    # Milchprodukte
    "skyr": "skyr",
    "magerquark": "magerquark",
    "frischkäse": "frischkäse",
    "hüttenkäse": "hüttenkäse",
    "sahne": "sahne",
    "milch": "milch",
}
    name = name_map.get(name, name)

    return {
        "original": original,
        "amount": amount,
        "unit": unit,
        "name": name,
    }

def shopping_list(recipes):
    categories = {}
    pantry = []
    ingredient_map = {}

    for recipe in recipes:
        zutaten = getattr(recipe, "zutaten", None) or getattr(recipe, "ingredients", None) or []

        if isinstance(zutaten, str):
            zutaten = [z.strip() for z in zutaten.split(",") if z.strip()]

        for zutat in zutaten:
            parsed = parse_ingredient(zutat)

            key = f'{parsed["name"]}|{parsed["unit"]}'

            if key not in ingredient_map:
                ingredient_map[key] = {
                    "name": parsed["name"],
                    "unit": parsed["unit"],
                    "amount": parsed["amount"],
                    "examples": [parsed["original"]],
                    "count": 1
                }
            else:
                existing = ingredient_map[key]

                if existing["amount"] is not None and parsed["amount"] is not None:
                    existing["amount"] += parsed["amount"]
                else:
                    existing["amount"] = None

                existing["examples"].append(parsed["original"])
                existing["count"] += 1

    result = []

    for item in ingredient_map.values():
        name = item["name"]
        unit = item["unit"]
        amount = item["amount"]

        if amount is not None:
            if amount.is_integer():
                amount = int(amount)

            if unit == "stück":
                if name == "ei":
                    label = "Ei" if amount == 1 else "Eier"
                elif name == "zwiebel":
                    label = "Zwiebel" if amount == 1 else "Zwiebeln"
                elif name == "tomate":
                    label = "Tomate" if amount == 1 else "Tomaten"
                elif name == "knoblauch":
                    label = "Knoblauchzehe" if amount == 1 else "Knoblauchzehen"
                else:
                    label = name.capitalize()

                result.append(f"{amount} {label}")
            else:
                result.append(f"{amount} {unit} {name}")
        else:
            if item["count"] > 1:
                result.append(f'{item["examples"][0]} ({item["count"]}x)')
            else:
                result.append(item["examples"][0])

    categories["Zutaten"] = sorted(result, key=lambda x: x.lower())

    return categories, pantry


@app.get("/einkaufsliste")
def einkaufsliste():
    db = get_db()
    plan = db.weekly_plan()

    recipes = []

    for day_slots in plan.values():
        if isinstance(day_slots, dict):
            for recipe_id in day_slots.values():
                if recipe_id:
                    recipe = db.get_recipe(int(recipe_id))
                    if recipe:
                        recipes.append(recipe)
        elif day_slots:
            recipe = db.get_recipe(int(day_slots))
            if recipe:
                recipes.append(recipe)

    categories, pantry = shopping_list(recipes)

    return {
        "categories": categories,
        "pantry": pantry,
    }