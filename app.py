import random
import re
import shutil
import uuid
from collections import Counter
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps

from config import BASE_DIR, LOCAL_IMAGE_DIR, IMAGE_DIR, IMAGE_EXTENSIONS, DAYS
from database import Database
from models import Rezept

def normalize(text: str) -> str:
    text = str(text).lower().strip()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"\b(optional|gramm|g|kg|ml|l|el|tl|dose|dosen|stück|stueck|eine|einer|einen|ein)\b"," ",text,)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def filename_stem(text: str) -> str:
    text = normalize(text)
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def image_folders() -> list[Path]:
    return [LOCAL_IMAGE_DIR, IMAGE_DIR, BASE_DIR, Path.cwd() / "bilder", Path.cwd()]
def find_image(image_name: str = "", fallback_name: str = "") -> Path | None:
    names: list[str] = []

    if image_name:
        names.append(image_name.strip())

    if fallback_name:
        raw = fallback_name.strip()
        stem = filename_stem(raw)
        names.extend([raw, stem, stem.replace("_", "-"), stem.replace("_", "")])

    for name in names:
        path = Path(name)

        if path.is_absolute() and path.exists():
            return path

        wanted_stem = filename_stem(path.stem)
        wanted_name = name.lower()

        for folder in image_folders():
            if not folder.exists():
                continue

            direct = folder / name
            if direct.exists():
                return direct

            for file in folder.iterdir():
                if not file.is_file():
                    continue

                if file.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                if file.name.lower() == wanted_name:
                    return file

                if filename_stem(file.stem) == wanted_stem:
                    return file

    return None

def make_transparent_icon_image(path: Path) -> Image.Image | None:
    try:
        img = Image.open(path).convert("RGBA")

        new_data = []
        for r, g, b, a in img.getdata():
            if r > 225 and g > 225 and b > 225:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append((r, g, b, a))

        img.putdata(new_data)

        bbox = img.getchannel("A").getbbox()
        if bbox:
            img = img.crop(bbox)

        return img

    except Exception as exc:
        print("Icon konnte nicht geladen werden:", path, exc)
        return None


def find_app_icon() -> Path | None:
    possible_names = ["Rezeptroulette", "rezeptroulette", "rezeptroulette_icon", "icon", "logo", "app_icon",]

    for folder in image_folders():
        if not folder.exists():
            continue

        for file in folder.iterdir():
            if not file.is_file() or file.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            stem = file.stem.lower()

            if any(name.lower() == stem for name in possible_names):
                return file

            if "rezeptroulette" in stem:
                return file

    return None


def copy_image_if_needed(path_text: str) -> str:
    if not path_text:
        return ""

    source = Path(path_text)

    if not source.exists():
        return path_text

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    if source.parent.resolve() == IMAGE_DIR.resolve():
        return source.name

    target_name = f"{uuid.uuid4().hex}{source.suffix.lower()}"
    target = IMAGE_DIR / target_name
    shutil.copy(source, target)
    return target_name


def search_recipes(recipes: list[Rezept], query: str, kueche: str = "Alle", tag: str = "Alle Tags",
                   schwierigkeit: str = "Alle Schwierigkeiten", max_time: int | None = None,) -> list[Rezept]:
    terms = [normalize(t) for t in query.split() if normalize(t)]
    results: list[tuple[int, Rezept]] = []

    for recipe in recipes:
        if kueche != "Alle" and recipe.kueche != kueche:
            continue

        if tag != "Alle Tags" and tag not in recipe.tags:
            continue

        if schwierigkeit != "Alle Schwierigkeiten" and recipe.schwierigkeit != schwierigkeit:
            continue

        if max_time is not None and recipe.kochzeit > max_time:
            continue

        searchable = " ".join([normalize(recipe.name), normalize(recipe.kueche), normalize(recipe.schwierigkeit),
                               normalize(" ".join(recipe.tags)), normalize(" ".join(recipe.zutaten))])

        if terms and not all(term in searchable for term in terms):
            continue

        score = 0

        for term in terms:
            if term in normalize(recipe.name):
                score += 60
            if term in normalize(recipe.kueche):
                score += 25
            if term in normalize(" ".join(recipe.tags)):
                score += 20
            if term in normalize(" ".join(recipe.zutaten)):
                score += 10

        if recipe.favorit:
            score += 5

        results.append((score, recipe))

    return [recipe
        for _, recipe in sorted(results, key=lambda item: (-item[0], item[1].name.lower()))]

def ingredient_shelf_life(zutat: str) -> str:
    text = normalize(zutat)

    rules = [(["hack", "fleisch", "haehnchen", "huhn"], "ca. 1–2 Tage im Kühlschrank"),
             (["fisch", "lachs", "garnelen"], "ca. 1 Tag im Kühlschrank"),
             (["milch", "joghurt", "quark", "sahne"], "ca. 2–5 Tage im Kühlschrank"),
             (["kaese", "mozzarella", "parmesan"], "ca. 5–7 Tage gut verpackt im Kühlschrank"),
             (["tomaten", "passata", "bohnen", "mais"], "ca. 2–3 Tage im Kühlschrank, nach Öffnen umfüllen"),
             (["salat", "spinat", "kraeuter"], "ca. 1–3 Tage im Kühlschrank"),
             (["nudeln", "reis", "mehl", "zucker"], "trocken mehrere Monate haltbar"),
             (["oel", "essig", "salz", "pfeffer", "gewuerz"], "mehrere Monate haltbar, trocken/dunkel lagern")]

    for words, info in rules:
        if any(word in text for word in words):
            return info

    return "Verpackung prüfen; kühl und sauber lagern"


def parse_amount(zutat: str) -> tuple[str, float | None, str | None, str]:
    original = zutat.strip()
    parts = original.split(" ", 2)

    units = {"g": "g",
             "kg": "kg",
             "ml": "ml",
             "l": "l",
             "el": "EL",
             "tl": "TL",
             "dose": "Dose",
             "dosen": "Dose",
             "packung": "Packung",
             "packungen": "Packung",
             "bund": "Bund",
             "stück": "Stück",
             "stueck": "Stück"}

    if len(parts) >= 3:
        try:
            amount = float(parts[0].replace(",", "."))
            unit = parts[1].lower()
            name = parts[2].strip()

            if unit in units:
                return normalize(name), amount, units[unit], name
        except ValueError:
            pass

    if len(parts) >= 2:
        try:
            amount = float(parts[0].replace(",", "."))
            name = parts[1].strip()
            return normalize(name), amount, "Stück", name
        except ValueError:
            pass

    return normalize(original), None, None, original


def is_pantry(text: str) -> bool:
    base = normalize(text)
    return any(w in base for w in ["salz", "pfeffer", "oel", "wasser", "zucker", "mehl", "essig"])


def category_for(text: str) -> str:
    t = normalize(text)

    if any(w in t for w in ["spaghetti", "nudel", "pasta", "reis", "lasagne", "mehl", "teig", "brot"]):
        return "Trockenwaren & Backwaren"

    if any(w in t for w in ["hack", "fleisch", "patty", "schinken", "fisch"]):
        return "Fleisch & Fisch"

    if any(w in t for w in ["kaese", "mozzarella", "sahne", "milch", "joghurt", "quark", "butter", "ei"]):
        return "Kühlregal"

    if any(w in t for w in ["zwiebel", "tomate", "paprika", "gurke", "salat", "kartoffel", "basilikum", "zitrone"]):
        return "Obst & Gemüse"

    if any(w in t for w in ["tomatensauce", "passata", "ketchup", "mayonnaise", "dose"]):
        return "Konserven & Saucen"

    return "Sonstiges"


