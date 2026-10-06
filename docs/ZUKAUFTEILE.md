# Zukaufteile (Elektronik, Kohlefaser, Draht, Kleinteile)

Alle Angaben passen zu den Maßen der gedruckten Teile. Gewichte sind Richtwerte; sie gehen in die
Schwerpunktrechnung ein (`cessna/params.py`, Abschnitt `BOUGHT_PARTS`).

## Antrieb

| Teil | Empfehlung | Menge |
|---|---|---:|
| Außenläufer | Klasse 28xx, ca. 1000–1100 kV, Ø 28 mm, ca. 70–80 g, Befestigung 16/19-mm-Kreuz (M3) | 1 |
| Regler | 30 A (besser 40 A), BEC ≥ 3 A | 1 |
| Luftschraube | 10×6″ (z. B. APC 10×6 E), 2 Blatt | 1 |
| Propelleradapter | mit Mitnehmerscheibe, Welle passend zum Motor (3,17 / 4 / 5 mm) | 1 |
| Akku | LiPo 3S 2200 mAh, ≥ 25C, **max. 115 × 35 × 26 mm**, ca. 190 g | 1 |

Richtwerte (nicht geflogen!): 3S + 1000 kV + 10×6″ → ca. 22–26 A, 250–300 W, Standschub ca. 800–950 g,
Schub/Gewicht ≈ 0,5–0,6.

## Funkanlage

| Teil | Hinweis | Menge |
|---|---|---:|
| Empfänger | mind. 5 Kanäle (Quer, Höhe, Seite, Gas; Querruder über Y-Kabel oder 2 Kanäle) | 1 |
| Servos 9 g | Mikroservos mit Metallgetriebe für Seite/Höhe empfohlen; **Abmessungen 23 × 12,4 × 22,8 mm, Flansch 32,5 mm** | 5 |
| Servo-Verlängerung | ca. 300 mm für die Querruder (Wurzel → Kabine), Y-Kabel | 2 |
| Y-Kabel | Bugradlenkung auf dem Seitenruder-Kanal mitführen | 1 |

Servo-Verteilung: 2× Querruder (im Flügel, Abtrieb nach unten), 1× Höhenruder (Rumpf links, Heck),
1× Seitenruder (Rumpf rechts, Heck), 1× Bugradlenkung (Bug links).

## Kohlefaser / Draht (Zuschnitt in mm)

| Teil | Maß | Menge | Verwendung |
|---|---|---:|---|
| CFK-Rohr 10/8 mm | **660** | 2 | Flügelholm (links/rechts) |
| CFK-Stab Ø 7,8 mm (oder 8 mm abschleifen) | 200 | 1 | Flächenverbinder in der Mitte |
| CFK-Stab Ø 4 mm | 395 | 1 | Holm Höhenflosse (durch beide Hälften) |
| CFK-Stab Ø 2 mm | 370 | 1 | Höhenruder-Verbindung (durch beide Nasen) |
| CFK-Stab/Stahl Ø 2 mm | je ca. 340 | 2 | Gestänge Höhen-/Seitenruder im Rumpf (ab Servo) |
| Stahldraht Ø 1,5 mm | je ca. 60 | 2 | Gestänge Querruder (mit Gabelkopf) |
| Stahldraht Ø 1,5 mm | je ca. 40 | 2 | Z-Bügel Heck (Austritt Rumpf → Horn) |
| Stahldraht Ø 1,2 mm | ca. 45 | 1 | Bugradlenkung (Servo → Lenkhebel) |
| **Federstahldraht Ø 4 mm** | **ca. 390** | 1 | Hauptfahrwerk, nach Biegeschablone `docs/fahrwerk_biegeschablone.pdf` |
| Federstahldraht Ø 3 mm | ca. 56 | 1 | Bugfahrwerk (gerade, in die Gabel geklebt) |
| Stahlstab Ø 3 mm | ca. 36 | 1 | Bugrad-Achse |
| Stahlstab Ø 4 mm | ca. 35 je | 2 | Radachsen = Enden des Fahrwerksdrahts (kein extra Teil) |
| Stellringe Ø 3 / Ø 4 mm | | je 4 | Räder sichern |

## Schrauben, Kleinteile

| Teil | Menge | Verwendung |
|---|---:|---|
| M3 × 20 Blechschraube (Linsenkopf) + Unterlegscheibe | 4 | Flügel auf Rumpf (Dome in W0, Gewinde in den Spantbalken) |
| M3 × 8 Zylinderschraube | 4 | Motor an Motorbock (Kreuz 16 oder 19 mm) |
| M3 × 10 Zylinderschraube + Mutter | 4 | Motorbock an Brandschott |
| M2,5 × 10 Blechschraube | 4 | Motorhaube am Brandschott |
| M2,5 × 10 Blechschraube | 4 | Spinnerkegel an Spinnerplatte |
| M3 × 12 Blechschraube | 2 | Hauptfahrwerks-Klemme |
| M3 × 4 Madenschraube | 1 | Lenkhebel auf dem Bugfahrwerksdraht |
| M2 × 8 Blechschraube | 10 | 5 Servos (je 2) |
| Gabelköpfe M2 / Rudermaschinen-Ersatz | 5 | Gestänge |
| Scharnierband / transparentes Gewebeband 25 mm | ca. 3 m | Ruderscharniere (beidseitig) |
| Epoxy 30 min, dünnflüssiger Sekundenkleber + Aktivator | | Verklebung (siehe Bauanleitung) |
| Klett / Akkugurt | | Akku, Regler, Empfänger |

## Optional

* Räder: statt gedruckter Naben/Reifen Schaumgummi- oder Gummiräder Ø 55 mm, Achse 4 mm (Haupt) / 3 mm (Bug).
* Trimmblei 20–60 g (Klett) im Bug, falls der Schwerpunkt nach dem Bau zu weit hinten liegt.
* Lack: Acryl-/Sprühfarbe für LW-PLA (Grundierung dünn auftragen!); Fenster nach den Gravuren abkleben.
