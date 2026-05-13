import json
import sqlite3
from pathlib import Path

DATA_RECIPE_PATH = Path("data/recipes.json")

from config import DB_PATH, IMAGE_DIR, LOCAL_IMAGE_DIR, DAYS
from models import Rezept


BUILTIN_RECIPE_TEXT = """
Spaghetti Bolognese|Italienisch|bolognese.jpg|4|45|Einfach|Pasta,Hackfleisch,Familie|400 g Spaghetti;500 g Hackfleisch;1 Zwiebel;2 Knoblauchzehen;2 EL Öl;2 EL Tomatenmark;1 Dose gehackte Tomaten;100 ml Wasser;1 TL Oregano;Salz;Pfeffer;Parmesan|1. Spaghetti in Salzwasser bissfest kochen.\\n2. Zwiebel und Knoblauch fein würfeln.\\n3. Öl erhitzen und Hackfleisch kräftig anbraten.\\n4. Zwiebel und Knoblauch dazugeben und kurz mitbraten.\\n5. Tomatenmark einrühren und leicht anrösten.\\n6. Gehackte Tomaten und Wasser dazugeben.\\n7. Mit Oregano, Salz und Pfeffer würzen.\\n8. Sauce 20 Minuten köcheln lassen.\\n9. Mit Spaghetti und Parmesan servieren.
Nudelauflauf|Deutsch|nudelauflauf.jpg|4|45|Einfach|Ofengericht,Pasta,Familie|400 g Nudeln;200 g Schinkenwürfel;1 Zwiebel;250 ml Sahne;150 ml Milch;200 g geriebener Käse;1 EL Öl;Salz;Pfeffer;Muskat|1. Nudeln in Salzwasser knapp bissfest kochen.\\n2. Zwiebel würfeln und in Öl anbraten.\\n3. Schinkenwürfel kurz mitbraten.\\n4. Sahne und Milch verrühren.\\n5. Mit Salz, Pfeffer und Muskat würzen.\\n6. Nudeln, Schinken und Sauce in eine Auflaufform geben.\\n7. Käse darüberstreuen.\\n8. Bei 180 °C ca. 25 Minuten goldbraun backen.
Pesto Pasta|Italienisch|pesto_pasta.jpg|2|20|Einfach|Pasta,Schnell,Vegetarisch|250 g Pasta;3 EL Pesto;50 g Parmesan;2 EL Nudelwasser;1 EL Olivenöl;Salz;Pfeffer|1. Pasta in Salzwasser bissfest kochen.\\n2. Etwas Nudelwasser aufbewahren.\\n3. Pasta abgießen.\\n4. Pesto mit Nudelwasser und Olivenöl cremig rühren.\\n5. Pasta mit der Pestomischung vermengen.\\n6. Mit Salz und Pfeffer abschmecken.\\n7. Parmesan darübergeben und servieren.
Gebratene Nudeln|Asiatisch|bratnudeln.jpg|3|30|Einfach|Wok,Nudeln,Schnell|300 g Nudeln;2 Eier;1 Paprika;1 Karotte;2 Frühlingszwiebeln;3 EL Sojasauce;2 EL Öl;Pfeffer|1. Nudeln nach Packungsangabe kochen und abgießen.\\n2. Paprika und Karotte in Streifen schneiden.\\n3. Öl in einer großen Pfanne erhitzen.\\n4. Gemüse 4 Minuten anbraten.\\n5. Eier verquirlen und in der Pfanne stocken lassen.\\n6. Nudeln dazugeben und alles gut vermengen.\\n7. Mit Sojasauce und Pfeffer abschmecken.\\n8. Mit Frühlingszwiebeln servieren.
Chili con Carne|Mexikanisch|chili.jpg|4|50|Einfach|Eintopf,Hackfleisch,Herzhaft|500 g Hackfleisch;1 Zwiebel;2 Knoblauchzehen;1 Dose Kidneybohnen;1 Dose Mais;1 Dose gehackte Tomaten;2 EL Tomatenmark;250 ml Brühe;1 TL Paprikapulver;Chili;Salz;Pfeffer;2 EL Öl|1. Zwiebel und Knoblauch fein würfeln.\\n2. Öl erhitzen und Hackfleisch krümelig anbraten.\\n3. Zwiebel und Knoblauch dazugeben.\\n4. Tomatenmark einrühren und kurz rösten.\\n5. Tomaten und Brühe hinzufügen.\\n6. Bohnen und Mais abspülen und dazugeben.\\n7. Mit Paprika, Chili, Salz und Pfeffer würzen.\\n8. 25 Minuten köcheln lassen.\\n9. Mit Brot oder Reis servieren.
Pellkartoffeln mit Quark|Deutsch|pellkartoffeln.jpg|2|35|Einfach|Kartoffeln,Vegetarisch,Low Budget|700 g Kartoffeln;250 g Quark;2 EL Milch;1 EL Kräuter;1 kleine Zwiebel;Salz;Pfeffer|1. Kartoffeln gründlich waschen.\\n2. Kartoffeln mit Schale in Salzwasser ca. 25 Minuten garen.\\n3. Quark mit Milch cremig rühren.\\n4. Zwiebel fein würfeln.\\n5. Kräuter und Zwiebel unter den Quark rühren.\\n6. Mit Salz und Pfeffer abschmecken.\\n7. Kartoffeln abgießen und mit Kräuterquark servieren.
Tortellini Auflauf|Italienisch|tortellini_auflauf.jpg|4|35|Einfach|Ofengericht,Pasta,Familie|500 g Tortellini;250 ml Sahne;1 Dose gehackte Tomaten;150 g geriebener Käse;1 Knoblauchzehe;1 TL italienische Kräuter;Salz;Pfeffer|1. Tortellini ungekocht oder kurz vorgekocht in eine Auflaufform geben.\\n2. Sahne, Tomaten und Gewürze verrühren.\\n3. Knoblauch pressen und einrühren.\\n4. Sauce über die Tortellini geben.\\n5. Käse darüberstreuen.\\n6. Bei 180 °C ca. 25 Minuten backen.\\n7. Kurz ruhen lassen und servieren.
Hähnchen-Geschnetzeltes mit Reis|Deutsch|haehnchen_geschnetzeltes.jpg|3|35|Einfach|Hähnchen,Reis,Pfanne|500 g Hähnchenbrust;250 g Reis;1 Zwiebel;250 ml Sahne;150 ml Brühe;1 EL Mehl;2 EL Öl;Salz;Pfeffer;Paprikapulver|1. Reis nach Packungsangabe kochen.\\n2. Hähnchen in Streifen schneiden.\\n3. Zwiebel fein würfeln.\\n4. Öl erhitzen und Hähnchen kräftig anbraten.\\n5. Zwiebel dazugeben.\\n6. Mehl darüberstäuben und verrühren.\\n7. Mit Brühe und Sahne ablöschen.\\n8. Mit Salz, Pfeffer und Paprika würzen.\\n9. 10 Minuten köcheln lassen und mit Reis servieren.
Hähnchenkeule mit Kartoffeln und Buttergemüse|Deutsch|haehnchenkeule_mit_kartoffel.jpg|4|65|Einfach|Ofengericht,Hähnchen,Familie|4 Hähnchenkeulen;800 g Kartoffeln;400 g Buttergemüse;3 EL Öl;1 TL Paprikapulver;Salz;Pfeffer;1 TL Kräuter|1. Ofen auf 200 °C vorheizen.\\n2. Kartoffeln schälen und in Spalten schneiden.\\n3. Hähnchenkeulen mit Öl und Gewürzen einreiben.\\n4. Kartoffeln mit Öl, Salz und Kräutern mischen.\\n5. Alles auf ein Blech geben.\\n6. Ca. 50 Minuten backen, zwischendurch wenden.\\n7. Buttergemüse nach Packungsangabe erhitzen.\\n8. Zusammen servieren.
Gulasch|Ungarisch|gulasch.jpg|4|120|Mittel|Fleisch,Eintopf,Hausmannskost|800 g Rindergulasch;3 Zwiebeln;2 Paprika;2 EL Tomatenmark;500 ml Rinderbrühe;2 EL Öl;1 TL Paprikapulver;Salz;Pfeffer;1 Lorbeerblatt|1. Zwiebeln grob würfeln.\\n2. Öl in einem Topf erhitzen.\\n3. Fleisch portionsweise kräftig anbraten.\\n4. Zwiebeln dazugeben und mitrösten.\\n5. Tomatenmark einrühren.\\n6. Mit Brühe ablöschen.\\n7. Paprika, Lorbeerblatt, Salz und Pfeffer hinzufügen.\\n8. Zugedeckt ca. 90 Minuten schmoren lassen.\\n9. Paprika würfeln und die letzten 20 Minuten mitgaren.\\n10. Mit Nudeln, Kartoffeln oder Reis servieren.
Rouladen|Deutsch|rouladen.jpg|4|120|Mittel|Hausmannskost,Fleisch,Sonntag|4 Rinderrouladen;4 TL Senf;4 Scheiben Speck;2 Gewürzgurken;2 Zwiebeln;500 ml Rinderbrühe;2 EL Öl;Salz;Pfeffer;1 EL Tomatenmark|1. Rouladen flach ausbreiten und mit Salz und Pfeffer würzen.\\n2. Mit Senf bestreichen.\\n3. Speck, Gurkenstreifen und Zwiebelstreifen darauflegen.\\n4. Rouladen aufrollen und fixieren.\\n5. Öl erhitzen und Rouladen rundherum scharf anbraten.\\n6. Tomatenmark kurz mitrösten.\\n7. Mit Brühe ablöschen.\\n8. Zugedeckt ca. 90 Minuten schmoren.\\n9. Sauce abschmecken und mit Kartoffeln oder Rotkohl servieren.
Schnitzel|Deutsch|schnitzel.jpg|2|30|Mittel|Fleisch,Pfanne,Klassiker|2 Schweineschnitzel;1 Ei;4 EL Mehl;100 g Paniermehl;Salz;Pfeffer;Öl zum Braten;1 Zitrone|1. Schnitzel flach klopfen.\\n2. Mit Salz und Pfeffer würzen.\\n3. Erst in Mehl, dann in verquirltem Ei und zuletzt in Paniermehl wenden.\\n4. Öl in einer Pfanne erhitzen.\\n5. Schnitzel von beiden Seiten goldbraun ausbacken.\\n6. Auf Küchenpapier abtropfen lassen.\\n7. Mit Zitrone servieren.
Schichtkohl|Deutsch|schichtkohl.jpg|4|60|Einfach|Hausmannskost,Kohl,Hackfleisch|1 kleiner Weißkohl;500 g Hackfleisch;1 Zwiebel;500 ml Brühe;2 EL Öl;Salz;Pfeffer;Kümmel;Paprikapulver|1. Weißkohl in Streifen schneiden.\\n2. Zwiebel würfeln.\\n3. Hackfleisch in Öl krümelig anbraten.\\n4. Zwiebel dazugeben.\\n5. Kohl portionsweise hinzufügen und kurz mitbraten.\\n6. Mit Brühe ablöschen.\\n7. Mit Salz, Pfeffer, Kümmel und Paprika würzen.\\n8. Zugedeckt 40 Minuten schmoren lassen.\\n9. Mit Kartoffeln servieren.
Schweinebraten|Deutsch|schweinebraten.jpg|4|110|Mittel|Braten,Hausmannskost,Fleisch|1 kg Schweinebraten;2 Zwiebeln;2 Karotten;500 ml Brühe;2 EL Senf;2 EL Öl;Salz;Pfeffer;Paprikapulver|1. Fleisch mit Senf, Salz, Pfeffer und Paprika einreiben.\\n2. Zwiebeln und Karotten grob schneiden.\\n3. Öl erhitzen und Braten rundherum anbraten.\\n4. Gemüse dazugeben.\\n5. Mit Brühe angießen.\\n6. Bei 180 °C ca. 90 Minuten im Ofen garen.\\n7. Zwischendurch mit Sauce übergießen.\\n8. Sauce abschmecken und mit Beilagen servieren.
Spaghetti Carbonara|Italienisch|carbonara.jpg|3|25|Einfach|Pasta,Schnell,Herzhaft|350 g Spaghetti;150 g Speckwürfel;3 Eier;70 g Parmesan;Salz;Pfeffer;1 EL Öl|1. Spaghetti in Salzwasser kochen.\\n2. Speck in Öl knusprig braten.\\n3. Eier mit Parmesan und Pfeffer verrühren.\\n4. Etwas Nudelwasser aufbewahren.\\n5. Spaghetti abgießen und zum Speck geben.\\n6. Pfanne vom Herd nehmen.\\n7. Eiermischung unterheben, bis eine cremige Sauce entsteht.\\n8. Sofort servieren.
Bratkartoffeln|Deutsch|bratkartoffeln.jpg|2|35|Einfach|Kartoffeln,Pfanne,Resteverwertung|600 g Kartoffeln;1 Zwiebel;100 g Speckwürfel;2 EL Öl;Salz;Pfeffer;Petersilie|1. Kartoffeln vorkochen, abkühlen lassen und in Scheiben schneiden.\\n2. Öl in einer Pfanne erhitzen.\\n3. Kartoffeln darin goldbraun braten.\\n4. Speck und Zwiebeln dazugeben.\\n5. Alles knusprig weiterbraten.\\n6. Mit Salz und Pfeffer abschmecken.\\n7. Mit Petersilie servieren.
Hähnchenpfanne|Deutsch|haehnchenpfanne.jpg|3|35|Einfach|Pfanne,Hähnchen,Schnell|500 g Hähnchenbrust;1 Paprika;1 Zucchini;1 Zwiebel;200 ml Sahne;2 EL Öl;Salz;Pfeffer;Paprikapulver|1. Hähnchen in Stücke schneiden.\\n2. Gemüse würfeln.\\n3. Öl erhitzen und Hähnchen anbraten.\\n4. Zwiebel und Gemüse dazugeben.\\n5. Alles 5 Minuten braten.\\n6. Sahne hinzufügen.\\n7. Mit Salz, Pfeffer und Paprika würzen.\\n8. Kurz köcheln lassen und servieren.
Milchreis|Deutsch|milchreis.jpg|4|35|Einfach|Süß,Warm,Comfort Food|250 g Milchreis;1 Liter Milch;2 EL Zucker;1 Prise Salz;1 TL Vanillezucker;Zimt;Apfelmus|1. Milch mit Salz, Zucker und Vanillezucker aufkochen.\\n2. Milchreis einrühren.\\n3. Bei niedriger Hitze 25 bis 30 Minuten quellen lassen.\\n4. Regelmäßig umrühren, damit nichts anbrennt.\\n5. Mit Zimt und Apfelmus servieren.
Spinat, Kartoffeln und Ei|Deutsch|spinat_kartoffeln_und_ei.jpg|2|35|Einfach|Vegetarisch,Kartoffeln,Klassiker|600 g Kartoffeln;400 g Rahmspinat;4 Eier;Salz;Pfeffer;Muskat|1. Kartoffeln schälen und in Salzwasser kochen.\\n2. Rahmspinat langsam erhitzen.\\n3. Spinat mit Muskat, Salz und Pfeffer abschmecken.\\n4. Eier nach Wunsch kochen oder als Spiegeleier braten.\\n5. Alles zusammen servieren.
Senfsoße und Ei|Deutsch|senfsosse_und_ei.jpg|2|30|Einfach|Vegetarisch,Kartoffeln,Hausmannskost|6 Kartoffeln;4 Eier;2 EL Butter;2 EL Mehl;400 ml Milch;2 EL Senf;Salz;Pfeffer;Zucker|1. Kartoffeln schälen und kochen.\\n2. Eier hart kochen.\\n3. Butter in einem Topf schmelzen.\\n4. Mehl einrühren und kurz anschwitzen.\\n5. Milch langsam einrühren.\\n6. Senf dazugeben und aufkochen lassen.\\n7. Mit Salz, Pfeffer und etwas Zucker abschmecken.\\n8. Eier pellen und mit Kartoffeln und Sauce servieren.
Königsberger Klopse|Deutsch|koenigsberger_klopse.jpg|4|60|Mittel|Hausmannskost,Hackfleisch,Klassiker|500 g Hackfleisch;1 Brötchen;1 Ei;1 Zwiebel;750 ml Brühe;2 EL Butter;2 EL Mehl;200 ml Sahne;2 EL Kapern;Salz;Pfeffer;Zitronensaft|1. Brötchen einweichen und ausdrücken.\\n2. Hackfleisch mit Brötchen, Ei, Zwiebel, Salz und Pfeffer mischen.\\n3. Klopse formen.\\n4. Brühe erhitzen und Klopse 15 Minuten ziehen lassen.\\n5. Klopse herausnehmen.\\n6. Butter und Mehl anschwitzen.\\n7. Mit Brühe und Sahne ablöschen.\\n8. Kapern und Zitronensaft hinzufügen.\\n9. Klopse in der Sauce erwärmen.\\n10. Mit Kartoffeln servieren.
Flammkuchen|Französisch|flammkuchen.jpg|2|30|Einfach|Ofengericht,Schnell,Herzhaft|1 Flammkuchenteig;150 g Schmand;100 g Speckwürfel;1 rote Zwiebel;Salz;Pfeffer;Schnittlauch|1. Ofen auf 220 °C vorheizen.\\n2. Teig auf einem Blech ausrollen.\\n3. Schmand mit Salz und Pfeffer würzen.\\n4. Schmand auf dem Teig verstreichen.\\n5. Zwiebel in dünne Ringe schneiden.\\n6. Speck und Zwiebeln darauf verteilen.\\n7. 12 bis 15 Minuten knusprig backen.\\n8. Mit Schnittlauch servieren.
Pasta Arrabbiata|Italienisch|pasta_arrabbiata.jpg|2|25|Einfach|Pasta,Scharf,Schnell|250 g Penne;1 Dose gehackte Tomaten;2 Knoblauchzehen;2 EL Olivenöl;Chili;Salz;Pfeffer;Basilikum|1. Penne in Salzwasser kochen.\\n2. Knoblauch fein hacken.\\n3. Öl erhitzen und Knoblauch kurz anbraten.\\n4. Tomaten hinzufügen.\\n5. Mit Chili, Salz und Pfeffer würzen.\\n6. 10 Minuten köcheln lassen.\\n7. Pasta unterheben.\\n8. Mit Basilikum servieren.
Nudeln mit Tomatensoße|Italienisch|nudeln_mit_tomatensosse.jpg|3|25|Einfach|Pasta,Vegetarisch,Familie|350 g Nudeln;1 Dose gehackte Tomaten;1 Zwiebel;1 Knoblauchzehe;1 EL Tomatenmark;2 EL Öl;Salz;Pfeffer;Oregano|1. Nudeln kochen.\\n2. Zwiebel und Knoblauch würfeln.\\n3. Öl erhitzen und Zwiebel anbraten.\\n4. Knoblauch und Tomatenmark dazugeben.\\n5. Tomaten hinzufügen.\\n6. Mit Salz, Pfeffer und Oregano würzen.\\n7. 15 Minuten köcheln lassen.\\n8. Mit Nudeln servieren.
Ciabatta Auflauf|Italienisch|ciabatta_auflauf.jpg|4|35|Einfach|Ofengericht,Resteverwertung,Vegetarisch|1 Ciabatta;2 Tomaten;200 g Mozzarella;200 ml Sahne;2 Eier;1 TL italienische Kräuter;Salz;Pfeffer|1. Ciabatta in Scheiben schneiden.\\n2. Tomaten und Mozzarella schneiden.\\n3. Alles abwechselnd in eine Form schichten.\\n4. Sahne mit Eiern und Gewürzen verrühren.\\n5. Mischung über den Auflauf geben.\\n6. Bei 180 °C ca. 25 Minuten backen.
Lasagne|Italienisch|lasagne.jpg|4|75|Mittel|Ofengericht,Pasta,Hackfleisch|500 g Hackfleisch;1 Zwiebel;2 Knoblauchzehen;1 Dose Tomaten;2 EL Tomatenmark;Lasagneplatten;500 ml Béchamelsauce;200 g Käse;Salz;Pfeffer;Oregano|1. Zwiebel und Knoblauch würfeln.\\n2. Hackfleisch anbraten.\\n3. Zwiebel, Knoblauch und Tomatenmark dazugeben.\\n4. Tomaten hinzufügen und würzen.\\n5. 20 Minuten köcheln lassen.\\n6. Sauce, Lasagneplatten und Béchamel abwechselnd schichten.\\n7. Mit Käse abschließen.\\n8. Bei 180 °C ca. 40 Minuten backen.\\n9. Vor dem Servieren 5 Minuten ruhen lassen.
Gebratener Reis mit Ei|Asiatisch|gebratener_reis_mit_ei.jpg|3|25|Einfach|Reis,Schnell,Pfanne|300 g gekochter Reis;3 Eier;1 Karotte;100 g Erbsen;3 EL Sojasauce;2 EL Öl;Pfeffer|1. Karotte klein würfeln.\\n2. Öl in einer Pfanne erhitzen.\\n3. Karotten und Erbsen anbraten.\\n4. Eier verquirlen und in der Pfanne stocken lassen.\\n5. Reis dazugeben und kräftig braten.\\n6. Mit Sojasauce und Pfeffer abschmecken.
Gyros mit Reis|Griechisch|gyrosmitreis.jpg|3|35|Einfach|Fleisch,Reis,Pfanne|500 g Gyrosfleisch;250 g Reis;1 Paprika;1 Zwiebel;2 EL Öl;Salz;Pfeffer;Tzatziki|1. Reis nach Packungsangabe kochen.\\n2. Zwiebel und Paprika schneiden.\\n3. Öl erhitzen und Gyrosfleisch kräftig anbraten.\\n4. Gemüse dazugeben und mitbraten.\\n5. Mit Salz und Pfeffer abschmecken.\\n6. Mit Reis und Tzatziki servieren.
Kassler mit Sauerkraut|Deutsch|kassler.jpg|4|55|Einfach|Hausmannskost,Fleisch,Klassiker|600 g Kassler;500 g Sauerkraut;1 Zwiebel;300 ml Brühe;1 Lorbeerblatt;1 EL Öl;Pfeffer;Kartoffeln|1. Zwiebel würfeln und in Öl anbraten.\\n2. Sauerkraut dazugeben.\\n3. Brühe und Lorbeerblatt hinzufügen.\\n4. Kassler auf das Sauerkraut legen.\\n5. Zugedeckt ca. 35 Minuten garen.\\n6. Kartoffeln separat kochen.\\n7. Alles zusammen servieren.
Wraps mit Hähnchen oder Hack|Mexikanisch|wraps.jpg|4|30|Einfach|Wrap,Schnell,Familie|4 Wraps;400 g Hähnchen oder Hackfleisch;1 Paprika;1 Zwiebel;Salat;Tomaten;150 g Käse;Salsa;2 EL Öl;Salz;Pfeffer|1. Fleisch in Öl anbraten.\\n2. Zwiebel und Paprika schneiden und dazugeben.\\n3. Mit Salz und Pfeffer würzen.\\n4. Wraps kurz erwärmen.\\n5. Mit Salat, Tomaten, Fleisch, Käse und Salsa füllen.\\n6. Einrollen und servieren.
Hähnchen-Curry mit Reis|Indisch|haehnchencurry.jpg|4|40|Einfach|Curry,Hähnchen,Reis|500 g Hähnchenbrust;250 g Reis;1 Zwiebel;1 Paprika;1 Dose Kokosmilch;2 EL Currypaste;1 EL Öl;Salz;Pfeffer|1. Reis kochen.\\n2. Hähnchen würfeln.\\n3. Zwiebel und Paprika schneiden.\\n4. Öl erhitzen und Hähnchen anbraten.\\n5. Gemüse dazugeben.\\n6. Currypaste einrühren.\\n7. Kokosmilch hinzufügen.\\n8. 15 Minuten köcheln lassen.\\n9. Mit Reis servieren.
Fischstäbchen mit Kartoffelbrei und Buttergemüse|Deutsch|fischstaebchen.jpg|4|35|Einfach|Fisch,Kartoffeln,Familie|12 Fischstäbchen;800 g Kartoffeln;200 ml Milch;2 EL Butter;400 g Buttergemüse;Salz;Muskat|1. Kartoffeln schälen und kochen.\\n2. Fischstäbchen nach Packungsangabe braten oder backen.\\n3. Buttergemüse erhitzen.\\n4. Kartoffeln abgießen und stampfen.\\n5. Milch und Butter einrühren.\\n6. Mit Salz und Muskat abschmecken.\\n7. Alles zusammen servieren.
Spaghetti Aglio e Olio|Italienisch|spaghetti_agilio_o_olio.jpg|2|20|Einfach|Pasta,Low Budget,Schnell|250 g Spaghetti;4 Knoblauchzehen;4 EL Olivenöl;Chili;Petersilie;Salz;Pfeffer;Parmesan|1. Spaghetti in Salzwasser kochen.\\n2. Knoblauch in dünne Scheiben schneiden.\\n3. Olivenöl langsam erhitzen.\\n4. Knoblauch und Chili darin sanft anbraten.\\n5. Spaghetti abgießen, etwas Nudelwasser behalten.\\n6. Pasta mit Knoblauchöl und Nudelwasser vermengen.\\n7. Mit Petersilie und Parmesan servieren.
Gemüse-Reis-Pfanne|Deutsch|gemuese_reispfanne.jpg|3|30|Einfach|Reis,Vegetarisch,Pfanne|250 g Reis;1 Paprika;1 Zucchini;1 Karotte;100 g Erbsen;2 EL Öl;Salz;Pfeffer;Paprikapulver|1. Reis kochen.\\n2. Gemüse klein schneiden.\\n3. Öl in einer Pfanne erhitzen.\\n4. Gemüse anbraten.\\n5. Reis dazugeben.\\n6. Alles würzen und 5 Minuten weiterbraten.\\n7. Abschmecken und servieren.
Blumenkohl überbacken|Deutsch|blumenkohl.jpg.jpg|4|45|Einfach|Ofengericht,Vegetarisch,Gemüse|1 Blumenkohl;250 ml Sahne;150 g Käse;1 EL Butter;Salz;Pfeffer;Muskat|1. Blumenkohl in Röschen teilen.\\n2. In Salzwasser 8 Minuten vorgaren.\\n3. In eine Auflaufform geben.\\n4. Sahne mit Salz, Pfeffer und Muskat würzen.\\n5. Sauce über den Blumenkohl geben.\\n6. Käse darüberstreuen.\\n7. Bei 180 °C ca. 25 Minuten überbacken.
Brokkoli Auflauf|Deutsch|brokkoliauflauf.jpg|4|45|Einfach|Ofengericht,Gemüse,Familie|500 g Brokkoli;300 g Kartoffeln;250 ml Sahne;150 g Käse;Salz;Pfeffer;Muskat|1. Kartoffeln schälen und in Scheiben schneiden.\\n2. Brokkoli in Röschen teilen.\\n3. Kartoffeln 8 Minuten vorkochen.\\n4. Brokkoli kurz blanchieren.\\n5. Alles in eine Form geben.\\n6. Sahne würzen und darübergeben.\\n7. Käse darüberstreuen.\\n8. Bei 180 °C ca. 30 Minuten backen.
Würstchengulasch|Deutsch|wuerstchengulasch.jpg|4|35|Einfach|Eintopf,Schnell,Familie|6 Würstchen;1 Zwiebel;1 Paprika;2 EL Tomatenmark;500 ml Brühe;1 Dose gehackte Tomaten;2 EL Öl;Paprikapulver;Salz;Pfeffer|1. Würstchen in Scheiben schneiden.\\n2. Zwiebel und Paprika würfeln.\\n3. Öl erhitzen und Würstchen anbraten.\\n4. Zwiebel und Paprika dazugeben.\\n5. Tomatenmark einrühren.\\n6. Mit Brühe und Tomaten ablöschen.\\n7. Würzen und 15 Minuten köcheln lassen.\\n8. Mit Nudeln oder Reis servieren.
Gefüllte Paprika|Deutsch|gefuelltepaprike.jpg|4|60|Mittel|Ofengericht,Hackfleisch,Gemüse|4 Paprika;500 g Hackfleisch;100 g Reis;1 Zwiebel;1 Ei;500 ml Tomatensauce;Salz;Pfeffer;Paprikapulver|1. Reis halb gar kochen.\\n2. Paprika waschen und Deckel abschneiden.\\n3. Hackfleisch mit Reis, Ei, Zwiebel und Gewürzen mischen.\\n4. Paprika füllen.\\n5. Tomatensauce in eine Form geben.\\n6. Paprika hineinsetzen.\\n7. Bei 180 °C ca. 45 Minuten backen.
Käsesuppe mit Hack|Deutsch|kaesesuppe.jpg|4|40|Einfach|Suppe,Hackfleisch,Herzhaft|500 g Hackfleisch;2 Stangen Lauch;1 Zwiebel;200 g Schmelzkäse;200 ml Sahne;700 ml Brühe;2 EL Öl;Salz;Pfeffer|1. Zwiebel würfeln und Lauch in Ringe schneiden.\\n2. Öl erhitzen und Hackfleisch anbraten.\\n3. Zwiebel und Lauch dazugeben.\\n4. Mit Brühe ablöschen.\\n5. 15 Minuten köcheln lassen.\\n6. Schmelzkäse und Sahne einrühren.\\n7. Mit Salz und Pfeffer abschmecken.
Burger|Amerikanisch|hamburger.jpg|4|35|Einfach|Fast Food,Hackfleisch,Familie|4 Burgerbrötchen;500 g Hackfleisch;4 Scheiben Käse;Salat;Tomaten;Gurken;Zwiebeln;Ketchup;Mayonnaise;Salz;Pfeffer|1. Hackfleisch mit Salz und Pfeffer würzen.\\n2. Vier Patties formen.\\n3. Patties in der Pfanne oder auf dem Grill braten.\\n4. Käse auflegen und schmelzen lassen.\\n5. Brötchen kurz anrösten.\\n6. Mit Sauce, Salat, Tomaten, Gurken, Zwiebeln und Patty belegen.\\n7. Sofort servieren.
Jägerschnitzel mit Nudeln|Deutsch|jaegerschnitzel.jpg|3|45|Mittel|Fleisch,Nudeln,Hausmannskost|3 Schnitzel;300 g Nudeln;250 g Champignons;1 Zwiebel;200 ml Sahne;200 ml Brühe;1 EL Mehl;2 EL Öl;Salz;Pfeffer|1. Nudeln kochen.\\n2. Schnitzel würzen und anbraten.\\n3. Herausnehmen und warm halten.\\n4. Zwiebel und Pilze in der Pfanne anbraten.\\n5. Mehl darüberstäuben.\\n6. Mit Brühe und Sahne ablöschen.\\n7. Sauce 10 Minuten köcheln lassen.\\n8. Schnitzel mit Sauce und Nudeln servieren.
Gyros Auflauf|Griechisch|gyrosauflauf.jpg|4|45|Einfach|Ofengericht,Fleisch,Familie|500 g Gyrosfleisch;300 g Nudeln;1 Paprika;1 Zwiebel;200 ml Sahne;150 g Käse;2 EL Öl;Pfeffer|1. Nudeln vorkochen.\\n2. Gyrosfleisch in Öl anbraten.\\n3. Paprika und Zwiebel schneiden und mitbraten.\\n4. Nudeln und Gyros in eine Form geben.\\n5. Sahne darübergeben.\\n6. Mit Käse bestreuen.\\n7. Bei 180 °C ca. 25 Minuten überbacken.
Nudeln mit Tomate-Mozzarella|Italienisch|tomatemozzarella.jpg|3|25|Einfach|Pasta,Vegetarisch,Schnell|350 g Nudeln;250 g Tomaten;200 g Mozzarella;2 EL Olivenöl;1 Knoblauchzehe;Basilikum;Salz;Pfeffer|1. Nudeln kochen.\\n2. Tomaten würfeln.\\n3. Knoblauch fein hacken.\\n4. Öl erhitzen und Knoblauch kurz anbraten.\\n5. Tomaten dazugeben und 5 Minuten köcheln.\\n6. Nudeln unterheben.\\n7. Mozzarella würfeln und kurz unterheben.\\n8. Mit Basilikum servieren.
Hirten-Makkaroni|Deutsch|hirtenmakkaroni.jpg|4|35|Einfach|Pasta,Hackfleisch,Familie|400 g Makkaroni;400 g Hackfleisch;1 Zwiebel;1 Paprika;200 g Feta;1 Dose Tomaten;2 EL Öl;Salz;Pfeffer;Oregano|1. Makkaroni kochen.\\n2. Zwiebel und Paprika würfeln.\\n3. Hackfleisch in Öl anbraten.\\n4. Zwiebel und Paprika dazugeben.\\n5. Tomaten einrühren und würzen.\\n6. 10 Minuten köcheln lassen.\\n7. Nudeln unterheben.\\n8. Feta zerbröseln und darübergeben.
Hühnerfrikassee|Deutsch|frikassee.jpg|4|60|Mittel|Hähnchen,Reis,Klassiker|600 g Hähnchenbrust;250 g Reis;500 ml Brühe;200 ml Sahne;200 g Erbsen;200 g Möhren;2 EL Butter;2 EL Mehl;Salz;Pfeffer;Zitronensaft|1. Hähnchen in Brühe gar ziehen lassen.\\n2. Fleisch herausnehmen und klein schneiden.\\n3. Reis kochen.\\n4. Butter schmelzen und Mehl einrühren.\\n5. Mit Brühe und Sahne ablöschen.\\n6. Erbsen und Möhren hinzufügen.\\n7. Hähnchenfleisch zurück in die Sauce geben.\\n8. Mit Salz, Pfeffer und Zitronensaft abschmecken.\\n9. Mit Reis servieren.
Pelmeni|Russisch|pelmeni.jpg|3|25|Einfach|Teigtaschen,Schnell,Herzhaft|500 g Pelmeni;1 EL Butter;150 g Schmand;Salz;Pfeffer;Dill|1. Pelmeni in kochendem Salzwasser garen, bis sie oben schwimmen.\\n2. Noch 3 bis 4 Minuten ziehen lassen.\\n3. Abgießen.\\n4. Mit Butter vermengen.\\n5. Mit Schmand, Pfeffer und Dill servieren.
Kohlrouladen|Deutsch|kohlrouladen.jpg|4|90|Mittel|Hausmannskost,Kohl,Hackfleisch|1 Weißkohl;600 g Hackfleisch;1 Brötchen;1 Ei;1 Zwiebel;500 ml Brühe;2 EL Öl;Salz;Pfeffer;Paprikapulver|1. Kohlblätter vorsichtig lösen und kurz blanchieren.\\n2. Brötchen einweichen und ausdrücken.\\n3. Hackfleisch mit Brötchen, Ei, Zwiebel und Gewürzen mischen.\\n4. Füllung auf Kohlblätter geben und aufrollen.\\n5. Rouladen fixieren.\\n6. In Öl rundherum anbraten.\\n7. Mit Brühe ablöschen.\\n8. Zugedeckt ca. 60 Minuten schmoren.\\n9. Mit Kartoffeln servieren.
Kartoffelgratin|Französisch|kartoffelauflauf.jpg|4|60|Einfach|Ofengericht,Kartoffeln,Vegetarisch|900 g Kartoffeln;250 ml Sahne;150 ml Milch;150 g Käse;1 Knoblauchzehe;1 EL Butter;Salz;Pfeffer;Muskat|1. Kartoffeln schälen und in dünne Scheiben schneiden.\\n2. Auflaufform mit Butter einfetten.\\n3. Knoblauch pressen und mit Sahne und Milch verrühren.\\n4. Mit Salz, Pfeffer und Muskat würzen.\\n5. Kartoffeln in die Form schichten.\\n6. Sahnemischung darübergeben.\\n7. Käse darüberstreuen.\\n8. Bei 180 °C ca. 45 Minuten backen.

Erdbeer-Bananen-Skyr Dessert|Neues Essen, neues Leben|erdbeer_bananen_skyr.png|2|20|Einfach|Frühstück,Dessert,Protein,Süß|400 g Erdbeeren;1–2 EL Erythrit;1 TL Zitronensaft;400 g Skyr;200 ml fettarme Milch;1 Päckchen Vanillepuddingpulver;2 kleine Bananen;150 g Frischkäse light;200 ml Protein-Sahne;1 Päckchen Sahnesteif;1 TL Vanilleextrakt;120–150 g Protein-Biskuit|1. Erdbeeren waschen, putzen und klein schneiden.\n2. Bananen in Scheiben schneiden und mit Zitronensaft sowie Süße vermengen.\n3. Vanillepudding mit Milch zubereiten und lauwarm abkühlen lassen.\n4. Skyr und Frischkäse glatt rühren und unter den Pudding mischen.\n5. Vanilleextrakt einrühren.\n6. Sahne mit Sahnesteif aufschlagen und vorsichtig unterheben.\n7. Dessert mit Biskuit, Früchten und Creme schichten.\n8. Mindestens 30 Minuten kaltstellen.
Fluffige Erdbeer-Proteincreme|Neues Essen, neues Leben|erdbeer_creme.png|2|15|Einfach|Frühstück,Dessert,Protein,Süß|250 g gefrorene Erdbeeren;32 g Proteinpulver Sahne;Chunky Flavour nach Wahl;ca. 100 ml gefrorene ungesüßte Mandelmilch;frische Erdbeeren optional;Light-Schokodrops optional|1. Gefrorene Erdbeeren grob mixen.\n2. Proteinpulver und etwas gefrorene Mandelmilch dazugeben.\n3. Die Masse mehrere Minuten aufschlagen, bis sie luftig und cremig wird.\n4. Nach Bedarf weitere Flüssigkeit einarbeiten.\n5. In eine Schale füllen und nach Wunsch toppen.
Froschgrütze|Neues Essen, neues Leben|froschgruetze.png|2|10|Einfach|Frühstück,Dessert,Protein,Süß|1 Tüte ungesüßte Götterspeise Waldmeister;Chunky Flavour nach Wahl;250 ml heißes Wasser;500 g Magerquark|1. Götterspeise in eine Schüssel geben.\n2. Mit heißem Wasser übergießen und gründlich verrühren.\n3. Chunky Flavour nach Geschmack einrühren.\n4. Magerquark nach und nach unterrühren.\n5. Über Nacht im Kühlschrank fest werden lassen.\n6. Gut gekühlt servieren.
Thunfisch-Frischkäse-Aufstrich|Neues Essen, neues Leben|tunfisch_aufstrich.png|2|15|Einfach|Frühstück,Protein,Herzhaft,Schnell|1 Dose Thunfisch;1 kleine Paprika;1 Lauchzwiebel;1 EL Tomatenmark;1 Dose Mais;200 g Kräuterfrischkäse light;1 EL Miracle Whip light;Eisbergsalat;4 Scheiben Eiweißbrot|1. Thunfisch und Mais abtropfen lassen und vermengen.\n2. Paprika fein würfeln und Lauchzwiebel in Ringe schneiden.\n3. Gemüse, Frischkäse, Miracle Whip und Tomatenmark zum Thunfisch geben.\n4. Alles cremig verrühren.\n5. Eiweißbrot nach Wunsch toasten.\n6. Mit Salat belegen und den Aufstrich darauf verteilen.
High Protein Käse-Flatbread|Neues Essen, neues Leben||2|30|Einfach|Frühstück,Protein,Herzhaft,Pfanne|130 g Weizenmehl;200 g Hüttenkäse fettarm;Salz;30 g Proteinpulver neutral;ca. 60 g Mozzarella light;Kräuter optional;Knoblauch optional|1. Hüttenkäse im Mixer glatt pürieren.\n2. Mehl, Proteinpulver, Hüttenkäse und Salz zu einem Teig verkneten.\n3. Teig etwa 10 Minuten ruhen lassen.\n4. Teig halbieren und dünn ausrollen.\n5. Mozzarella in die Mitte geben.\n6. Teig darüberfalten und wieder vorsichtig flachrollen.\n7. In einer heißen Pfanne etwa 5 Minuten pro Seite goldbraun braten.
Protein-Chia-Pudding mit Erdbeeren und Schokolade|Neues Essen, neues Leben|schokopudding.png|2|10|Einfach|Frühstück,Dessert,Protein,Süß|200–250 g Joghurt pur;20 g gefriergetrocknete Erdbeeren;20 g Chiasamen;1 TL Honig;dunkle Schokolade nach Belieben|1. Joghurt, Chiasamen, Honig und Erdbeeren gründlich verrühren.\n2. Die Mischung mindestens 2 Stunden im Kühlschrank quellen lassen.\n3. Vor dem Servieren mit geschmolzener dunkler Schokolade beträufeln.\n4. Nach Wunsch mit weiteren Erdbeeren dekorieren.
Protein-Schokobrötchen|Neues Essen, neues Leben|schokobroetchen.png|4|35|Einfach|Frühstück,Protein,Süß,Backen|250 g Magerquark;50 g Proteinpulver Sahne;50 g Schokoladentropfen;100 g Dinkelmehl;1 TL Backpulver;Chunky Flavour Vanille|1. Backofen auf 170 °C Ober-/Unterhitze vorheizen.\n2. Magerquark, Proteinpulver und Chunky Flavour glatt verrühren.\n3. Dinkelmehl und Backpulver unterkneten.\n4. Schokoladentropfen unterheben.\n5. Kleine Brötchen formen und auf ein Backblech legen.\n6. Etwa 25 Minuten goldgelb backen.
High Protein Käse-Brezeln|Neues Essen, neues Leben|kaesebrezel.png|3|30|Einfach|Frühstück,Protein,Herzhaft,Backen|500 g Skyr;10 g Backpulver;1 Eigelb;350 g Dinkelmehl;100 g Light-Reibekäse;grobes Salz|1. Skyr, Dinkelmehl, Backpulver, Reibekäse, Eigelb und Salz zu einem Teig verkneten.\n2. Teig in 2–3 Portionen teilen.\n3. Aus den Portionen Brezeln formen.\n4. Auf ein Backblech legen.\n5. Bei 200 °C Umluft etwa 20 Minuten goldbraun backen.\n6. Nach Wunsch aufschneiden und belegen.
Quark-Bagels mit Mohn und Sonnenblumenkernen|Neues Essen, neues Leben|bagle.png|4|35|Einfach|Frühstück,Protein,Backen,Herzhaft|250 g Magerquark;300 g Dinkelmehl Type 630;1 TL Salz;1 TL Backpulver;2 EL Olivenöl;etwas Wasser;2 TL Mohn;2 TL Sonnenblumenkerne|1. Backofen auf 180 °C Ober-/Unterhitze vorheizen.\n2. Magerquark mit Öl und Salz glatt verrühren.\n3. Backpulver und Mehl einarbeiten.\n4. Alles zu einem formbaren Teig verkneten.\n5. Teig in vier Portionen teilen und Bagels formen.\n6. Oberfläche leicht mit Wasser bestreichen.\n7. Mit Mohn und Sonnenblumenkernen bestreuen.\n8. 20–25 Minuten goldbraun backen.
Quark-Himbeer-Frühstück aus dem Ofen|Neues Essen, neues Leben|himbeer_fruestueck.png|2|38|Einfach|Frühstück,Protein,Süß,Ofengericht|250 g Magerquark;200 g Frischkäse;2 Eier;50 g gemahlene Mandeln;40 g Erythrit;80 g Himbeeren;1 Prise Salz|1. Backofen auf 170 °C Umluft vorheizen.\n2. Magerquark, Frischkäse, Eier, Erythrit, Mandeln und Salz cremig verrühren.\n3. Himbeeren vorsichtig unterheben.\n4. Masse in eine ofenfeste Form geben.\n5. Etwa 30 Minuten backen, bis die Oberfläche leicht goldbraun ist.\n6. Warm oder kalt genießen.
Protein-Pfannkuchen Vanille|Neues Essen, neues Leben|panecake_vanille.png|2|17|Einfach|Frühstück,Protein,Süß,Pfanne|3 Eier;70 g Magerquark;5 g Vanille-Proteinpulver;90 ml Mandelmilch;1 Prise Salz;50 g Dinkelmehl Type 630|1. Eier, Mandelmilch und Magerquark in einer Schüssel verrühren.\n2. Dinkelmehl, Proteinpulver und Salz dazugeben.\n3. Alles zu einem glatten Teig verrühren.\n4. Eine Pfanne leicht einfetten.\n5. Teig portionsweise dünn ausbacken.\n6. Warm servieren.
High Protein Waffeln|Neues Essen, neues Leben|protein_waffel.png|2|15|Einfach|Frühstück,Protein,Süß,Waffeln|200 g proteinreicher Vanillepudding;25 g Protein-Eiskaffee Honig-Karamell-Waffel;1 Ei;25 g Dinkelmehl;3 g Backpulver;Light-Schokodrops optional;etwas Ölspray|1. Alle Zutaten in einer Schüssel verrühren.\n2. So lange rühren, bis ein glatter cremiger Teig entsteht.\n3. Waffeleisen vorheizen und leicht einsprühen.\n4. Teig portionsweise einfüllen.\n5. Waffeln goldbraun backen.\n6. Nach Wunsch mit Schokodrops oder Früchten servieren.
Protein-Quarkbrötchen mit Körnerkruste|Neues Essen, neues Leben|quarkbroetchen.png|4|30|Einfach|Frühstück,Protein,Backen,Herzhaft|200 g Dinkelmehl;330 g Magerquark;¾ Päckchen Backpulver;¾ TL Salz;45 g Körner zum Wälzen|1. Airfryer-Korb oder Backblech mit Backpapier auslegen.\n2. Dinkelmehl, Magerquark, Backpulver und Salz in eine Schüssel geben.\n3. Alles zu einem glatten Teig verkneten.\n4. Teig in vier Portionen teilen und Brötchen formen.\n5. Brötchen in Körnern wälzen und leicht andrücken.\n6. Im Airfryer bei 165 °C etwa 25 Minuten backen.\n7. Alternativ im Backofen bei 180 °C Umluft etwa 30 Minuten backen.
Protein-Pfannkuchen mit Apfelmark|Neues Essen, neues Leben|panecake_apfelmark.png|2|20|Einfach|Frühstück,Protein,Süß,Pfanne|60 g Mehl;270 ml ungesüßte Mandelmilch;1–2 Scoops Chunky Flavour Vanille;2 Eier;50 g Proteinpulver Sahne;10 ml Sprudelwasser optional;Apfelmark zum Servieren;Früchte optional|1. Alle Zutaten für die Pfannkuchen in einer Schüssel verrühren.\n2. Eine beschichtete Pfanne leicht einfetten.\n3. Teig portionsweise hineingeben.\n4. Pfannkuchen von beiden Seiten goldbraun ausbacken.\n5. Mit Apfelmark servieren.\n6. Nach Wunsch mit frischen Früchten toppen.
Frühstücks-Wrap|Neues Essen, neues Leben|fruestueck_wrap.png|1|10|Einfach|Frühstück,Protein,Herzhaft,Schnell|1 Low-Carb-Wrap;2 Eier;30 g Frischkäse;30 g geriebener Käse;Salz;Pfeffer|1. Eier in einer Pfanne zu Rührei braten.\n2. Mit Salz und Pfeffer würzen.\n3. Wrap mit Frischkäse bestreichen.\n4. Rührei auf dem Wrap verteilen.\n5. Geriebenen Käse darüberstreuen.\n6. Wrap einrollen.\n7. Optional kurz in der Pfanne anbraten.
Protein Brötchen Brot|Neues Essen, neues Leben|protein_brot.png|4|45|Einfach|Frühstück,Protein,Backen,Grundrezept|350 g Dinkelmehl;380 g Skyr;9 g Backpulver;1 Ei;1 TL Olivenöl;1 Prise Salz;etwas Speisestärke optional|1. Dinkelmehl mit Backpulver und Salz vermischen.\n2. Skyr, Ei und Olivenöl hinzufügen.\n3. Alles zuerst mit einem Löffel, dann mit den Händen verkneten.\n4. Bei Bedarf etwas Speisestärke verwenden, damit der Teig formbar wird.\n5. Teig zu Brötchen, Brot oder Fladen formen.\n6. Nach gewünschter Form backen, bis er goldbraun ist.
Proteinreiche Skyr-Stangen|Neues Essen, neues Leben|skyr_stangen.png|4|45|Einfach|Frühstück,Protein,Backen,Herzhaft|250 g Skyr;150 g Mehl;½ Päckchen Backpulver;1 Prise Salz;etwas Wasser;Salatkernmischung|1. Skyr, Mehl, Backpulver und Salz in eine Schüssel geben.\n2. Zu einem geschmeidigen Teig verkneten.\n3. Backofen auf 180 °C Ober-/Unterhitze vorheizen.\n4. Teig in vier Portionen teilen und zu Stangen formen.\n5. Stangen leicht mit Wasser bestreichen.\n6. In der Kernmischung wälzen.\n7. Auf ein Backblech legen und 25–30 Minuten goldbraun backen.
Apfel Pancakes|Frühstück|apfel_panecake.png|2|20|Einfach|Frühstück,Süß,Vegetarisch|2 Äpfel;2 Eier;120 g Mehl;200 ml Milch;1 TL Backpulver;1 TL Zimt;1 EL Zucker;Butter|1. Äpfel schälen und fein raspeln.\n2. Eier mit Milch verrühren.\n3. Mehl, Backpulver, Zucker und Zimt einrühren.\n4. Apfelraspel unterheben.\n5. Butter in einer Pfanne erhitzen.\n6. Kleine Pancakes portionsweise ausbacken.\n7. Goldbraun wenden und servieren.

Apfelkuchen Bowl|Dessert|apfelkuchen_bowl.png|2|10|Einfach|Dessert,Süß,Schnell|250 g Skyr;1 Apfel;30 g Haferflocken;1 TL Zimt;1 TL Honig;10 g Walnüsse|1. Apfel klein würfeln.\n2. Mit Zimt kurz in der Pfanne anbraten.\n3. Skyr in eine Schüssel geben.\n4. Haferflocken und Apfel darauf verteilen.\n5. Mit Honig und Walnüssen toppen.

Auflauf Fischstäbchen|Abendessen|auflauf_fischstaebchen.png|4|35|Einfach|Auflauf,Familie,Fisch|10 Fischstäbchen;800 g Kartoffeln;200 ml Sahne;150 g Käse;Salz;Pfeffer;Muskat|1. Kartoffeln schälen und in Scheiben schneiden.\n2. Kurz vorkochen.\n3. In eine Auflaufform geben.\n4. Sahne würzen und darüber verteilen.\n5. Fischstäbchen darauflegen.\n6. Käse darübergeben.\n7. Bei 180 °C 25 Minuten backen.

Bagel|Snack|bagle.png|2|15|Einfach|Snack,Schnell,Frühstück|2 Bagels;100 g Frischkäse;Salat;Tomaten;Gurke;Putenbrust|1. Bagels halbieren.\n2. Mit Frischkäse bestreichen.\n3. Mit Salat, Tomaten, Gurke und Putenbrust belegen.\n4. Zusammenklappen und servieren.

Blueberry Dessert|Dessert|blaubeer_dessert.png|2|10|Einfach|Dessert,Süß,Schnell|250 g Skyr;100 g Blaubeeren;20 g Granola;1 TL Honig|1. Skyr in Gläser geben.\n2. Blaubeeren darauf verteilen.\n3. Granola darüberstreuen.\n4. Mit Honig servieren.


Cheesecake Bowl|Dessert|cheesecake_bowl.png|2|10|Einfach|Dessert,Süß,Protein|250 g Frischkäse light;150 g Skyr;1 TL Honig;Keksbrösel;Beeren|1. Frischkäse und Skyr cremig verrühren.\n2. In Schalen geben.\n3. Mit Beeren und Keksbröseln toppen.

Churros|Dessert|churros.png|2|25|Einfach|Dessert,Süß,Snack|100 g Mehl;150 ml Wasser;1 EL Zucker;1 Prise Salz;Zimt;Zucker;Öl|1. Wasser mit Zucker und Salz erhitzen.\n2. Mehl einrühren bis ein Teig entsteht.\n3. In einen Spritzbeutel füllen.\n4. In heißes Öl spritzen.\n5. Goldbraun ausbacken.\n6. In Zimt-Zucker wenden.

Corndogs|Snack|corndogs.png|2|30|Einfach|Snack,Fast Food,Herzhaft|4 Würstchen;120 g Mehl;80 g Maismehl;1 Ei;150 ml Milch;1 TL Backpulver;Öl|1. Würstchen auf Spieße stecken.\n2. Teig aus allen Zutaten herstellen.\n3. Würstchen eintauchen.\n4. In heißem Öl goldbraun ausbacken.

Erdbeerpudding|Dessert|erdbeerpudding.png|2|15|Einfach|Dessert,Süß|500 ml Milch;1 Puddingpulver;150 g Erdbeeren;1 EL Zucker|1. Pudding nach Anleitung kochen.\n2. Erdbeeren klein schneiden.\n3. Unterheben oder darübergeben.\n4. Kalt stellen.

Erdnuss Schnitte|Dessert|erdnuss_schnitte.png|4|20|Einfach|Dessert,Süß,Protein|150 g Haferflocken;80 g Erdnussbutter;2 EL Honig;100 g Skyr|1. Alles vermengen.\n2. In eine Form drücken.\n3. Kalt stellen.\n4. In Stücke schneiden.

Friss dich dumm Suppe|Suppe|friss_dich_dumm_suppe.png|4|35|Einfach|Suppe,Herzhaft,Familie|500 g Hackfleisch;1 Zwiebel;1 Paprika;1 Dose Mais;1 Dose Tomaten;500 ml Brühe;200 g Schmelzkäse|1. Hackfleisch anbraten.\n2. Gemüse dazugeben.\n3. Brühe und Tomaten hinzufügen.\n4. 15 Minuten köcheln.\n5. Schmelzkäse einrühren.

Froschgrütze|Dessert|froschgruetze.png|2|10|Einfach|Dessert,Süß|1 Packung Wackelpudding;500 ml Wasser;Vanillesoße|1. Wackelpudding nach Anleitung kochen.\n2. Abkühlen lassen.\n3. Mit Vanillesoße servieren.

Fruchtschnitten|Snack|fruchtschnitten.png|4|15|Einfach|Snack,Süß|150 g Haferflocken;2 Bananen;100 g Trockenfrüchte|1. Alles pürieren.\n2. In eine Form drücken.\n3. Backen oder kalt stellen.\n4. In Riegel schneiden.

Fruestueck Wrap|Frühstück|fruestueck_wrap.png|2|10|Einfach|Frühstück,Schnell|2 Wraps;2 Eier;Frischkäse;Salat;Tomaten|1. Eier anbraten.\n2. Wraps bestreichen.\n3. Mit Zutaten füllen.\n4. Einrollen.

Gartenpasta|Nudeln|gartenpasta.png|3|25|Einfach|Pasta,Vegetarisch|300 g Pasta;Zucchini;Paprika;Tomaten;200 ml Sahne;Parmesan|1. Pasta kochen.\n2. Gemüse anbraten.\n3. Sahne hinzufügen.\n4. Pasta unterheben.\n5. Mit Parmesan servieren.

Gnocchi Pfanne|Abendessen|gnocchi.png|3|20|Einfach|Gnocchi,Schnell|500 g Gnocchi;1 Zwiebel;200 g Tomaten;100 g Mozzarella|1. Gnocchi anbraten.\n2. Gemüse hinzufügen.\n3. Mozzarella darübergeben.\n4. Kurz schmelzen lassen.
Hack mit Gemüse|Abendessen|hack_mit_gemüse.png|3|25|Einfach|Hackfleisch,Low Carb,Herzhaft|500 g Hackfleisch;1 Zucchini;1 Paprika;1 Zwiebel;2 EL Öl;Salz;Pfeffer;Paprikapulver|1. Hackfleisch in Öl krümelig anbraten.\n2. Gemüse klein schneiden.\n3. Zum Hack geben.\n4. Würzen.\n5. 10 Minuten braten und servieren.

Hähnchen Brokkoli Pasta|Nudeln|haehnchen_brokkoli_pasta.png|3|30|Einfach|Pasta,Hähnchen,Familie|300 g Pasta;400 g Hähnchenbrust;300 g Brokkoli;200 ml Sahne;Parmesan;Salz;Pfeffer|1. Pasta kochen.\n2. Brokkoli kurz vorgaren.\n3. Hähnchen anbraten.\n4. Sahne hinzufügen.\n5. Alles vermengen.\n6. Parmesan darübergeben.

Hähnchen Paprika Auflauf|Auflauf|haehnchen_paprika_auflauf.png|4|35|Einfach|Auflauf,Hähnchen,Familie|500 g Hähnchenbrust;2 Paprika;250 ml Sahne;150 g Käse;Gewürze|1. Hähnchen würfeln.\n2. Paprika schneiden.\n3. In eine Auflaufform geben.\n4. Sahne würzen und darübergeben.\n5. Käse darüber.\n6. Backen.

Hähnchenbissen|Snack|haehnchenbissen.png|2|20|Einfach|Snack,Hähnchen,Protein|400 g Hähnchenbrust;Paniermehl;1 Ei;Salz;Pfeffer|1. Hähnchen in Stücke schneiden.\n2. Würzen.\n3. Panieren.\n4. Im Ofen oder in der Pfanne goldbraun garen.

Hähnchenbrust Kräutersauce|Abendessen|haehnchenbrust_kraeutersauce.png|2|30|Einfach|Hähnchen,Herzhaft|2 Hähnchenbrüste;200 ml Sahne;Kräuter;1 Zwiebel;Salz;Pfeffer|1. Hähnchen anbraten.\n2. Zwiebel dazugeben.\n3. Sahne und Kräuter hinzufügen.\n4. Kurz köcheln lassen.

Hähnchen Wrap|Snack|haehnchenwrap.png|2|15|Einfach|Wrap,Schnell,Hähnchen|2 Wraps;300 g Hähnchen;Salat;Tomaten;Joghurtsoße|1. Hähnchen anbraten.\n2. Gemüse schneiden.\n3. Alles in Wraps füllen.\n4. Einrollen.

Himbeer Chia Quark|Frühstück|himbeer_chia_quark.png|2|5|Einfach|Frühstück,Süß,Protein|250 g Quark;100 g Himbeeren;2 EL Chiasamen;1 TL Honig|1. Alles vermengen.\n2. Kurz ziehen lassen.\n3. Servieren.

Himbeer Frühstück|Frühstück|himbeer_fruestueck.png|2|5|Einfach|Frühstück,Schnell|250 g Skyr;Himbeeren;Granola;Honig|1. Alles in eine Bowl geben.\n2. Direkt servieren.

Himbeertraum|Dessert|himbeertraum.png|2|10|Einfach|Dessert,Süß|200 g Himbeeren;200 g Skyr;100 ml Sahne;Keksbrösel|1. Himbeeren pürieren.\n2. Creme anrühren.\n3. Schichten.\n4. Kühlen.

Käse Patties|Snack|kaese_patties.png|2|20|Einfach|Snack,Herzhaft|200 g Käse;2 Eier;Paniermehl|1. Käse formen.\n2. Panieren.\n3. Goldbraun ausbacken.

Käsebrezel|Snack|kaesebrezel.png|2|10|Einfach|Snack,Schnell|2 Brezeln;Käse;Butter|1. Brezeln aufschneiden.\n2. Mit Butter und Käse belegen.\n3. Kurz überbacken.

Mini Pizza|Snack|pizzataler.png|2|20|Einfach|Snack,Pizza,Schnell|Toast;Tomatensauce;Käse;Belag|1. Toast belegen.\n2. Käse drauf.\n3. Überbacken.



"""