def shopping_list(recipes: list[Rezept]) -> tuple[dict[str, list[str]], list[str]]:
    amounts: dict[tuple[str, str], float] = {}
    simple: Counter[str] = Counter()
    originals: dict[str, str] = {}
    pantry: list[str] = []

    for recipe in recipes:
        for ingredient in recipe.zutaten:
            key, amount, unit, original = parse_amount(ingredient)

            if is_pantry(original):
                if original not in pantry:
                    pantry.append(original)

            originals[key] = original

            if amount is not None and unit is not None:
                amounts[(key, unit)] = amounts.get((key, unit), 0) + amount
            else:
                simple[key] += 1

    categories: dict[str, list[str]] = {}

    for (key, unit), amount in sorted(amounts.items()):
        shown_amount = int(amount) if float(amount).is_integer() else round(amount, 1)
        original = originals.get(key, key)
        item = f"{shown_amount} {unit} {original}" if unit != "Stück" else f"{shown_amount} {original}"
        categories.setdefault(category_for(original), []).append(item)

    for key, count in sorted(simple.items()):
        original = originals.get(key, key)
        item = original if count == 1 else f"{original} ({count}x)"
        categories.setdefault(category_for(original), []).append(item)

    return categories, pantry


def match_ingredient(a: str, b: str) -> bool:
    a_norm = normalize(a)
    b_norm = normalize(b)

    if not a_norm or not b_norm:
        return False

    return (a_norm in b_norm or b_norm in a_norm or any(word in b_norm for word in a_norm.split() if len(word) > 3))

def parse_food_input(text: str) -> list[dict[str, int | None]]:
    foods = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        name = line
        days = None

        if "|" in line:
            raw_name, raw_days = line.split("|", 1)
            name = raw_name.strip()

            try:
                days = int(raw_days.strip())
            except ValueError:
                days = None

        if name:
            foods.append({"name": name, "tage": days})

    return foods


def food_rescue(recipes: list[Rezept], foods: list[dict[str, int | None]], persons: int) -> list[dict]:
    proposals = []

    for recipe in recipes:
        matching = []
        urgent = []

        for food in foods:
            if any(match_ingredient(food["name"], ingredient) for ingredient in recipe.zutaten):
                matching.append(food["name"])

                if food.get("tage") is not None and food["tage"] <= 2:
                    urgent.append(food["name"])

        missing = [ingredient
            for ingredient in recipe.zutaten
            if not any(match_ingredient(food["name"], ingredient) for food in foods)]

        match_percent = int((len(matching) / max(1, len(recipe.zutaten))) * 100)
        rescue_score = max(0, min(100, match_percent + len(urgent) * 12 - len(missing) * 3))

        if len(matching) >= 2 or rescue_score >= 35:
            proposals.append({"recipe": recipe,
                              "persons": persons,
                              "matching": matching,
                              "urgent": urgent,
                              "missing": missing,
                              "match_percent": match_percent,
                              "rescue_score": rescue_score})

    return sorted(proposals, key=lambda p: (p["rescue_score"], p["match_percent"]), reverse=True)


def invent_rescue_recipe(foods: list[dict[str, int | None]], persons: int) -> dict:
    ingredients = [food["name"] for food in foods]
    joined = normalize(" ".join(ingredients))
    traits = []

    if any(w in joined for w in ["sahne", "kaese", "milch", "joghurt", "butter"]):
        traits.append("cremig")

    if any(w in joined for w in ["ei", "fleisch", "hack", "kaese"]):
        traits.append("herzhaft")

    if any(w in joined for w in ["tomate", "gurke", "salat", "paprika", "zitrone"]):
        traits.append("frisch")

    if any(w in joined for w in ["reis", "nudel", "pasta", "kartoffel", "brot"]):
        traits.append("sättigend")

    traits = traits or ["spontan"]

    if "cremig" in traits and "sättigend" in traits:
        kind = "Cremige Reste-Pfanne"
    elif "herzhaft" in traits:
        kind = "Herzhafte Küchen-DNA-Pfanne"
    else:
        kind = "Improvisiertes Rettungsgericht"

    urgent = [
        food["name"]
        for food in foods
        if food.get("tage") is not None and food["tage"] <= 2
    ]

    return {"name": f"{kind} mit {', '.join(ingredients[:3])}",
            "traits": traits,
            "ingredients": [f"{persons} Portion(en) {ingredient}" for ingredient in ingredients],
            "urgent": urgent,
            "score": min(100, 45 + len(ingredients) * 8 + len(urgent) * 10),
            "instructions": "\n".join(["1. Lebensmittel prüfen, schlechte Stellen entfernen und alles klein schneiden.",
                                       "2. Feste Zutaten zuerst anbraten.",
                                       "3. Sättigende Basis wie Reis, Nudeln, Kartoffeln oder Brot ergänzen, falls vorhanden.",
                                       "4. Cremige oder frische Zutaten später zugeben.",
                                       "5. Vorsichtig würzen, abschmecken und servieren."])}

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


# ------------------------------------------------------------
# Eigenes App-Farbschema
# ------------------------------------------------------------

# ------------------------------------------------
# MEDITERRAN THEME
# ------------------------------------------------

# Hintergründe
# ------------------------------------------------
# MEDITERRAN THEME
# ------------------------------------------------

# ---------------------------------
# Mediterranes Creme / Olive Theme
# ---------------------------------

# App Hintergrund
COLOR_BG = ("#F7F2E8", "#20251F")

# Sidebar + Hauptkarten
COLOR_PANEL = ("#F4EEE2", "#2B332C")

# Buttons / Menüs / Feature Cards
COLOR_PANEL_ALT = ("#E6DCCB", "#364238")

# Rahmen
COLOR_BORDER = ("#CDBB9D", "#516053")


# Hauptbuttons (Oliv)
COLOR_PRIMARY = ("#70875F", "#809B72")
COLOR_PRIMARY_HOVER = ("#5F7650", "#6F8862")

# Terracotta Button
COLOR_ACCENT = ("#C97C4A", "#D68D61")
COLOR_ACCENT_HOVER = ("#B96B3E", "#C97D53")

# Neutrale Buttons
COLOR_MUTED = ("#E2D7C7", "#445247")
COLOR_MUTED_HOVER = ("#D5C7B2", "#556357")

# Löschen
COLOR_DANGER = ("#A55A47", "#BD6B55")
COLOR_DANGER_HOVER = ("#8D4938", "#A95B47")


# Text
TEXT_MAIN = ("#2E3A2F", "#F5F2E8")
TEXT_MUTED = ("#66715E", "#C9D0C2")
TEXT_ON_DARK = "#FFFFFF"


# Typografie
FONT_TITLE = ("Georgia", 42, "bold")
FONT_SUBTITLE = ("Georgia", 24, "bold")
FONT_CARD_TITLE = ("Georgia", 25, "bold")

FONT_BODY = ("Segoe UI", 20)
FONT_SMALL = ("Segoe UI", 18)
FONT_BUTTON = ("Segoe UI", 19, "bold")

