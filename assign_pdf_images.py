from pathlib import Path
from database import Database

IMAGE_DIR = Path("static/images")

def page_number(path):
    # pdf_recipe_12_0.png
    parts = path.stem.split("_")
    try:
        return int(parts[2])
    except Exception:
        return 99999

db = Database()

images = sorted(
    IMAGE_DIR.glob("pdf_recipe_*.*"),
    key=page_number
)

recipes = db.conn.execute(
    "SELECT id, name FROM recipes WHERE kueche = 'PDF Import' ORDER BY id"
).fetchall()

print(f"{len(recipes)} PDF-Rezepte gefunden")
print(f"{len(images)} PDF-Bilder gefunden")

for recipe, image in zip(recipes, images):
    db.conn.execute(
        "UPDATE recipes SET bild = ? WHERE id = ?",
        (image.name, recipe["id"]),
    )
    print(recipe["name"], "->", image.name)

db.conn.commit()
print("Bilder wurden zugeordnet.")