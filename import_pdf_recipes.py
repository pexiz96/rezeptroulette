import re
from pathlib import Path

import fitz
import pdfplumber

from database import Database
from models import Rezept
from config import LOCAL_IMAGE_DIR


PDF_PATH = Path("Neu Essen, Neu Leben.pdf")


def clean_import_title(title):
    if not title:
        return ""

    title = str(title)

    title = re.sub(r"[^\w\säöüÄÖÜß&\-]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    fixes = {
        "Protei N": "Protein",
        "Prot E I N": "Protein",
        "M It": "mit",
        "M I T": "mit",
        "Cham Pignon": "Champignon",
        "Crem Ige": "Cremige",
        "Crem Iger": "Cremiger",
        "Krä Ute R": "Kräuter",
        "Waf F E L N": "Waffeln",
        "Ncrem E": "ncreme",
        "Sahnecrem E": "Sahnecreme",
        "Kuch En": "Kuchen",
        "Pfan N Kuch En": "Pfannkuchen",
        "Quarkbrötchen M It": "Quarkbrötchen mit",
        "Protein Chia Pudding M It": "Protein-Chia-Pudding mit",
        "Teriyaki Hähnchen M It": "Teriyaki-Hähnchen mit",
        "Rinderhack M It": "Rinderhack mit",
        "Quark Langos M It": "Quark-Langos mit",
        "Top Secret Käsekuch En": "Top Secret Käsekuchen",
    }

    for wrong, correct in fixes.items():
        title = title.replace(wrong, correct)

    title = title.replace(" - ", "-")
    title = re.sub(r"\s+", " ", title).strip()

    return title


def slugify(text):
    text = str(text or "").lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text[:80] or "rezept"


def render_page_image(pdf_doc, page_index, image_name):
    LOCAL_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    page = pdf_doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)

    output_path = LOCAL_IMAGE_DIR / image_name
    pix.save(str(output_path))


def split_recipe_text(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]

    if not lines:
        return None

    title = lines[0]
    zutaten = []
    anleitung = []

    mode = None

    for line in lines[1:]:
        lower = line.lower()

        if "zutat" in lower:
            mode = "zutaten"
            continue

        if "anleitung" in lower or "zubereitung" in lower:
            mode = "anleitung"
            continue

        if mode == "zutaten":
            zutaten.append(line)
        elif mode == "anleitung":
            anleitung.append(line)
        else:
            if any(char.isdigit() for char in line):
                zutaten.append(line)
            else:
                anleitung.append(line)

    if not zutaten:
        zutaten = ["Bitte Zutaten prüfen"]

    if not anleitung:
        anleitung = ["Bitte Anleitung prüfen"]

    return title, zutaten, anleitung


def import_recipes():
    db = Database()

    if not PDF_PATH.exists():
        print(f"PDF nicht gefunden: {PDF_PATH}")
        return

    imported = 0

    pdf_doc = fitz.open(str(PDF_PATH))

    with pdfplumber.open(str(PDF_PATH)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            parsed = split_recipe_text(text)

            if not parsed:
                continue

            title, zutaten, anleitung = parsed
            clean_title = clean_import_title(title)

            if not clean_title:
                continue

            image_name = f"pdf_{slugify(clean_title)}.png"
            render_page_image(pdf_doc, page_index - 1, image_name)

            recipe = Rezept(
                name=clean_title,
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
                print(f"Importiert: {clean_title} -> {image_name}")
            except Exception as exc:
                print(f"Übersprungen: {clean_title}", exc)

    print(f"{imported} PDF-Rezepte neu importiert.")


if __name__ == "__main__":
    import_recipes()