class RezeptfinderApp:
    def __init__(self):
        self.db = Database()
        self.current_recipe_id: int | None = None
        self.dark_mode = False
        self.random_active = False
        self.random_history: list[int] = []
        self.random_index = -1

        self.image_refs: list[ctk.CTkImage] = []
        self.logo_image: ctk.CTkImage | None = None
        self.window_icon_ref = None

        self.app = ctk.CTk()
        self.app.title("Rezeptroulette")
        self.app.geometry("1550x980")
        self.app.minsize(1450, 920)

        self.set_window_icon()

        self.build_ui()
        self.refresh_filters()
        self.show_home()

    def set_window_icon(self) -> None:
        icon = find_app_icon()

        if not icon:
            print("Kein App-Icon gefunden. Lege z. B. bilder/Rezeptroulette.jpg ab.")
            return

        try:
            img = Image.open(icon).convert("RGBA")
            self.window_icon_ref = ImageTk.PhotoImage(img)
            self.app.iconphoto(False, self.window_icon_ref)
        except Exception as exc:
            print("Fenster-Icon konnte nicht geladen werden:", exc)

    def recipes(self) -> list[Rezept]:
        return self.db.all_recipes()

    def build_ui(self) -> None:
        self.main = ctk.CTkFrame(self.app, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=20, pady=20)

        self.sidebar = ctk.CTkFrame(
            self.main,
            width=305,
            corner_radius=26,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 20))
        self.sidebar.pack_propagate(False)

        self.content = ctk.CTkFrame(
            self.main,
            corner_radius=26,
            fg_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.content.pack(side="right", fill="both", expand=True)

        self.build_sidebar_header()

        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="🔍  Suche Rezept, Küche, Zutat",
            width=255,
            height=46,
            corner_radius=16,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
        )
        self.search_entry.pack(pady=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda _event: self.show_search())
        self.search_entry.bind("<Return>", lambda _event: self.store_search())

        self.menu = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", width=250)
        self.menu.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self.section("Rezepte")
        self.button("🏠  Startseite", self.show_home)
        self.button("🎲  Zufallsgericht", self.show_random, COLOR_PRIMARY, COLOR_PRIMARY_HOVER)
        self.button("⭐  Favoriten", self.show_favorites)
        self.button("+  Rezept hinzufügen", self.show_recipe_form, COLOR_ACCENT, COLOR_ACCENT_HOVER)

        self.section("Filter")
        self.kueche_var = ctk.StringVar(value="Alle")
        self.tag_var = ctk.StringVar(value="Alle Tags")
        self.diff_var = ctk.StringVar(value="Alle Schwierigkeiten")
        self.time_var = ctk.StringVar(value="Alle Zeiten")

        self.kueche_menu = ctk.CTkOptionMenu(
            self.menu,
            variable=self.kueche_var,
            values=["Alle"],
            width=255,
            command=lambda _value: self.show_search(),
        )
        self.kueche_menu.pack(pady=5)

        self.tag_menu = ctk.CTkOptionMenu(
            self.menu,
            variable=self.tag_var,
            values=["Alle Tags"],
            width=255,
            command=lambda _value: self.show_search(),
        )
        self.tag_menu.pack(pady=5)

        ctk.CTkOptionMenu(
            self.menu,
            variable=self.diff_var,
            values=["Alle Schwierigkeiten", "Einfach", "Mittel", "Schwer"],
            width=255,
            command=lambda _value: self.show_search(),
        ).pack(pady=5)

        ctk.CTkOptionMenu(
            self.menu,
            variable=self.time_var,
            values=["Alle Zeiten", "Bis 15 Min", "Bis 30 Min", "Bis 60 Min"],
            width=255,
            command=lambda _value: self.show_search(),
        ).pack(pady=5)

        self.section("Planung")
        self.button("📅  Wochenplaner", self.show_weekly_plan)
        self.button("🛒  Einkaufsliste", self.show_shopping_list)

        self.section("Helfer")
        self.button("🛟  Food Rescue", self.show_food_rescue)
        self.button("🧬  Küchen-DNA", self.show_profile)
        self.dark_button = self.button("🌙  Dark Mode", self.toggle_dark_mode)

        self.header = ctk.CTkLabel(self.content, text="", font=FONT_TITLE)
        self.header.pack(pady=(25, 8))

        self.empty_img = ctk.CTkImage(
            light_image=Image.new("RGB", (1, 1), "white"),
            dark_image=Image.new("RGB", (1, 1), "black"),
            size=(1, 1),
        )
        self.image_label = ctk.CTkLabel(self.content, image=self.empty_img, text="")
        self.image_label.pack(pady=(0, 6))

        self.random_nav_frame = ctk.CTkFrame(
            self.content,
            fg_color=COLOR_PANEL_ALT,
            corner_radius=18,
        )

        self.random_back_button = ctk.CTkButton(
            self.random_nav_frame,
            text="← Zurück",
            command=self.previous_random_recipe,
            width=140,
            height=46,
            corner_radius=14,
            fg_color=COLOR_MUTED,
            hover_color=COLOR_MUTED_HOVER,
            font=FONT_BUTTON, text_color="black"
        )
        self.random_back_button.grid(row=0, column=0, padx=8, pady=8)

        self.random_recipe_button = ctk.CTkButton(
            self.random_nav_frame,
            text="📋 Rezept",
            command=lambda: None,
            width=140,
            height=46,
            corner_radius=14,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=FONT_BUTTON,
        )
        self.random_recipe_button.grid(row=0, column=1, padx=8, pady=8)

        self.random_next_button = ctk.CTkButton(
            self.random_nav_frame,
            text="Weiter →",
            command=self.next_random_recipe,
            width=140,
            height=46,
            corner_radius=14,
            fg_color=COLOR_MUTED,
            hover_color=COLOR_MUTED_HOVER,
            font=FONT_BUTTON, text_color="black"
        )
        self.random_next_button.grid(row=0, column=2, padx=8, pady=8)

        self.random_nav_frame.pack_forget()

        self.info = ctk.CTkScrollableFrame(
            self.content,
            corner_radius=16,
            width=860,
            height=530, fg_color=COLOR_BG
        )
        self.info.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        self.info._scrollbar.configure(width=0)

    def build_sidebar_header(self) -> None:
        icon = find_app_icon()

        logo_holder = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent",
            width=230,
            height=185,
        )
        logo_holder.pack(pady=(14, 0))
        logo_holder.pack_propagate(False)

        if icon:
            try:
                img = Image.open(icon).convert("RGBA")

                # Weißen/hellen Rand im Logo unsichtbar machen:
                # sehr helle Pixel werden transparent.
                data = img.getdata()
                new_data = []
                for r, g, b, a in data:
                    if r > 238 and g > 238 and b > 238:
                        new_data.append((r, g, b, 0))
                    else:
                        new_data.append((r, g, b, a))
                img.putdata(new_data)

                self.logo_image = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=(205, 170),
                )

                logo = ctk.CTkLabel(
                    logo_holder,
                    text="",
                    image=self.logo_image,
                    fg_color="transparent",
                    cursor="hand2",
                )
                logo.pack(expand=True)
                logo.bind("<Button-1>", lambda _event: self.show_home())
            except Exception as exc:
                print("Sidebar-Logo konnte nicht geladen werden:", exc)
        else:
            ctk.CTkLabel(
                logo_holder,
                text="🍽",
                font=("Segoe UI Emoji", 54),
                fg_color="transparent",
                cursor="hand2",
            ).pack(expand=True)

        title = ctk.CTkLabel(
            self.sidebar,
            text="Rezeptroulette",
            font=("Segoe UI", 32, "bold"),
            text_color=TEXT_MAIN,
            cursor="hand2",
        )
        title.pack(pady=(0, 18))
        title.bind("<Button-1>", lambda _event: self.show_home())

    def section(self, text: str) -> None:
        ctk.CTkLabel(
            self.menu,
            text=text.upper(),
            font=FONT_BUTTON,
            text_color=("gray35", "gray70"),
        ).pack(anchor="w", padx=20, pady=(14, 2))

    def button(self, text, command, color=None, hover=None):
        is_accent = color is not None
        btn = ctk.CTkButton(
            self.menu,
            text=text,
            command=command,
            width=255,
            height=48,
            corner_radius=16,
            fg_color=color or COLOR_MUTED,
            hover_color=hover or COLOR_MUTED_HOVER,
            text_color=TEXT_ON_DARK if is_accent else TEXT_MAIN,
            border_width=1,
            border_color=COLOR_BORDER,
            font=FONT_BUTTON,
            anchor="w",
        )
        btn.pack(pady=6)
        return btn

    def clear(self) -> None:

        for widget in self.info.winfo_children():
            widget.destroy()

    def reset_image(self) -> None:
        self.image_label.configure(image=self.empty_img, text="")
        self.image_label.image = self.empty_img

    def make_ctk_image(
        self,
        path: Path,
        max_size: tuple[int, int],
        *,
        pad_to_box: bool = True,
    ) -> ctk.CTkImage | None:
        """Lädt ein Bild, ohne es abzuschneiden.

        pad_to_box=True bedeutet:
        Das Bild wird komplett sichtbar gemacht und mit hellem Hintergrund
        auf die gewünschte Box-Größe gesetzt.
        """
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")

                if pad_to_box:
                    contained = ImageOps.contain(img, max_size)

                    canvas = Image.new("RGB", max_size, "#F4EEE2")
                    x = (max_size[0] - contained.width) // 2
                    y = (max_size[1] - contained.height) // 2
                    canvas.paste(contained, (x, y))

                    return ctk.CTkImage(
                        light_image=canvas,
                        dark_image=canvas,
                        size=max_size,
                    )

                img.thumbnail(max_size)
                return ctk.CTkImage(
                    light_image=img.copy(),
                    dark_image=img.copy(),
                    size=img.size,
                )

        except Exception as exc:
            print("Bild konnte nicht geladen werden:", path, exc)
            return None

    def set_recipe_image(self, recipe: Rezept) -> None:
        path = find_image(recipe.bild, recipe.name)

        if not path:
            self.reset_image()
            self.image_label.configure(text=f"Kein Bild gefunden für: {recipe.name}")
            print(f"Bild nicht gefunden: bild='{recipe.bild}', rezept='{recipe.name}'")
            print("Gesucht in:", [str(p) for p in image_folders()])
            return

        ctk_img = self.make_ctk_image(path, (310, 175), pad_to_box=True)

        if not ctk_img:
            self.reset_image()
            self.image_label.configure(text="Bild konnte nicht geladen werden.")
            return

        self.image_refs.append(ctk_img)
        self.image_label.configure(image=ctk_img, text="")
        self.image_label.image = ctk_img

    def refresh_filters(self) -> None:
        recipes = self.recipes()
        self.kueche_menu.configure(values=["Alle"] + sorted({r.kueche for r in recipes}))
        self.tag_menu.configure(values=["Alle Tags"] + sorted({t for r in recipes for t in r.tags}))

    def load_feature_icon(self, filename: str, size: tuple[int, int] = (92, 92)) -> ctk.CTkImage | None:
        path = find_image(filename)

        if not path:
            print(f"Feature-Icon nicht gefunden: {filename}")
            return None

        img = make_transparent_icon_image(path)

        if img is None:
            return None

        img.thumbnail(size, Image.Resampling.LANCZOS)

        icon = ctk.CTkImage(
            light_image=img,
            dark_image=img,
            size=img.size,
        )

        self.image_refs.append(icon)
        return icon

    def feature_icon_label(self, parent, filename: str, fallback: str) -> None:
        icon = self.load_feature_icon(filename, (92, 92))

        if icon:
            label = ctk.CTkLabel(
                parent,
                text="",
                image=icon,
                fg_color="transparent",
            )
            label.image = icon
            label.pack(pady=(0,0))
            return

        ctk.CTkLabel(
            parent,
            text=fallback,
            font=("Segoe UI", 34, "bold"),
            text_color=COLOR_ACCENT,
            fg_color="transparent",
        ).pack(pady=(24,10))

    def show_home(self) -> None:
            self.random_active = False
            self.hide_random_nav()
            self.current_recipe_id = None
            self.search_entry.delete(0, "end")
            self.header.configure(text="")
            self.reset_image()
            self.clear()

            hero = ctk.CTkFrame(
                self.info,
                corner_radius=24,
                fg_color=COLOR_PANEL,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            hero.pack(fill="x", padx=18, pady=(20, 18))

            ctk.CTkLabel(
                hero,
                text="Willkommen bei Rezeptroulette",
                font=FONT_TITLE,
                text_color=TEXT_MAIN,
            ).pack(anchor="center", pady=(24, 24))

            feature_row = ctk.CTkFrame(hero, fg_color="transparent")
            feature_row.pack(fill="x", padx=24, pady=(0, 24))

            features = [
                ("suche.jpg", "🔍", "Suche", self.show_search),
                ("planen.jpg", "📅", "Planen", self.show_weekly_plan),
                ("food rescue.jpg", "♻", "Food Rescue", self.show_food_rescue),
                ("küchen DNA.jpg", "DNA", "Küchen-DNA", self.show_profile),
            ]

            for icon_file, fallback_icon, title, command in features:
                box = ctk.CTkFrame(
                    feature_row,
                    width=260,
                    height=200,
                    corner_radius=18,
                    fg_color=COLOR_PANEL_ALT,
                    border_width=1,
                    border_color=COLOR_BORDER,
                )
                box.pack(side="left", expand=True, fill="x", padx=8)
                box.pack_propagate(False)

                inner = ctk.CTkFrame(box, fg_color="transparent")
                inner.place(relx=0.5, rely=0.5, anchor="center")

                self.feature_icon_label(inner, icon_file, fallback_icon)

                label = ctk.CTkLabel(
                    inner,
                    text=title,
                    font=FONT_CARD_TITLE,
                    text_color=TEXT_MAIN,
                )
                label.pack(pady=(14, 0))

                box.bind("<Button-1>", lambda e, cmd=command: cmd())
                inner.bind("<Button-1>", lambda e, cmd=command: cmd())
                label.bind("<Button-1>", lambda e, cmd=command: cmd())

                for child in inner.winfo_children():
                    child.bind("<Button-1>", lambda e, cmd=command: cmd())

            ctk.CTkLabel(
                self.info,
                text="Heute empfohlen",
                font=FONT_SUBTITLE,
                text_color=TEXT_MAIN,
            ).pack(anchor="w", padx=22, pady=(6, 2))

            grid = ctk.CTkFrame(self.info, fg_color="transparent")
            grid.pack(fill="x", padx=10, pady=(0, 20))

            for index, recipe in enumerate(self.recipes()[:3]):
                self.recipe_card_modern(grid, recipe, index)

    def store_search(self) -> None:
        text = self.search_entry.get().strip()

        if len(text) >= 3:
            self.db.add_profile_event("search", text)

    def filtered_recipes(self) -> list[Rezept]:
        max_time = {
            "Bis 15 Min": 15,
            "Bis 30 Min": 30,
            "Bis 60 Min": 60,
        }.get(self.time_var.get())

        return search_recipes(
            self.recipes(),
            self.search_entry.get().strip(),
            self.kueche_var.get(),
            self.tag_var.get(),
            self.diff_var.get(),
            max_time,
        )

    def show_search(self) -> None:
        recipes = self.filtered_recipes()
        title = "Rezepte" if not self.search_entry.get().strip() else f"Suche: {self.search_entry.get().strip()}"
        self.show_recipe_list(recipes, title)

    def show_recipe_list(self, recipes: list[Rezept], title: str) -> None:
        self.random_active = False
        self.hide_random_nav()
        self.current_recipe_id = None
        self.header.configure(text=title)
        self.reset_image()
        self.clear()

        ctk.CTkLabel(
            self.info,
            text=f"{len(recipes)} Rezept(e) gefunden",
            font=FONT_SUBTITLE,
        ).pack(anchor="w", padx=20, pady=(20, 8))

        if not recipes:
            ctk.CTkLabel(
                self.info,
                text="Keine passenden Rezepte gefunden.",
                font=("Segoe UI", 18),
            ).pack(anchor="w", padx=20, pady=10)
            return

        for recipe in recipes:
            self.recipe_card(recipe)

    def recipe_card_modern(self, parent, recipe: Rezept, column: int) -> None:
        card = ctk.CTkFrame(
            parent,
            width=310,
            height=380,
            corner_radius=20,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.grid(row=0, column=column, padx=16, pady=8, sticky="nsew")
        card.grid_propagate(False)
        parent.grid_columnconfigure(column, weight=1)

        image_box = ctk.CTkFrame(
            card,
            width=310,
            height=175,
            corner_radius=18,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        image_box.pack(fill="x", padx=0, pady=0)
        image_box.pack_propagate(False)

        path = find_image(recipe.bild, recipe.name)
        img = self.make_ctk_image(path, (310, 120), pad_to_box=True) if path else None

        if img:
            self.image_refs.append(img)
            image_label = ctk.CTkLabel(image_box, image=img, text="")
            image_label.image = img
            image_label.pack(expand=True)
        else:
            ctk.CTkLabel(image_box, text="🍽", font=("Segoe UI Emoji", 58)).pack(expand=True)

        star = ctk.CTkButton(
            image_box,
            text="☆" if not recipe.favorit else "★",
            width=44,
            height=46,
            corner_radius=12,
            fg_color=COLOR_PANEL,
            hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_ACCENT,
            font=("Segoe UI", 24),
            command=lambda rid=recipe.id: self.toggle_favorite_in_list(rid),
        )
        star.place(relx=0.95, rely=0.08, anchor="ne")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(
            content,
            text=recipe.name,
            font=FONT_CARD_TITLE,
            text_color=TEXT_MAIN,
        ).pack(pady=(8,4))

        ctk.CTkLabel(
            content,
            text=f"{recipe.kueche}  •  {recipe.kochzeit} Min  •  {recipe.schwierigkeit}  •  {recipe.portionen} Portion(en)",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            wraplength=260,
            justify="center",
        ).pack(pady=(6, 8))

        tag_row = ctk.CTkFrame(content, fg_color="transparent")
        tag_row.pack(pady=(0,10))

        for tag in recipe.tags[:3]:
            ctk.CTkLabel(
                tag_row,
                text=tag,
                font=("Segoe UI", 14),
                text_color=TEXT_MAIN,
                fg_color=COLOR_MUTED,
                corner_radius=16,
                padx=10,
                pady=4,
            ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            content,
            text="Rezept öffnen",
            command=lambda rid=recipe.id: self.show_recipe(rid),
            height=42,
            corner_radius=12,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=FONT_BUTTON,
        ).pack(side="bottom", pady=(8,12), padx=30, fill="x")

    def recipe_card(self, recipe: Rezept) -> None:
        card = ctk.CTkFrame(
            self.info,
            corner_radius=18,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="x", padx=20, pady=8)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=14)

        img_box = ctk.CTkFrame(row, width=120, height=90, corner_radius=12, fg_color=COLOR_PANEL_ALT)
        img_box.pack(side="left", padx=(0, 14))
        img_box.pack_propagate(False)

        path = find_image(recipe.bild, recipe.name)
        thumb = self.make_ctk_image(path, (120, 90), pad_to_box=True) if path else None

        if thumb:
            self.image_refs.append(thumb)
            label = ctk.CTkLabel(img_box, text="", image=thumb)
            label.image = thumb
            label.pack(expand=True)
        else:
            ctk.CTkLabel(img_box, text="🍽", font=("Segoe UI Emoji", 34)).pack(expand=True)

        text_area = ctk.CTkFrame(row, fg_color="transparent")
        text_area.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            text_area,
            text=recipe.name,
            font=FONT_CARD_TITLE,
            text_color=TEXT_MAIN,
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_area,
            text=recipe.meta_text(),
            font=FONT_SMALL,
            wraplength=620,
            justify="left",
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=2)

        preview = ", ".join(recipe.zutaten[:4]) + (" ..." if len(recipe.zutaten) > 4 else "")

        ctk.CTkLabel(
            text_area,
            text=f"Zutaten: {preview}",
            font=FONT_SMALL,
            wraplength=620,
            justify="left",
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=2)

        right_area = ctk.CTkFrame(row, fg_color="transparent")
        right_area.pack(side="right", padx=(12, 0))

        ctk.CTkButton(
            right_area,
            text="★" if recipe.favorit else "☆",
            width=46,
            height=38,
            corner_radius=12,
            fg_color=COLOR_PANEL,
            hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_ACCENT,
            font=("Segoe UI", 24),
            command=lambda rid=recipe.id: self.toggle_favorite_in_list(rid),
        ).pack(pady=(0, 8))

        ctk.CTkButton(
            right_area,
            text="Öffnen",
            command=lambda rid=recipe.id: self.show_recipe(rid),
            width=120,
            height=34,
            corner_radius=12,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
        ).pack()

    def toggle_favorite_in_list(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            return
        self.db.toggle_favorite(recipe_id)
        self.refresh_filters()
        if self.search_entry.get().strip() or self.kueche_var.get() != "Alle" or self.tag_var.get() != "Alle Tags" or self.diff_var.get() != "Alle Schwierigkeiten" or self.time_var.get() != "Alle Zeiten":
            self.show_search()
        else:
            self.show_home()

    def show_recipe(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            return

        recipe = self.db.get_recipe(recipe_id)

        if not recipe:
            return

        self.current_recipe_id = recipe.id
        self.db.add_profile_event("opened_recipe", recipe.name)

        for ingredient in recipe.zutaten:
            self.db.add_profile_event("used_ingredient", ingredient)

        self.header.configure(text=recipe.name)
        self.set_recipe_image(recipe)
        if self.random_active:
            self.show_random_nav()
        else:
            self.hide_random_nav()
        self.clear()

        ctk.CTkLabel(
            self.info,
            text=recipe.meta_text(),
            font=FONT_SUBTITLE,
        ).pack(anchor="w", padx=20, pady=(20, 10))

        actions = ctk.CTkFrame(self.info, fg_color="transparent")
        actions.pack(anchor="w", padx=20, pady=(5, 15))

        ctk.CTkButton(
            actions,
            text="☆ Favorisieren" if not recipe.favorit else "★ Entfavorisieren",
            command=lambda rid=recipe.id: self.toggle_favorite_from_detail(rid),
            width=170,
            height=38,
            corner_radius=12,
            fg_color="#E8F3E4",
            hover_color="#D7EBD2",
            text_color="#15351D",
            font=FONT_BUTTON,
        ).grid(row=0, column=0, padx=4, pady=4)

        ctk.CTkButton(
            actions,
            text="📅 Zum Wochenplan",
            command=lambda rid=recipe.id: self.add_to_weekplan(rid),
            width=170,
            height=38,
            corner_radius=12,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
            font=FONT_BUTTON,
        ).grid(row=0, column=1, padx=4, pady=4)

        ctk.CTkButton(
            actions,
            text="✏️ Bearbeiten",
            command=lambda: self.show_recipe_form(recipe.id),
            width=140,
            height=38,
            corner_radius=12,
            fg_color="#E8F3E4",
            hover_color="#D7EBD2",
            text_color="#15351D",
            font=FONT_BUTTON,
        ).grid(row=0, column=2, padx=4, pady=4)

        ctk.CTkButton(
            actions,
            text="📤 Export",
            command=lambda: self.export_recipe(recipe),
            width=120,
            height=38,
            corner_radius=12,
            fg_color="#E8F3E4",
            hover_color="#D7EBD2",
            text_color="#15351D",
            font=FONT_BUTTON,
        ).grid(row=0, column=3, padx=4, pady=4)

        ctk.CTkButton(
            actions,
            text="🗑 Löschen",
            command=lambda: self.delete_recipe(recipe.id),
            width=120,
            height=38,
            corner_radius=12,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            text_color="white",
            font=FONT_BUTTON,
        ).grid(row=0, column=4, padx=4, pady=4)

        ctk.CTkLabel(
            self.info,
            text="Zutaten",
            font=FONT_CARD_TITLE,
        ).pack(anchor="w", padx=20, pady=(8, 5))

        for ingredient in recipe.zutaten:
            ctk.CTkLabel(
                self.info,
                text=f"• {ingredient} — {ingredient_shelf_life(ingredient)}",
                font=FONT_SMALL,
                wraplength=780,
                justify="left",
            ).pack(anchor="w", padx=35, pady=2)

        ctk.CTkLabel(
            self.info,
            text="Anleitung",
            font=FONT_CARD_TITLE,
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            self.info,
            text=recipe.anleitung,
            font=FONT_BODY,
            wraplength=780,
            justify="left",
        ).pack(anchor="w", padx=35, pady=(0, 20))

    def show_random_nav(self) -> None:
        if not self.random_nav_frame.winfo_ismapped():
            self.random_nav_frame.pack(after=self.image_label, pady=(0, 12))

    def hide_random_nav(self) -> None:
        self.random_nav_frame.pack_forget()

    def random_navigation_bar(self) -> None:
        self.show_random_nav()

    def pick_new_random_recipe_id(self) -> int | None:
        recipes = self.recipes()

        if not recipes:
            return None

        ids = [r.id for r in recipes if r.id is not None]

        if not ids:
            return None

        if self.current_recipe_id in ids and len(ids) > 1:
            ids = [rid for rid in ids if rid != self.current_recipe_id]

        return random.choice(ids)

    def next_random_recipe(self) -> None:
        self.random_active = True

        if self.random_index < len(self.random_history) - 1:
            self.random_index += 1
            self.show_recipe(self.random_history[self.random_index])
            return

        recipe_id = self.pick_new_random_recipe_id()

        if recipe_id is None:
            messagebox.showinfo("Keine Rezepte", "Es gibt noch keine Rezepte.")
            return

        self.random_history = self.random_history[: self.random_index + 1]
        self.random_history.append(recipe_id)
        self.random_index += 1
        self.show_recipe(recipe_id)

    def previous_random_recipe(self) -> None:
        self.random_active = True

        if self.random_index <= 0:
            messagebox.showinfo("Hinweis", "Es gibt kein vorheriges Zufallsgericht.")
            return

        self.random_index -= 1
        self.show_recipe(self.random_history[self.random_index])

    def show_random(self) -> None:
        if not self.recipes():
            messagebox.showinfo("Keine Rezepte", "Es gibt noch keine Rezepte.")
            return

        self.random_active = True
        self.next_random_recipe()

    def show_favorites(self) -> None:
        self.show_recipe_list(
            [r for r in self.recipes() if r.favorit],
            "⭐ Favoriten",
        )

    def show_hint(self, text: str) -> None:
        hint = ctk.CTkLabel(
            self.content,
            text="✓ " + text,
            fg_color=COLOR_PRIMARY,
            text_color="white",
            corner_radius=12,
            font=FONT_BUTTON,
            padx=16,
            pady=8,
        )
        hint.place(relx=0.97, rely=0.95, anchor="se")
        self.app.after(2200, hint.destroy)

    def add_to_weekplan(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            return

        recipe = self.db.get_recipe(recipe_id)
        if not recipe:
            return

        plan = self.db.weekly_plan()

        for day in DAYS:
            if not plan.get(day):
                plan[day] = recipe_id
                self.db.set_weekly_plan(plan)
                self.show_hint(f"{recipe.name} wurde für {day} eingetragen.")
                return

        self.show_hint("Wochenplan ist voll.")

    def toggle_favorite_from_detail(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            return
        self.db.toggle_favorite(recipe_id)
        self.refresh_filters()
        if self.random_active:
            recipe = self.db.get_recipe(recipe_id)
            if recipe:
                self.show_hint(f"{recipe.name} wurde aktualisiert.")
            return
        self.show_recipe(recipe_id)

    def toggle_favorite_silent(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            return
        self.db.toggle_favorite(recipe_id)
        self.refresh_filters()

    def toggle_favorite(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            return

        self.db.toggle_favorite(recipe_id)
        self.refresh_filters()

        if self.random_active:
            # Im Zufallsmodus nur favorisieren, nicht neu öffnen/navigieren.
            return

        self.show_recipe(recipe_id)

    def delete_recipe(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            return

        recipe = self.db.get_recipe(recipe_id)

        if not recipe:
            return

        if not messagebox.askyesno("Rezept löschen", f"Möchtest du „{recipe.name}“ wirklich löschen?"):
            return

        self.db.delete_recipe(recipe_id)
        self.refresh_filters()
        self.show_home()

    def show_recipe_form(self, recipe_id: int | None = None) -> None:
        old = self.db.get_recipe(recipe_id) if recipe_id else Rezept()

        popup = ctk.CTkToplevel(self.app)
        popup.title("Rezept bearbeiten" if recipe_id else "Rezept hinzufügen")
        popup.geometry("780x900")
        popup.grab_set()

        frame = ctk.CTkScrollableFrame(popup, corner_radius=18)
        frame.pack(fill="both", expand=True, padx=25, pady=25)

        ctk.CTkLabel(
            frame,
            text="✏️ Rezept bearbeiten" if recipe_id else "🍳 Rezept hinzufügen",
            font=("Segoe UI", 26, "bold"),
        ).pack(pady=(20, 16))

        entries = {}

        for key, placeholder, value in [
            ("name", "Name", old.name),
            ("kueche", "Küche", old.kueche),
            ("portionen", "Portionen", str(old.portionen)),
            ("kochzeit", "Kochzeit in Minuten", str(old.kochzeit)),
            ("tags", "Tags, mit Komma getrennt", ", ".join(old.tags)),
            ("bild", "Bildpfad oder leer", old.bild),
        ]:
            entry = ctk.CTkEntry(frame, width=560, placeholder_text=placeholder)
            entry.pack(pady=7)
            entry.insert(0, value)
            entries[key] = entry

        diff_var = ctk.StringVar(value=old.schwierigkeit)

        ctk.CTkOptionMenu(
            frame,
            variable=diff_var,
            values=["Einfach", "Mittel", "Schwer"],
            width=560,
        ).pack(pady=7)

        preview_label = ctk.CTkLabel(frame, text="")
        preview_label.pack(pady=8)
        preview_ref = {"image": None}

        def update_preview(path_text: str) -> None:
            path = find_image(path_text, entries["name"].get().strip())

            if not path:
                preview_label.configure(image=None, text="Keine Vorschau")
                return

            preview = self.make_ctk_image(path, (240, 160))

            if not preview:
                preview_label.configure(image=None, text="Keine Vorschau")
                return

            preview_ref["image"] = preview
            preview_label.configure(image=preview, text="")

        update_preview(old.bild)

        def choose_image() -> None:
            path = filedialog.askopenfilename(
                filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.webp *.bmp")],
                parent=popup,
            )

            if path:
                entries["bild"].delete(0, "end")
                entries["bild"].insert(0, path)
                update_preview(path)

        ctk.CTkButton(
            frame,
            text="Bild auswählen",
            command=choose_image,
            width=180,
        ).pack(pady=5)

        ctk.CTkLabel(
            frame,
            text="Zutaten, eine pro Zeile",
            font=FONT_BUTTON,
        ).pack(anchor="w", padx=80, pady=(12, 0))

        ingredients_box = ctk.CTkTextbox(frame, width=620, height=150)
        ingredients_box.pack(pady=8)
        ingredients_box.insert("1.0", "\n".join(old.zutaten))

        ctk.CTkLabel(
            frame,
            text="Anleitung",
            font=FONT_BUTTON,
        ).pack(anchor="w", padx=80, pady=(12, 0))

        instructions_box = ctk.CTkTextbox(frame, width=620, height=180)
        instructions_box.pack(pady=8)
        instructions_box.insert(
            "1.0",
            old.anleitung if old.anleitung != "Keine Anleitung vorhanden." else "",
        )

        def save() -> None:
            try:
                name = entries["name"].get().strip()

                if not name:
                    raise ValueError("Name fehlt.")

                recipe = Rezept(
                    id=old.id,
                    name=name,
                    kueche=entries["kueche"].get().strip() or "Unbekannt",
                    bild=copy_image_if_needed(entries["bild"].get().strip()),
                    portionen=int(entries["portionen"].get().strip()),
                    kochzeit=int(entries["kochzeit"].get().strip()),
                    schwierigkeit=diff_var.get(),
                    tags=[t.strip() for t in entries["tags"].get().split(",") if t.strip()],
                    favorit=old.favorit,
                    zutaten=[
                        z.strip()
                        for z in ingredients_box.get("1.0", "end").splitlines()
                        if z.strip()
                    ],
                    anleitung=instructions_box.get("1.0", "end").strip()
                    or "Keine Anleitung vorhanden.",
                )

                if recipe.portionen <= 0:
                    raise ValueError("Portionen müssen größer als 0 sein.")

                if recipe.kochzeit <= 0:
                    raise ValueError("Kochzeit muss größer als 0 sein.")

                if not recipe.zutaten:
                    raise ValueError("Mindestens eine Zutat fehlt.")

                saved_id = self.db.save_recipe(recipe)

            except Exception as exc:
                messagebox.showwarning("Ungültige Angaben", str(exc), parent=popup)
                return

            self.refresh_filters()
            popup.destroy()
            self.show_recipe(saved_id)

        ctk.CTkButton(
            frame,
            text="💾 Speichern",
            command=save,
            width=240,
            height=44,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
        ).pack(pady=(20, 8))

        ctk.CTkButton(
            frame,
            text="Schließen",
            command=popup.destroy,
            width=240,
            height=44,
            fg_color="#757575",
            hover_color="#424242",
        ).pack(pady=(0, 20))

    def show_weekly_plan(self) -> None:
        self.random_active = False
        self.hide_random_nav()
        self.current_recipe_id = None
        self.header.configure(text="📅 Wochenplaner")
        self.reset_image()
        self.clear()

        plan = self.db.weekly_plan()
        recipes = self.recipes()
        names = [""] + [r.name for r in recipes]
        by_name = {r.name: r.id for r in recipes}
        by_id = {r.id: r.name for r in recipes}
        vars_ = {}

        frame = ctk.CTkFrame(self.info, corner_radius=16)
        frame.pack(fill="x", padx=20, pady=20)

        for row, day in enumerate(DAYS):
            ctk.CTkLabel(
                frame,
                text=day,
                font=("Segoe UI", 17, "bold"),
                width=120,
            ).grid(row=row, column=0, padx=16, pady=8, sticky="w")

            vars_[day] = ctk.StringVar(value=by_id.get(plan.get(day), ""))

            ctk.CTkOptionMenu(
                frame,
                variable=vars_[day],
                values=names,
                width=520,
            ).grid(row=row, column=1, padx=16, pady=8, sticky="w")

        def clear_plan() -> None:
            if not messagebox.askyesno(
                "Wochenplan leeren",
                "Möchtest du wirklich den kompletten Wochenplan löschen?"
            ):
                return

            self.db.set_weekly_plan({day: None for day in DAYS})
            self.show_hint("Wochenplan wurde geleert.")
            self.show_weekly_plan()

        def save() -> None:
            self.db.set_weekly_plan(
                {day: by_name.get(var.get()) for day, var in vars_.items()}
            )
            self.show_hint("Wochenplan wurde gespeichert.")
            self.show_weekly_plan()

        button_row = ctk.CTkFrame(self.info, fg_color="transparent")
        button_row.pack(anchor="w", padx=20, pady=(0, 8))

        ctk.CTkButton(
            button_row,
            text="💾 Wochenplan speichern",
            command=save,
            width=220,
            height=42,
            corner_radius=14,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
            font=FONT_BUTTON,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            button_row,
            text="🧹 Wochenplan leeren",
            command=clear_plan,
            width=220,
            height=42,
            corner_radius=14,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            text_color="white",
            font=FONT_BUTTON,
        ).pack(side="left")

        ctk.CTkButton(
            self.info,
            text="Einkaufsliste aus Wochenplan",
            command=self.show_shopping_list,
            width=260,
            height=42,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
        ).pack(anchor="w", padx=20, pady=(0, 20))

    def show_shopping_list(self) -> None:
        self.random_active = False
        self.hide_random_nav()
        self.current_recipe_id = None
        self.header.configure(text="🛒 Einkaufsliste")
        self.reset_image()
        self.clear()

        plan = self.db.weekly_plan()
        recipes = [self.db.get_recipe(rid) for rid in plan.values() if rid]
        recipes = [recipe for recipe in recipes if recipe]

        if not recipes:
            ctk.CTkLabel(
                self.info,
                text="Noch keine Rezepte im Wochenplan.",
                font=("Segoe UI", 18),
            ).pack(anchor="w", padx=20, pady=20)
            return

        ctk.CTkLabel(
            self.info,
            text="Rezepte:",
            font=FONT_CARD_TITLE,
        ).pack(anchor="w", padx=20, pady=(20, 5))

        for name, count in Counter(r.name for r in recipes).items():
            text = f"• {name}" if count == 1 else f"• {name} ({count}x)"
            ctk.CTkLabel(
                self.info,
                text=text,
                font=FONT_SMALL,
            ).pack(anchor="w", padx=35, pady=1)

        categories, pantry = shopping_list(recipes)
        order = [
            "Obst & Gemüse",
            "Kühlregal",
            "Fleisch & Fisch",
            "Trockenwaren & Backwaren",
            "Konserven & Saucen",
            "Sonstiges",
        ]

        for category in order:
            items = categories.get(category, [])

            if not items:
                continue

            ctk.CTkLabel(
                self.info,
                text=category,
                font=FONT_SUBTITLE,
            ).pack(anchor="w", padx=20, pady=(14, 4))

            for item in items:
                ctk.CTkCheckBox(
                    self.info,
                    text=f"{item} — {ingredient_shelf_life(item)}",
                    font=FONT_SMALL,
                ).pack(anchor="w", padx=35, pady=2)

        if pantry:
            ctk.CTkLabel(
                self.info,
                text="Grundvorrat prüfen",
                font=FONT_SUBTITLE,
            ).pack(anchor="w", padx=20, pady=(14, 4))

            for item in sorted(set(pantry)):
                ctk.CTkCheckBox(
                    self.info,
                    text=item,
                    font=FONT_SMALL,
                ).pack(anchor="w", padx=35, pady=2)

    def show_food_rescue(self) -> None:
        self.random_active = False
        self.hide_random_nav()
        self.current_recipe_id = None
        self.header.configure(
            text="",
            font=("Georgia", 44, "bold")  # größer mediterran
        )
        self.reset_image()
        self.clear()

        # Überschrift mit JPG-Icon statt Emoji
        title_row = ctk.CTkFrame(self.info, fg_color="transparent")
        title_row.pack(pady=(20, 15))

        icon_path = find_image("food rescue.jpg")
        if icon_path:
            icon_img = self.load_feature_icon("food rescue.jpg", (70, 70))
            if icon_img:
                ctk.CTkLabel(
                    title_row,
                    image=icon_img,
                    text="",
                    fg_color="transparent",
                ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            title_row,
            text="Food Rescue",
            font=("Georgia", 48, "bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left")

        ctk.CTkLabel(
            self.info,
            text="Gib Lebensmittel ein.",
            font=("Segoe UI", 26),
            wraplength=780,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(20, 8))

        box = ctk.CTkTextbox(self.info, width=800, height=150, font=("Segoe UI", 19))
        box.pack(anchor="w", padx=20, pady=8)
        box.insert("1.0", "Sahne \nPaprika \nReis\nEier\nKäse")

        persons_entry = ctk.CTkEntry(
            self.info,
            width=240,
            placeholder_text="Personenanzahl",
        )
        persons_entry.pack(anchor="w", padx=20, pady=8)
        persons_entry.insert(0, "2")

        rescue_button_bar = ctk.CTkFrame(self.info, fg_color="transparent")
        rescue_button_bar.pack(anchor="w", padx=20, pady=(12, 8))

        result = ctk.CTkFrame(self.info, corner_radius=16, fg_color=COLOR_BG,        # statt grau
    border_width=1,
    border_color=COLOR_BORDER
)
        result.pack(fill="x", padx=20, pady=18)

        def start() -> None:
            for widget in result.winfo_children():
                widget.destroy()

            try:
                persons = int(persons_entry.get())
                foods = parse_food_input(box.get("1.0", "end"))

                if persons <= 0 or len(foods) < 3:
                    raise ValueError

            except Exception:
                messagebox.showwarning(
                    "Eingabe prüfen",
                    "Bitte mindestens 3 Lebensmittel und eine gültige Personenanzahl eingeben.",
                )
                return

            proposals = food_rescue(self.recipes(), foods, persons)

            ctk.CTkLabel(
                result,
                text="Beste Rettungs-Vorschläge",
                font=FONT_SUBTITLE,
                text_color=COLOR_PRIMARY,
            ).pack(anchor="w", padx=20, pady=(18, 8))

            for proposal in proposals[:5]:
                recipe = proposal["recipe"]

                card = ctk.CTkFrame(result, corner_radius=14,  fg_color=COLOR_BG,
    border_width=1,
    border_color=COLOR_BORDER
)
                card.pack(fill="x", padx=20, pady=8)

                ctk.CTkLabel(
                    card,
                    text=f"{recipe.name} — Rettungswert {proposal['rescue_score']}%",
                    font=FONT_CARD_TITLE,
                    text_color=COLOR_PRIMARY,
                ).pack(anchor="w", padx=16, pady=(12, 3))

                ctk.CTkLabel(
                    card,
                    text=f"Vorhanden: {', '.join(proposal['matching']) or '-'}",
                    font=FONT_SMALL,
                    wraplength=740,
                ).pack(anchor="w", padx=16, pady=2)

                ctk.CTkLabel(
                    card,
                    text=f"Fehlt: {', '.join(proposal['missing'][:5]) or 'nichts Wichtiges'}",
                    font=FONT_SMALL,
                    wraplength=740,
                ).pack(anchor="w", padx=16, pady=2)

                ctk.CTkButton(
                    card,
                    text="Rezept öffnen",
                    command=lambda rid=recipe.id: self.show_recipe(rid),
                    width=150,
                ).pack(anchor="w", padx=16, pady=(6, 12))

            invented = invent_rescue_recipe(foods, persons)

            ctk.CTkLabel(
                result,
                text="🧬 Erfundenes Rettungsgericht",
                font=FONT_SUBTITLE,
                text_color=COLOR_ACCENT,
            ).pack(anchor="w", padx=20, pady=(18, 6))

            ctk.CTkLabel(
                result,
                text=invented["name"],
                font=FONT_SUBTITLE,
            ).pack(anchor="w", padx=35, pady=2)

            ctk.CTkLabel(
                result,
                text=invented["instructions"],
                font=FONT_SMALL,
                wraplength=740,
                justify="left",
            ).pack(anchor="w", padx=35, pady=(5, 18))

        ctk.CTkButton(
            rescue_button_bar,
            text="🛟 Lebensmittel retten",
            command=start,
            width=240,
            height=46,
            corner_radius=14,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
            font=FONT_BUTTON,
        ).pack(anchor="w")

    def show_profile(self) -> None:
        self.random_active = False
        self.hide_random_nav()
        self.current_recipe_id = None
        self.header.configure(text="🧬 Küchen-DNA")
        self.reset_image()
        self.clear()

        opened = self.db.profile_values("opened_recipe")
        ingredients = self.db.profile_values("used_ingredient")
        searches = self.db.profile_values("search")

        ctk.CTkLabel(
            self.info,
            text="Dein persönliches Kochprofil",
            font=("Segoe UI", 25, "bold"),
            text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=20, pady=(20, 10))

        data = [
            f"Geöffnete Rezepte: {len(opened)}",
            "Top-Rezepte: " + (", ".join(name for name, _ in Counter(opened).most_common(5)) or "noch keine"),
            "Top-Zutaten: " + (", ".join(name for name, _ in Counter(ingredients).most_common(8)) or "noch keine"),
            "Häufige Suchen: " + (", ".join(name for name, _ in Counter(searches).most_common(5)) or "noch keine"),
        ]

        for line in data:
            ctk.CTkLabel(
                self.info,
                text=f"• {line}",
                font=FONT_BODY,
                wraplength=780,
                justify="left",
            ).pack(anchor="w", padx=35, pady=4)

    def export_recipe(self, recipe: Rezept) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Textdatei", "*.txt")],
            initialfile=f"{recipe.name}.txt",
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(recipe.name + "\n")
                file.write("=" * len(recipe.name) + "\n\n")
                file.write(recipe.meta_text() + "\n\n")
                file.write("Zutaten:\n")

                for ingredient in recipe.zutaten:
                    file.write(f"- {ingredient} — {ingredient_shelf_life(ingredient)}\n")

                file.write("\nAnleitung:\n")
                file.write(recipe.anleitung)

            messagebox.showinfo("Exportiert", "Das Rezept wurde gespeichert.")

        except Exception as exc:
            messagebox.showerror("Exportfehler", str(exc))

    def toggle_dark_mode(self) -> None:
        self.dark_mode = not self.dark_mode
        ctk.set_appearance_mode("dark" if self.dark_mode else "light")
        self.dark_button.configure(text="☀ Light Mode" if self.dark_mode else "🌙 Dark Mode")

    def run(self) -> None:
        self.app.mainloop()





