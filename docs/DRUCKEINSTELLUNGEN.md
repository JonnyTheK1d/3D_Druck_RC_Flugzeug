# Druckeinstellungen und Material

Alle STL-Dateien liegen in **Druckausrichtung** vor (kein Drehen nötig, Teile liegen auf z = 0). Größte Grundfläche:
205 × 205 mm (Flügelabschnitte, Leitwerk), höchstes Teil 93 mm (Motorbock) → passt auf Betten ab **220 × 220 mm**
(Ender 3, Prusa MK3/MK4, Bambu A1/P1 usw.). Jedes Teil hält mindestens 4 mm Rand ein.

## Materialübersicht

<!-- AUTO:material -->
| Material | Teile | Masse |
|---|---|---:|
| **LW-PLA** (schäumend) | Flügel, Querruder, Rumpf (6 Segmente), Leitwerk | ca. 937 g |
| **PETG** | Motorbock, Spinnerplatte, Fahrwerksklemmen, Bugfahrwerkslager, Gabel, Lenkhebel, Ruderhörner | ca. 71 g |
| **PLA** | Spinnerkegel, Radnaben, Streben | ca. 46 g |
| **TPU 95A** | 3 Reifen | ca. 35 g |
<!-- /AUTO:material -->

> Ohne LW-PLA geht es auch mit normalem PLA, dann wird das Flugzeug aber etwa **doppelt so schwer** (Flügel/Rumpf-Schalen
> wiegen dann ca. 2,0 kg) und fliegt nicht mehr sinnvoll. Für PLA müsste man die Wandstärken in `cessna/params.py`
> (`WALL_WING`, `WALL_FUSE`) auf ca. 0,6 mm verringern und neu generieren; dafür ist dieser Entwurf nicht optimiert.

## LW-PLA (Flügel, Rumpf, Leitwerk)

LW-PLA schäumt bei hoher Temperatur auf und hat dann nur ca. 0,5 g/cm³. Das Modell geht von **ausgeschäumten** Wandstärken aus:
Flügel 1,1 mm, Rumpf 1,2 mm, Leitwerk 0,85 mm (Parameter in `cessna/params.py` bzw. `tail.py`).

| Einstellung | Richtwert |
|---|---|
| Düse | 0,4 mm (0,6 mm geht auch, dann Linienbreite anpassen) |
| Temperatur | 230–250 °C (je nach Hersteller; höher = mehr schäumen = leichter) |
| Fluss (Flow) | **ca. 50–65 %**: so kalibrieren, dass ein Einzelwand-Würfel die Modellwandstärke ergibt (messen!) |
| Schichthöhe | 0,2–0,28 mm |
| Wände | so viele, dass die Wandstärke erreicht wird (z. B. 2 Wände bei 0,55 mm Linienbreite = 1,1 mm) |
| Füllung | **0 %** (Hohlbauweise); Boden/Deckel je 3 Schichten |
| „Dünne Wände erkennen“ / Gap-Fill | **an** (Rippen sind 1,2 mm, Leitwerk 0,85 mm dick) |
| Rückzug | aus oder sehr klein (LW-PLA fadet sonst stark) |
| Geschwindigkeit | 35–60 mm/s |
| Lüfter | 50–100 % |
| Stützen | **nur** unter der Flügelnase (optional, siehe unten); sonst keine; Brim 3–5 mm bei Flügelabschnitten |
| Z-Naht | hinten/zufällig, nicht an der Vorderkante |

**Erst wiegen:** Drucke zuerst `W0_Mittelstueck` (rechnerisch ca. 56 g) und wiege es. Weicht die Masse deutlich ab,
Flow/Temperatur nachstellen, bevor du alles druckst. Die Gesamtmasse bestimmt Schwerpunkt und Flugleistung.

## Ausrichtung je Bauteilgruppe (bereits in den STL)

* **Flügelabschnitte (W0–W3)** liegen auf der flachen Unterseite (Profil hinter 25 % Tiefe eben, um 3,1° gekippt).
  Nur die Nasenunterseite hebt sich vorn vom Bett ab (bei 10 % Tiefe 2,5 mm, an der Nasenspitze ca. 5 mm): dort ist ein
  schmaler Stützkeil „nur vom Druckbett aus" sinnvoll oder ein Brim; im Zweifel zuerst ein kurzes Probestück drucken.
  Die Hohlräume sind rundum geschlossen, Rippen verhindern das Durchhängen der Oberseite (Rippenabstand ca. 34 mm).
* **Querruder** liegen auf der Unterseite; die Rundnase ist massiv.
* **Leitwerksflächen** sind in **Ober- und Unterschale** geteilt (symmetrische Profile wären sonst nur mit Stützen
  druckbar). Jede Schale liegt mit der ebenen Schnittfläche auf dem Bett; ein Klebeflansch umläuft die Naht.
  Seitenflosse/-ruder: obere Schale = linke Seite, untere = rechte Seite.
* **Rumpf** besteht aus 6 Segmenten, jeweils links/rechts. Gedruckt wird **mit der Außenwand nach unten**, die offene
  Teilungsebene zeigt nach oben. Die Seitenwand ist eben und liegt bei jedem Segment (gegebenenfalls leicht gekippt, bis 8°)
  vollflächig auf dem Bett. Innenteile (Spanten, Servoböden, Domen) wachsen von der Wand nach oben. Überhänge treten nur
  an den Rundungen zur Dach-/Bauchlinie auf.
* **Motorbock** steht auf dem hinteren Flansch, **Spinnerkegel** mit offener Seite nach unten, **Streben** liegen
  diagonal (248 mm lang), **Reifen** liegen flach (TPU langsam, 15–25 mm/s, Rückzug aus).

## PETG / PLA / TPU

| Teil | Wände | Füllung | Hinweis |
|---|---:|---|---|
| Motorbock (PETG) | 3 | 30 % | Wärmebeständig, 245 °C/80 °C Bett |
| Fahrwerksteile (PETG) | 4 | 40 % | |
| Spinner/Streben/Naben (PLA) | 2–3 | 15–40 % | Spinnerkegel: 1,2 mm Wand, offene Seite nach unten |
| Reifen (TPU 95A) | 2 | 10 % | langsam drucken |

## Nacharbeit

* Brims/Fäden entfernen; Klebeflächen (Ränder der Schalen, Rippenränder) leicht anschleifen.
* Vor dem Kleben **alles trocken zusammenstecken** (Steckmuffen am Rumpf, Holmrohre durch die Flügelabschnitte).
* Spinner und Hauben leicht verspachteln/schleifen, bevor lackiert wird.
