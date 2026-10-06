# Fernsteuerung: Servos, Anlenkung, Sender

Das Modell ist komplett für den Fernsteuerbetrieb vorbereitet: Servoschächte und -böden, Ruderhörner, Gestängekanäle,
Wartungsöffnung und alle Gestängelängen sind im CAD-Modell festgelegt und **kinematisch nachgerechnet** (Servo dreht,
Gestänge bleibt gleich lang, Ruder folgt). In der 3D-Ansicht (`docs/viewer`) bewegen sich Servohebel und Gestänge mit,
wenn du die Ruder-Regler verschiebst. „Rumpf durchsichtig“ zeigt die Anlenkungen im Rumpf.

## 1. Übersicht

| Funktion | Servo | Weg zum Ruder |
|---|---|---|
| Querruder (2×) | im Flügel `W2`, Abtrieb nach unten | kurzes Gestänge zum Horn an `Q1` |
| Landeklappen (2×) | im Flügel `W1`, Abtrieb nach unten | kurzes Gestänge zum Horn an `K1` |
| Höhenruder | Rumpf `F4` **links** | Bowdenzug im Kanal, tritt links am Heck schräg aus, Horn links unten an `H2`; die rechte Ruderhälfte hängt über den 2-mm-Verbinder mit |
| Seitenruder | Rumpf `F4` **rechts** | Stab im Kanal zum **Seitenruderhebel `S4`** im Heck; `S4` klemmt auf der **Ruderwelle** (Ø 2-mm-Federstahl in der Scharnierachse, im Ruder eingeklebt) |
| Bugrad | Rumpf `F2` **links** | kurzes Gestänge zum Lenkhebel `G6` auf dem Bugfahrwerksdraht |
| Gas | Regler in der Motorhaube | – |

Warum eine Ruderwelle beim Seitenruder? Das Seitenruder beginnt erst über der Höhenflosse. Ein außen liegendes Gestänge
müsste durch die Höhenflosse laufen. Die Welle in der Scharnierachse führt die Bewegung durch die Flossenwurzel in den
Rumpf; das Gestänge bleibt komplett innen. Die Welle läuft 4,9 mm hinter dem Verbinder der Höhenruder vorbei.

## 2. Anlenkungen (aus dem Modell berechnet)

Die Tabelle wird beim Generieren aus der Geometrie neu geschrieben (`python -m cessna.build`).
„Max. Ausschlag“ = Ruderausschlag bei ±35° Servoweg mit dem angegebenen Hebel-Loch. „Servoweg-Anteil“ = wie viel von
diesen ±35° du für den Sollausschlag brauchst. Stell die Endpunkte im Sender so ein, dass der Ausschlag an der
Hinterkante stimmt (Lineal/Ausschlagslehre an der breitesten Stelle des Ruders messen).

<!-- AUTO:anlenkung -->
| Funktion | Servo | Hebel-Loch | Ruderhebel | Gestänge (Z-Bügel → Loch) | max. Ausschlag (±35° Servo) | Soll | ≈ an der Hinterkante | Servoweg-Anteil für Soll |
|---|---|---:|---:|---|---:|---:|---:|---:|
| **Querruder rechts** | Flügel W2 rechts, y = +352 mm, Abtrieb unten | 8 mm | 21 mm | **66 mm**: Stahldraht Ø1,5 mm mit Z-Bügel am Servo und Gabelkopf am Horn | ± 16° | 15° | 14 mm | ≈ 90 % |
| **Landeklappe rechts** | Flügel W1 rechts, y = +150 mm, Abtrieb unten | 10 mm | 21 mm | **68 mm**: Stahldraht Ø1,5 mm mit Z-Bügel am Servo und Gabelkopf am Horn | 0 … 35° | 35° | 32 mm | 100 % (Endlage → Endlage) |
| **Querruder links** | Flügel W2 links, y = -352 mm, Abtrieb unten | 8 mm | 21 mm | **66 mm**: Stahldraht Ø1,5 mm mit Z-Bügel am Servo und Gabelkopf am Horn | ± 16° | 15° | 14 mm | ≈ 90 % |
| **Landeklappe links** | Flügel W1 links, y = -150 mm, Abtrieb unten | 10 mm | 21 mm | **68 mm**: Stahldraht Ø1,5 mm mit Z-Bügel am Servo und Gabelkopf am Horn | 0 … 35° | 35° | 32 mm | 100 % (Endlage → Endlage) |
| **Höhenruder** | Rumpf F4 links, x = 538 mm, Abtrieb oben | 10 mm | 17 mm | **312 + 56 mm**: Bowdenzug: Außenrohr Ø3/2 mm im Kanal bis ins Austrittsloch, Stahlseele Ø1,2 mm; Z-Bügel am Servo, Gabelkopf am Horn | ± 21° | 15° | 13 mm | ≈ 70 % |
| **Seitenruder** | Rumpf F4 rechts, x = 538 mm, Abtrieb oben | 10 mm | 12 mm | **351 mm**: CFK-Stab Ø2 mm im Kanal, Enden Stahldraht Ø1,5 mm (Z-Bügel am Servo, Gabelkopf am Hebel) | ± 28° | 20° | 25 mm | ≈ 70 % |
| **Bugrad** | Rumpf F2 links, x = 190 mm, Abtrieb oben (Welle vorn) | 14 mm | 14 mm | **61 mm**: Stahldraht Ø1,2 mm mit Z-Bügeln | ± 32° | 30° | – | ≈ 95 % |
<!-- /AUTO:anlenkung -->

