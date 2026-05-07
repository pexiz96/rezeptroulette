from dataclasses import dataclass, field

@dataclass(slots=True)
class Rezept:
    id: int | None = None
    name: str = ""
    kueche: str = "Unbekannt"
    bild: str = ""
    portionen: int = 2
    kochzeit: int = 30
    schwierigkeit: str = "Einfach"
    tags: list[str] = field(default_factory=list)
    favorit: bool = False
    zutaten: list[str] = field(default_factory=list)
    anleitung: str = "Keine Anleitung vorhanden."

    def meta_text(self) -> str:
        tag_text = " · " + ", ".join(self.tags[:3]) if self.tags else ""
        return (
            f"{self.kueche} · {self.kochzeit} Min · {self.schwierigkeit} · "
            f"{self.portionen} Portion(en){tag_text}"
        )