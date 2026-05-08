import json
import sqlite3
from pathlib import Path

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