* **Hebel-Loch:** Abstand des Lochs am Servohebel von der Servowelle. Nimm den Standard-Hebel und bohr bei Bedarf
  ein Loch Ø 1,6 mm im passenden Abstand.
* **Gestängelänge:** Maß von Lochmitte zu Lochmitte in Neutralstellung. Beim Höhenruder gilt der erste Wert bis zum
  Knick vor dem Austrittsloch, der zweite außen bis zum Horn. Draht 10–15 mm länger abschneiden, Z-Bügel biegen,
  am Gabelkopf fein einstellen.
* **Landeklappen:** Das Servo arbeitet von Endlage zu Endlage. In Ruhe (Klappe eingefahren) steht der Hebel **35° schräg**,
  bei voll ausgefahrener Klappe 35° zur anderen Seite. So ist der ganze Servoweg für 0–35° Klappe nutzbar.

## 3. Kanalbelegung

**Mindestens 6 Kanäle** (so wie in `docs/ZUKAUFTEILE.md` bestellt):

| Kanal | Funktion | Anschluss |
|---|---|---|
| 1 | Querruder | **Y-Kabel** für beide Querruderservos. Die Servos sind gleich eingebaut; beide Ruder laufen deshalb automatisch gegenläufig. |
| 2 | Höhenruder | direkt |
| 3 | Gas | Regler (BEC versorgt den Empfänger) |
| 4 | Seitenruder + Bugrad | **Y-Kabel**. Lenkt das Bugrad falsch herum: Servo-Reverser ins Bugrad-Kabel oder Variante 8 Kanäle. |
| 5 | Landeklappen | **Y-Kabel mit Servo-Reverser** auf einer Seite. Die Klappenservos müssen **gegenläufig** drehen, weil sie spiegelbildlich anlenken. |
| 6 | frei | z. B. Flugphasen-Schalter |

**Komfort mit 8 Kanälen (empfohlen):** Jedes Flügelservo bekommt einen eigenen Kanal (Quer rechts/links, Klappe rechts/links)
und das Bugrad einen eigenen Kanal. Der Sender übernimmt dann die Richtungen und die Mischer, kein Reverser nötig.
Dazu bekommst du Querruder-Differenzierung, Klappen-Trimmung und einen eigenen Lenkausschlag fürs Bugrad.

Die **Servokabel aus dem Flügel** laufen durch die Rippen zum Langloch in der Unterseite von `W0` und von dort in die Kabine.
Verlängerungen: Querruder ca. 300 mm, Klappen ca. 150 mm. Die Heckservos reichen mit 300-mm-Verlängerungen bis zum
Empfänger. Kabel im Rumpf mit Klebeband an den Spanten fixieren, nicht über die Gestängekanäle legen.

## 4. Einbau und Neutralstellung

1. **Servos vor dem Einbau zentrieren:** Empfänger, Regler und Akku anschließen, alle Trimmungen und Subtrims auf 0.
   Bei Klappen den Klappenschalter auf „eingefahren“ stellen.
