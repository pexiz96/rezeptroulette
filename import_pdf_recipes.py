import re
import json
import fitz
import pdfplumber

from database import Database
from models import Rezept

PDF_PATH = "Neu Essen, Neu Leben.pdf"


def extract_text():
    pages = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

    return pages


def save_pdf_images():
    doc = fitz.open(PDF_PATH)

    for page_index in range(len(doc)):
        page = doc[page_index]
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]

            base_image = doc.extract_image(xref)

            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            filename = f"pdf_recipe_{page_index}_{img_index}.{image_ext}"

            with open(f"static/images/{filename}", "wb") as f:
                f.write(image_bytes)


def parse_recipe_pages(pages):
    recipes = []

    current_recipe = None

    for text in pages:
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            continue

        title = lines[0]

        if (
            len(title.split()) <= 8
            and "zutaten" not in title.lower()
            and "zubereitung" not in title.lower()
        ):
            current_recipe = {
                "name": title,
                "zutaten": [],
                "anleitung": []
            }

            recipes.append(current_recipe)

        if not current_recipe:
            continue

        ingredient_mode = False
        instruction_mode = False

        for line in lines:
            lower = line.lower()

            if "zutaten" in lower:
                ingredient_mode = True
                instruction_mode = False
                continue

            if "zubereitung" in lower or "anleitung" in lower:
                instruction_mode = True
                ingredient_mode = False
                continue

            if ingredient_mode:
                current_recipe["zutaten"].append(line)

            elif instruction_mode:
                current_recipe["anleitung"].append(line)

    return recipes


def import_recipes():
    db = Database()

    pages = extract_text()

    save_pdf_images()

    recipes = parse_recipe_pages(pages)

    imported = 0

    for item in recipes:
        if not item["zutaten"]:
            continue

        recipe = Rezept(
            name=item["name"],
            kueche="PDF Import",
            bild="",
            portionen=2,
            kochzeit=30,
            schwierigkeit="Einfach",
            tags=["PDF Import"],
            favorit=False,
            zutaten=item["zutaten"],
            anleitung="\n".join(item["anleitung"])
        )

        try:
            db.save_recipe(recipe)
            imported += 1

        except Exception:
            pass

    print(f"{imported} Rezepte importiert")


if __name__ == "__main__":
    import_recipes()