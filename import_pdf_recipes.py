import re
from pathlib import Path

import fitz
import pdfplumber

from database import Database
from models import Rezept

PDF_PATH = "Neu Essen, Neu Leben.pdf"
IMAGE_DIR = Path("static/images")


def slugify(text):
    text = text.lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def clean_title(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    lines = [l for l in lines if not l.isdigit()]
    if not lines:
        return None

    title = " ".join(lines[:2])
    title = title.replace("￾", "-")
    title = re.sub(r"\s+", " ", title).strip()
    return title.title()


def render_page_image(doc, page_index, filename):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)

    path = IMAGE_DIR / filename
    pix.save(path)

    return filename


def parse_recipe_page(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    zutaten = []
    anleitung = []

    mode = None

    for line in lines:
        lower = line.lower()

        if "zutaten" in lower:
            mode = "zutaten"
            continue

        if "zubereitung" in lower:
            mode = "anleitung"
            continue

        if line.isdigit():
            continue

        if "vorbereitung" in lower or "gesamtzeit" in lower or "backzeit" in lower or "kühlzeit" in lower:
            continue

        if mode == "zutaten":
            zutaten.append(line)

        elif mode == "anleitung":
            anleitung.append(line)

    return zutaten, anleitung


def import_recipes():
    db = Database()

    db.conn.execute("DELETE FROM recipes WHERE kueche = 'PDF Import'")
    db.conn.commit()

    pdf_doc = fitz.open(PDF_PATH)

    imported = 0

    with pdfplumber.open(PDF_PATH) as pdf:
        for page_index, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            if "ZUTATEN" not in text.upper() or "ZUBEREITUNG" not in text.upper():
                continue

            if page_index == 0:
                continue

            previous_text = pdf.pages[page_index - 1].extract_text() or ""
            title = clean_title(previous_text)

            if not title:
                continue

            zutaten, anleitung = parse_recipe_page(text)

            if not zutaten:
                continue

            image_name = f"pdf_{slugify(title)}.png"
            render_page_image(pdf_doc, page_index - 1, image_name)

            recipe = Rezept(
                name=title,
                kueche="PDF Import",
                bild=image_name,
                portionen=2,
                kochzeit=30,
                schwierigkeit="Einfach",
                tags=["PDF Import"],
                favorit=False,
                zutaten=zutaten,
                anleitung="\n".join(anleitung) or "Keine Anleitung vorhanden.",
            )

            try:
                db.save_recipe(recipe)
                imported += 1
                print(f"Importiert: {title} -> {image_name}")
            except Exception as exc:
                print(f"Übersprungen: {title}", exc)

    print(f"{imported} PDF-Rezepte neu importiert.")


if __name__ == "__main__":
    import_recipes()