2. **Hebel aufstecken:** Bei Quer, Höhe, Seite und Bugrad den Hebel **rechtwinklig zum Gestänge** aufstecken. Er
   zeigt dann genau in die Richtung, die die 3D-Ansicht zeigt (Flügel: nach außen, Heck: zur Rumpfmitte, Bug: nach vorn).
   Bei den **Klappen** steht der Hebel in Ruhe 35° schräg (siehe oben). Kleine Restfehler gleichst du mit Subtrim aus,
   maximal ±10 %.
3. **Gestänge:** Z-Bügel ins Hebel-Loch, Gabelkopf ins Horn, Länge am Gabelkopf so einstellen, dass das Ruder neutral steht
   (Klappe: eingefahren und bündig). Gabelköpfe mit einem Stück Silikonschlauch sichern.
4. **Seitenruder:** Die Ruderwelle (Ø 2 mm, 95 mm) wird beim Verkleben der Seitenruderschalen in die Halbrinne
   eingeklebt. In der Seitenflosse liegt sie **ohne Kleber** in der Lagerrinne. Den Hebel `S4` setzt du durch die
   **Wartungsöffnung links am Heck** auf das untere Wellenende. Er zeigt nach rechts. M3-Madenschraube durch die Öffnung
   anziehen, wenn das Ruder neutral steht. Den Gabelkopf des Seitenrudergestänges ebenfalls durch die Öffnung einklipsen.
5. **Höhenruder:** Das Außenrohr des Bowdenzugs (Ø 3/2 mm) läuft im Kanal von `F4` bis ins schräge Austrittsloch links am
   Heck. Dort bündig abschneiden und einkleben. Die Stahlseele läuft innen.
6. **Bugrad:** Lenkhebel `G6` so auf den Draht klemmen, dass das Rad bei neutralem Seitenruder geradeaus steht.
   Das Anlenkloch ist **senkrecht**, also Z-Bügel von oben einhängen.

## 5. Senderprogrammierung

| Funktion | Ausschlag | Dual Rate „niedrig“ | Expo |
|---|---:|---:|---:|
| Querruder | ± 15° | ± 10° | 30 % |
| Höhenruder | ± 15° | ± 10° | 25 % |
| Seitenruder | ± 20° | ± 15° | 20 % |
| Bugrad | ± 30° (bei Y-Kabel folgt es dem Seitenruder, dann ca. ± 25°) | – | – |
| Landeklappen | 0° / 15° (Start) / 35° (Landung) über 3-Stufen-Schalter, Servogeschwindigkeit 1–2 s | – | – |

* **Klappen → Höhe:** Beim Ausfahren der Klappen nimmt das Modell meist die Nase hoch. Mischer Klappe → Höhenruder mit
  2–3° **tief** bei 35° Klappe als Startwert, im Flug nachtrimmen.
* **Querruder-Differenzierung** (nur mit 2 Kanälen): 30–40 % (mehr nach oben als nach unten), das mindert das negative Wendemoment.
* **Gas:** Motor-Aus-Schalter (Throttle Cut) einrichten. Den Regler vor dem ersten Lauf auf den Gasweg einlernen.
* **Failsafe:** Gas auf **Motor aus**, Ruder neutral, Klappen eingefahren. Prüfen: Sender ausschalten, der Motor muss stoppen.
* **Drehrichtungen prüfen** (von hinten gesehen):
  * Knüppel rechts: rechtes Querruder hoch, linkes runter.
  * Knüppel gezogen: Höhenruder hoch.
  * Seite rechts: Ruderhinterkante nach rechts, Bugrad lenkt nach rechts.
  * Klappenschalter: beide Klappen nach unten.

## 6. Vor dem Erstflug

1. **Ruder-Check:** Alle Ruder laufen ohne Klemmen über den vollen Weg. Die Servos dürfen in den Endlagen nicht brummen,
   sonst den Endpunkt reduzieren.
2. **Spiel:** Ruder an der Hinterkante leicht bewegen; mehr als ca. 1 mm Spiel → Gabelkopf/Z-Bügel nacharbeiten.
3. **Reichweitentest** im Reichweitentest-Modus des Senders, einmal mit laufendem Motor.
4. **Schwerpunkt** nach `docs/BAUANLEITUNG.md` Abschnitt 7 einstellen. Die Lage von Akku und Empfänger ist im Modell
   berücksichtigt: Akku x ≈ 170–285 mm, Empfänger rechts in der Kabine.
5. **Empfängerantennen** 90° zueinander, weg von Regler, Motor- und Akkukabeln.
