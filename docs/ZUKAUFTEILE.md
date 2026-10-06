# Zukaufteile (Elektronik, Kohlefaser, Draht, Kleinteile)

Alle Angaben passen zu den Maßen der gedruckten Teile. Gewichte sind Richtwerte; sie gehen in die
Schwerpunktrechnung ein (`cessna/params.py`, Abschnitt `BOUGHT_PARTS`).

## Antrieb

| Teil | Empfehlung | Menge |
|---|---|---:|
| Außenläufer | Klasse 28xx, ca. 1000–1100 kV, Ø 28 mm, ca. 70–80 g, Befestigung 16/19-mm-Kreuz (M3) | 1 |
| Regler | 30 A (besser 40 A), BEC ≥ 3 A | 1 |
| Luftschraube | 10×6″ (z. B. APC 10×6 E), 2 Blatt; **Bodenfreiheit nur ca. 23 mm** (Wellenhöhe 150 mm) → auf rauem Gras besser 9×6″ (36 mm) | 1 |
| Propelleradapter | mit Mitnehmerscheibe, Welle passend zum Motor (3,17 / 4 / 5 mm) | 1 |
| Akku | LiPo 3S 2200 mAh, ≥ 25C, **max. 115 × 35 × 26 mm**, ca. 190 g | 1 |

Richtwerte (nicht geflogen!): 3S + 1000 kV + 10×6″ → ca. 22–26 A, 250–300 W, Standschub ca. 800–950 g,
Schub/Gewicht ≈ 0,5–0,6.

## Funkanlage

| Teil | Hinweis | Menge |
|---|---|---:|
| Empfänger | mind. 6 Kanäle (Quer, Höhe, Gas, Seite+Bugrad, Klappen); **8 Kanäle empfohlen** (jedes Flügelservo und das Bugrad einzeln). Kanalplan: `docs/FERNSTEUERUNG.md` | 1 |
| Servos 9 g | Mikroservos mit Metallgetriebe für Seite/Höhe empfohlen; **Abmessungen 23 × 12,4 × 22,8 mm, Flansch 32,5 mm** | 7 |
| Servo-Verlängerung | ca. 300 mm für Querruder und Heckservos, ca. 150 mm für die Klappen (→ Kabine) | 6 |
| Y-Kabel | Querruder (bei 6 Kanälen; die Ruder laufen ohne Reverser gegenläufig) | 1 |
| Y-Kabel + Servo-Reverser | Landeklappen (bei 6 Kanälen; die Klappenservos müssen gegenläufig drehen) | 1 |
| Y-Kabel | Bugradlenkung auf dem Seitenruder-Kanal (bei 6 Kanälen; ggf. Reverser für die Lenkrichtung) | 1 |

Servo-Verteilung: 2× Querruder und 2× Landeklappe (im Flügel, Abtrieb nach unten), 1× Höhenruder (Rumpf links, Heck),
1× Seitenruder (Rumpf rechts, Heck), 1× Bugradlenkung (Bug links).

## Kohlefaser / Draht (Zuschnitt in mm)

| Teil | Maß | Menge | Verwendung |
|---|---|---:|---|
| CFK-Rohr 10/8 mm | **660** | 2 | Flügelholm (links/rechts) |
| CFK-Stab Ø 7,8 mm (oder 8 mm abschleifen) | 200 | 1 | Flächenverbinder in der Mitte |
| CFK-Stab Ø 4 mm | 395 | 1 | Holm Höhenflosse (durch beide Hälften) |
| CFK-Stab Ø 2 mm | 370 | 1 | Höhenruder-Verbindung (durch beide Nasen) |
| Bowdenzug: Außenrohr Ø 3/2 mm + Stahlseele Ø 1,2 mm | Rohr ca. 330, Seele ca. 400 | 1 | Höhenruder (Kanal links, schräger Austritt am Heck) |
| CFK-Stab Ø 2 mm | ca. 320 | 1 | Seitenrudergestänge im Rumpf (Servo → Hebel `S4`), Enden: |
| Stahldraht Ø 1,5 mm | je ca. 40 | 2 | Enden des Seitenrudergestänges (Z-Bügel / Gabelkopf, mit Schrumpfschlauch und Sekundenkleber auf den CFK-Stab) |
| **Federstahldraht Ø 2 mm** | **95** | 1 | **Ruderwelle Seitenruder** (im Ruder eingeklebt, in der Flosse gelagert) |
| Stahldraht Ø 1,5 mm | je ca. 80 | 4 | Gestänge Querruder (66 mm) und Landeklappen (68 mm), Z-Bügel + Gabelkopf |
| Stahldraht Ø 1,2 mm | ca. 75 | 1 | Bugradlenkung (Servo → Lenkhebel, 61 mm, zwei Z-Bügel) |
| **Federstahldraht Ø 4 mm** | **ca. 390** | 1 | Hauptfahrwerk, nach Biegeschablone `docs/fahrwerk_biegeschablone.pdf` |
| Federstahldraht Ø 3 mm | ca. 56 | 1 | Bugfahrwerk (gerade, in die Gabel geklebt) |
| Stahlstab Ø 3 mm | ca. 44 | 1 | Bugrad-Achse (durch Gabel und Radverkleidung) |
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
| M3 × 4 Madenschraube | 2 | Lenkhebel `G6` auf dem Bugfahrwerksdraht, Seitenruderhebel `S4` auf der Ruderwelle |
| M2 × 8 Blechschraube | 14 | 7 Servos (je 2; im Flügel zusätzlich Heißkleber) |
| Gabelköpfe M2 + Gewindestück zum Einlöten/Kleben | 6 | Querruder, Klappen, Höhenruder, Seitenruder (Hebel `S4`) |
| Servohebel (Standard, Löcher 8–14 mm) | 7 | meist beim Servo dabei; fehlendes Loch Ø 1,6 mm nachbohren |
| Silikonschlauch 3 mm | 10 cm | Gabelköpfe sichern |
| Scharnierband / transparentes Gewebeband 25 mm | ca. 3 m | Ruderscharniere (beidseitig) |
| Epoxy 30 min, dünnflüssiger Sekundenkleber + Aktivator | | Verklebung (siehe Bauanleitung) |
| Klett / Akkugurt | | Akku, Regler, Empfänger |

## Optional

* Räder: statt gedruckter Naben/Reifen Schaumgummi- oder Gummiräder Ø 55 mm, Achse 4 mm (Haupt) / 3 mm (Bug).
* Trimmblei 20–60 g (Klett) im Bug, falls der Schwerpunkt nach dem Bau zu weit hinten liegt.
* Lack: Acryl-/Sprühfarbe für LW-PLA (Grundierung dünn auftragen!); Fenster nach den Gravuren abkleben.