def builtin_recipe_rows() -> list[tuple]:
    rows = []
    seen = set()

    for line in BUILTIN_RECIPE_TEXT.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("|")
        if len(parts) != 9:
            print("Überspringe ungültige Rezeptzeile:", line[:80])
            continue

        name, kueche, bild, portionen, kochzeit, schwierigkeit, tags, zutaten, anleitung = parts

        if name in seen:
            continue
        seen.add(name)

        try:
            portionen_int = int(portionen)
        except Exception:
            portionen_int = 2

        try:
            kochzeit_int = int(kochzeit)
        except Exception:
            kochzeit_int = 30

        rows.append((name.strip(), kueche.strip() or "Unbekannt", bild.strip(), max(1, portionen_int), max(1, kochzeit_int), schwierigkeit.strip() or "Einfach",
                     [tag.strip() for tag in tags.split(",") if tag.strip()], [zutat.strip() for zutat in zutaten.split(";") if zutat.strip()],
                     anleitung.replace("\\n", "\n").strip() or "Keine Anleitung vorhanden."))

    return rows

def external_recipe_rows() -> list[tuple]:
    if not DATA_RECIPE_PATH.exists():
        return []

    with DATA_RECIPE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    rows = []

    for item in data:
        name = str(item.get("name", "")).strip()
        if not name:
            continue

        rows.append((
            name,
            str(item.get("kueche", "Unbekannt")).strip() or "Unbekannt",
            str(item.get("bild", "")).strip(),
            max(1, int(item.get("portionen", 2) or 2)),
            max(1, int(item.get("kochzeit", 30) or 30)),
            str(item.get("schwierigkeit", "Einfach")).strip() or "Einfach",
            item.get("tags", []) if isinstance(item.get("tags", []), list) else [],
            item.get("zutaten", []) if isinstance(item.get("zutaten", []), list) else [],
            str(item.get("anleitung", "")).strip() or "Keine Anleitung vorhanden."
        ))

    return rows

class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        LOCAL_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

        self.init_schema()
        self.seed_if_empty()
        self.import_builtin_recipes()
        self.import_external_recipes()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                kueche TEXT NOT NULL DEFAULT 'Unbekannt',
                bild TEXT NOT NULL DEFAULT '',
                portionen INTEGER NOT NULL DEFAULT 2,
                kochzeit INTEGER NOT NULL DEFAULT 30,
                schwierigkeit TEXT NOT NULL DEFAULT 'Einfach',
                tags_json TEXT NOT NULL DEFAULT '[]',
                favorit INTEGER NOT NULL DEFAULT 0,
                zutaten_json TEXT NOT NULL DEFAULT '[]',
                anleitung TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS weekly_plan (
                day TEXT PRIMARY KEY,
                recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS profile_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """)

        for day in DAYS:
            self.conn.execute(
                "INSERT OR IGNORE INTO weekly_plan(day, recipe_id) VALUES (?, NULL)",
                (day,),
            )

        self.conn.commit()

    def seed_if_empty(self) -> None:
        count = self.conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]

        if count:
            return

        examples = [Rezept(name="Spaghetti Bolognese", kueche="Italienisch", bild="Bolognese.jpg", portionen=2, kochzeit=35,
                           schwierigkeit="Einfach", tags=["Pasta", "Herzhaft", "Familie"],zutaten=["250 g Spaghetti",
                                                                                                   "300 g Hackfleisch",
                                                                                                   "1 Zwiebel",
                                                                                                   "1 Dose gehackte Tomaten",
                                                                                                   "2 EL Öl",
                                                                                                   "Salz",
                                                                                                   "Pfeffer"],
                           anleitung=("1. Spaghetti kochen.\n"
                                      "2. Zwiebel anbraten.\n"
                                      "3. Hackfleisch dazugeben.\n"
                                      "4. Tomaten hinzufügen.\n"
                                      "5. Köcheln lassen.\n"
                                      "6. Servieren.")),
            Rezept(name="Pizza Margherita", kueche="Italienisch", bild="pizza.jpg", portionen=2, kochzeit=25, schwierigkeit="Einfach",
                   tags=["Vegetarisch", "Pizza", "Schnell"], zutaten=["1 Pizzateig",
                                                                      "200 g Tomatensauce",
                                                                      "200 g Mozzarella",
                                                                      "Basilikum",
                                                                      "Olivenöl"],
                   anleitung=("1. Teig ausrollen.\n"
                              "2. Sauce verteilen.\n"
                              "3. Mozzarella darauf geben.\n"
                              "4. Backen.\n"
                              "5. Mit Basilikum servieren.")),
            Rezept(name="Omelett", kueche="Frühstück", bild="omelett.jpg", portionen=1, kochzeit=10, schwierigkeit="Einfach",
                   tags=["Frühstück", "Schnell", "Low Budget"], zutaten=["3 Eier", "1 EL Butter", "Salz", "Pfeffer", "optional: Käse oder Gemüse",],
                   anleitung=("1. Eier verquirlen.\n"
                              "2. Butter erhitzen.\n"
                              "3. Eiermasse braten.\n"
                              "4. Füllen und zusammenklappen."))]

        for recipe in examples:
            self.save_recipe(recipe)
            self.conn.commit()

    def import_builtin_recipes(self) -> None:
        imported = 0
        updated = 0

        for name, kueche, bild, portionen, kochzeit, schwierigkeit, tags, zutaten, anleitung in builtin_recipe_rows():
            existing = self.conn.execute("SELECT id, bild FROM recipes WHERE name = ?", (name,)).fetchone()

            if existing:
                if bild and existing["bild"] != bild:
                    self.conn.execute(
                        "UPDATE recipes SET bild = ? WHERE id = ?",
                        (bild, existing["id"]),
                    )
                    updated += 1
                continue

            recipe = Rezept(
                name=name,
                kueche=kueche,
                bild=bild,
                portionen=portionen,
                kochzeit=kochzeit,
                schwierigkeit=schwierigkeit,
                tags=tags,
                favorit=False,
                zutaten=zutaten,
                anleitung=anleitung,
            )
            self.save_recipe(recipe)
            imported += 1

        self.conn.commit()

        if imported or updated:
            print(f"Fest eingebaute Rezepte importiert: {imported}, Bilder aktualisiert: {updated}")

    def import_external_recipes(self) -> None:
        imported = 0
        updated = 0

        for name, kueche, bild, portionen, kochzeit, schwierigkeit, tags, zutaten, anleitung in external_recipe_rows():
            existing = self.conn.execute(
                "SELECT id FROM recipes WHERE name = ?",
                (name,),
            ).fetchone()

            if existing:
                self.conn.execute(
                    """
                    UPDATE recipes
                    SET kueche=?, bild=?, portionen=?, kochzeit=?, schwierigkeit=?,
                        tags_json=?, zutaten_json=?, anleitung=?
                    WHERE id=?
                    """,
                    (
                        kueche,
                        bild,
                        portionen,
                        kochzeit,
                        schwierigkeit,
                        json.dumps(tags, ensure_ascii=False),
                        json.dumps(zutaten, ensure_ascii=False),
                        anleitung,
                        existing["id"],
                    ),
                )
                updated += 1
                continue

            recipe = Rezept(
                name=name,
                kueche=kueche,
                bild=bild,
                portionen=portionen,
                kochzeit=kochzeit,
                schwierigkeit=schwierigkeit,
                tags=tags,
                favorit=False,
                zutaten=zutaten,
                anleitung=anleitung,
            )

            self.save_recipe(recipe)
            imported += 1

        self.conn.commit()

        if imported or updated:
            print(f"Externe Rezepte importiert: {imported}, aktualisiert: {updated}")
    
    def row_to_recipe(self, row: sqlite3.Row) -> Rezept:
        return Rezept(
            id=row["id"],
            name=row["name"],
            kueche=row["kueche"],
            bild=row["bild"],
            portionen=row["portionen"],
            kochzeit=row["kochzeit"],
            schwierigkeit=row["schwierigkeit"],
            tags=json.loads(row["tags_json"] or "[]"),
            favorit=bool(row["favorit"]),
            zutaten=json.loads(row["zutaten_json"] or "[]"),
            anleitung=row["anleitung"] or "Keine Anleitung vorhanden.",
        )

    def all_recipes(self) -> list[Rezept]:
        rows = self.conn.execute(
            "SELECT * FROM recipes ORDER BY favorit DESC, name COLLATE NOCASE"
        ).fetchall()
        return [self.row_to_recipe(row) for row in rows]

    def get_recipe(self, recipe_id: int) -> Rezept | None:
        row = self.conn.execute(
            "SELECT * FROM recipes WHERE id = ?",
            (recipe_id,),
        ).fetchone()
        return self.row_to_recipe(row) if row else None

    def save_recipe(self, recipe: Rezept) -> int:
        payload = (
            recipe.name.strip(),
            recipe.kueche.strip() or "Unbekannt",
            recipe.bild.strip(),
            max(1, int(recipe.portionen)),
            max(1, int(recipe.kochzeit)),
            recipe.schwierigkeit,
            json.dumps(recipe.tags, ensure_ascii=False),
            1 if recipe.favorit else 0,
            json.dumps(recipe.zutaten, ensure_ascii=False),
            recipe.anleitung.strip() or "Keine Anleitung vorhanden.",
        )

        if recipe.id is None:
            cur = self.conn.execute(
                """
                INSERT INTO recipes
                (name, kueche, bild, portionen, kochzeit, schwierigkeit,
                 tags_json, favorit, zutaten_json, anleitung)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            self.conn.commit()
            return int(cur.lastrowid)

        self.conn.execute(
            """
            UPDATE recipes
            SET name=?, kueche=?, bild=?, portionen=?, kochzeit=?, schwierigkeit=?,
                tags_json=?, favorit=?, zutaten_json=?, anleitung=?
            WHERE id=?
            """,
            (*payload, recipe.id),
        )
        self.conn.commit()
        return recipe.id

    def delete_recipe(self, recipe_id: int) -> None:
        self.conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        self.conn.commit()

    def delete_recipes_without_images(self) -> int:
        cur = self.conn.execute("""
        DELETE FROM recipes
        WHERE bild IS NULL
           OR TRIM(bild) = ''
    """)
        self.conn.commit()
        return cur.rowcount

    def toggle_favorite(self, recipe_id: int) -> None:
        self.conn.execute(
            "UPDATE recipes SET favorit = CASE favorit WHEN 1 THEN 0 ELSE 1 END WHERE id = ?",
            (recipe_id,),
        )
        self.conn.commit()

    def weekly_plan(self) -> dict[str, int | None]:
        rows = self.conn.execute("SELECT day, recipe_id FROM weekly_plan").fetchall()
        return {row["day"]: row["recipe_id"] for row in rows}

    def set_weekly_plan(self, plan: dict[str, int | None]) -> None:
        for day, recipe_id in plan.items():
            self.conn.execute(
                "UPDATE weekly_plan SET recipe_id = ? WHERE day = ?",
                (recipe_id, day),
            )
        self.conn.commit()

    def add_profile_event(self, kind: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO profile_events(kind, value) VALUES (?, ?)",
            (kind, value),
        )
        self.conn.commit()

    def profile_values(self, kind: str, limit: int = 300) -> list[str]:
        rows = self.conn.execute(
            "SELECT value FROM profile_events WHERE kind = ? ORDER BY id DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
        return [row["value"] for row in rows]