"""Zentrale Maße des Modells (mm). Vorbild: Cessna 172, Maßstab 1:8.

Koordinaten im Zusammenbau: x nach hinten (x=0 = Haubenvorderkante, Spinner davor),
y nach rechts (Pilotensicht), z nach oben (z=0 = Boden bei stehendem Flieger).
"""
import numpy as np

SCALE = 8

# --------------------------------------------------------------------------- #
# Drucker / Material
# --------------------------------------------------------------------------- #
BED = (220.0, 220.0, 250.0)         # nutzbares Druckvolumen x, y, z
BED_MARGIN = 4.0                    # Rand, den ein Teil mindestens zum Bettrand hält
WALL_FUSE = 1.2                     # Außenhaut Rumpf (3 Perimeter @0,4 mm)
WALL_WING = 1.1                     # Außenhaut Flügel/Leitwerk an der Wurzel
RIB_T = 1.2                         # Rippendicke
CLEAR = 0.25                        # Passungsspiel für Steckverbindungen
DENSITY = {"LW-PLA": 0.55, "PLA": 1.24, "PETG": 1.27, "TPU": 1.20}   # g/cm³ im Bauteil (Schätzung)

# --------------------------------------------------------------------------- #
# Flügel (NACA 2412, gerade Vorderkante, Innenteil rechteckig, außen verjüngt)
# --------------------------------------------------------------------------- #
WING_AIRFOIL = "2412"
WING_FLAT_FROM = 0.25               # gerader Unterseitenboden ab 25 % Tiefe (druckfreundlich)
WING_SEMISPAN = 687.5               # 11,0 m / 8 / 2
WING_ROOT_CHORD = 200.0             # 1,63 m / 8 (gerundet)
WING_TIP_CHORD = 140.0              # 1,12 m / 8
WING_TAPER_START = 300.0            # y, ab hier verjüngt
WING_LE_X = 295.0                   # Flügelvorderkante im Rumpf (bestimmt Schwerpunktlage)
WING_INCIDENCE = 2.0                # Einstellwinkel (Grad, Nase hoch)
WING_Z_REF = 240.0                  # Höhe der Profilsehne an der Flügelnase im Zusammenbau
WING_CENTER_HALF = 80.0             # Mittelstück reicht von -80 bis +80
WING_PANEL_SPAN = (WING_SEMISPAN - WING_CENTER_HALF) / 3.0   # 202,5
SPAR_X = 55.0                       # Holmachse hinter der Vorderkante
SPAR_Z = 3.0                        # Holmachse über der Profilsehne
SPAR_OD, SPAR_ID = 10.0, 8.0        # CFK-Rohr 10/8 mm
SPAR_BORE = SPAR_OD + 0.4           # Bohrung
SPAR_SLEEVE_OD = 13.0               # gedruckte Holmhülse
JOINER_D = 8.0                      # CFK-Stab als Flächenverbinder (in Rohr 10/8)
AIL_Y0, AIL_Y1 = 330.0, 650.0       # Querruder von/bis
AIL_Y_SPLIT = WING_CENTER_HALF + 2 * WING_PANEL_SPAN   # 485: Plattenstoß -> Querruder in 2 Teilen
AIL_CHORD_FRAC = 0.28               # Querruderanteil an der Flügeltiefe
HINGE_GAP = 1.6
SERVO_9G = dict(L=23.2, W=12.4, H=22.8, flange_L=32.5, flange_T=2.4, flange_off=6.0)
AIL_SERVO_Y = 352.0                 # Servomitte (spannweitig)
AIL_SERVO_X = 80.0                  # Servomitte hinter der Vorderkante
FLAP_Y0, FLAP_Y1 = 84.0, 278.5      # Landeklappe (im Abschnitt W1, gleiche Scharnierlinie wie Querruder)
FLAP_SERVO_Y = 150.0                # Servomitte Klappenservo
FLAP_DOWN_MAX = 35.0                # maximaler Klappenausschlag nach unten (Grad)
WING_BOLT_X = (32.0, 150.0)         # Schraubenpositionen hinter der Flügelvorderkante
WING_BOLT_Y = 38.0                  # +/- y der Flügelschrauben (M3)
STRUT_Y = 282.5                     # Strebenansatz am Flügel (Plattenstoß)
STRUT_X = 78.0                      # hinter der Flügelvorderkante

# --------------------------------------------------------------------------- #
# Rumpf
# --------------------------------------------------------------------------- #
FUSE_LEN = 980.0
# Stützstellen: x, Breite, Unterkante z, Oberkante z, Eckenradius (Rundrechteck)
FUSE_TABLE = np.array([
    #  x      w     zb     zt     rc
    [  0.0, 118.0, 105.0, 195.0, 38.0],
    [ 40.0, 128.0,  97.0, 201.0, 34.0],
    [125.0, 140.0,  78.0, 198.0, 28.0],
    [200.0, 148.0,  70.0, 199.0, 22.0],
    [WING_LE_X - 3.0, 150.0,  66.0, 240.0,  9.0],
    [WING_LE_X + 205.0, 150.0,  66.0, 240.0,  9.0],
    [WING_LE_X + 255.0, 140.0,  75.0, 208.0, 18.0],
    [650.0,  98.0, 100.0, 190.0, 26.0],
    [800.0,  56.0, 132.0, 182.0, 18.0],
    [900.0,  38.0, 140.0, 178.0, 12.0],
    [980.0,  26.0, 145.0, 174.0,  9.0],
])
# Rumpfbreite: stückweise linear mit Knoten an den Segmentgrenzen -> jede Seitenwand ist eben und
# lässt sich beim Druck exakt flach auf das Bett legen (Spalte w der Tabelle oben dient nur als Vorbild)
FUSE_WIDTH_NODES = np.array([
    [  0.0, 118.0],
    [125.0, 140.0],
    [WING_LE_X + 15.0, 150.0],
    [WING_LE_X + 205.0, 150.0],
    [660.0,  98.0],
    [830.0,  48.0],
    [980.0,  26.0],
])
# Rumpfsegmente (x von, x bis, Name)
FUSE_SEGMENTS = [
    (0.0, 125.0, "F1_Motorhaube"),
    (125.0, WING_LE_X + 15.0, "F2_Bug"),
    (WING_LE_X + 15.0, WING_LE_X + 205.0, "F3_Kabine"),
    (WING_LE_X + 205.0, 660.0, "F4_Rumpfmitte"),
    (660.0, 830.0, "F5_Heckkonus"),
    (830.0, 980.0, "F6_Heck"),
]
LIP_LEN = 8.0                       # Steckmuffe zum nächsten Segment
FIREWALL_X = 125.0
FIREWALL_T = 4.0
CABIN_OPEN_X = (WING_LE_X, WING_LE_X + WING_ROOT_CHORD)   # hier bildet der Flügel das Dach
FRAME_X = (165.0, WING_LE_X, WING_LE_X + 110.0, WING_LE_X + 200.0, 580.0, 640.0, 700.0, 770.0, 860.0, 925.0)  # Spanten
FRAME_T = 1.2
FRAME_W = 6.0

DORSAL_X0 = 690.0                   # Rückenflosse beginnt hier auf dem Rumpfrücken
DORSAL_TOP = 212.0                  # und endet an der Flossenvorderkante in dieser Höhe
DORSAL_T = 5.0                      # Dicke

# --------------------------------------------------------------------------- #
# Antrieb
# --------------------------------------------------------------------------- #
MOTOR_D = 28.0                      # z. B. 2826/2830 Outrunner
MOTOR_LEN = 30.0
MOTOR_AXIS_Z = 150.0
PROP_DIA_IN = 10                    # 10x6" Luftschraube
SPINNER_D = 50.0
SPINNER_LEN = 45.0
MOTOR_SEAT_X = 32.0                 # Anlagefläche des Motors (Rückseite) am Motorbock

# --------------------------------------------------------------------------- #
# Leitwerk
# --------------------------------------------------------------------------- #
STAB_AIRFOIL = "0010"
STAB_HALFSPAN = 212.5               # 3,4 m / 8 / 2
STAB_ROOT_CHORD = 130.0
STAB_TIP_CHORD = 100.0
STAB_LE_X = 815.0
STAB_Z = 187.0                      # Höhe der Stab-Sehnenebene über Boden
STAB_CAP = 25.0                     # gerundete Spitze
ELEV_FRAC = 0.40
ELEV_END = 185.0                    # Höhenruder reicht bis y = 185
ELEV_Y0 = 6.5                       # Höhenruder beginnt neben der Seitenflosse
STAB_SPAR_X = 30.0                  # CFK-Stab Ø4 hinter der Stab-Vorderkante
FIN_AIRFOIL = "0009"
FIN_BASE_Z = 165.0                  # Fußebene des Seitenleitwerks (steckt im Heck)
FIN_HEIGHT = 175.0                  # bis Oberkante (z = 340 mm = 2,72 m / 8)
FIN_ROOT_LE = 770.0
FIN_ROOT_TE = 975.0
FIN_TIP_LE = 895.0
FIN_TIP_TE = 972.0
FIN_CAP = 22.0
RUDDER_HINGE = ((893.0, 0.0), (932.0, FIN_HEIGHT))   # (x, Höhe über Fußebene); Ruderwelle läuft 4,9 mm hinter dem Höhenruder-Verbinder
RUDDER_Y0, RUDDER_Y1 = 31.0, 150.0                    # Seitenruder von/bis (Höhe über Fußebene)
RUDDER_WIRE_TOP = RUDDER_Y0 + 45.0                    # Ruderwelle (Ø2-Draht) reicht bis hier ins Seitenruder
RUDDER_LEVER_R = 12.0                                 # Lochabstand am Seitenruderhebel (im Rumpfheck)
RUDDER_LEVER_Z = 149.0                                # Unterkante Seitenruderhebel (Zusammenbau)
ELEV_HORN_Y = 34.0                                    # Horn am Höhenruder (seitlich neben dem Heck)

# --------------------------------------------------------------------------- #
# Fahrwerk
# --------------------------------------------------------------------------- #
WHEEL_D = 55.0
WHEEL_W = 18.0
MAIN_GEAR_X = 382.0                 # Achse der Haupträder (hinter dem Schwerpunkt)
MAIN_GEAR_TRACK_HALF = 160.0        # Radmitte bei y = ±160
MAIN_WIRE_Z = 76.0                  # Höhe des Drahtes im Rumpf (Austritt durch die Seitenwand)
GEAR_WIRE_MAIN = 4.0                # Federstahl-Ø
GEAR_WIRE_NOSE = 3.0
NOSE_GEAR_X = 150.0
NOSE_WIRE_Z_TOP = 110.0             # oberes Ende der Bugfahrwerksachse (Steuerhebel)
NOSE_WHEEL_D = 50.0
PANT_HALF_W_MAIN = 14.5             # Radverkleidung: halbe Außenbreite Hauptrad
PANT_HALF_W_NOSE = 20.0             # Bugrad (Gabel liegt innen)
PANT_HALF_H = 33.0
PANT_BOTTOM = -13.0                 # Unterkante relativ zur Radmitte (Rad schaut unten heraus)
STRUT_Y_FUSE = 75.0                 # Strebenfuß an der Rumpfseite
STRUT_Z_FUSE = 110.0

# --------------------------------------------------------------------------- #
# Massenabschätzung der gekauften Teile (g) und Lage x (mm)
# --------------------------------------------------------------------------- #
BOUGHT_PARTS = {
    "Motor 2830 ~1000kV":      (75, 17),
    "Luftschraube 10x6":       (14, -8),
    "Regler 30 A":             (30, 85),
    "LiPo 3S 2200 mAh":        (190, 227),           # im Bugfach (115 mm lang) vor dem Flügel
    "Empfänger":               (8, 240),
    "Servo Querruder links":   (9, WING_LE_X + AIL_SERVO_X),
    "Servo Querruder rechts":  (9, WING_LE_X + AIL_SERVO_X),
    "Servo Klappe links":      (9, WING_LE_X + AIL_SERVO_X),
    "Servo Klappe rechts":     (9, WING_LE_X + AIL_SERVO_X),
    "Servo Höhe":              (9, 538),
    "Servo Seite":             (9, 538),
    "Servo Bugrad":            (9, 190),
    "CFK Holme + Verbinder":   (75, WING_LE_X + SPAR_X),
    "Fahrwerksdraht (Haupt+Bug)": (35, 330),
    "Kleber/Kabel/Anlenkung":  (55, 450),
}

# --------------------------------------------------------------------------- #
# Fensterkonturen (Gravur 0,8 x 0,4 mm als Lackiermaske); Polygone (x, z) bzw. (x, y)
# --------------------------------------------------------------------------- #
WINDOW_SIDE = [
    # Tür-/Frontfenster
    [(WING_LE_X - 68.0, 172.0), (WING_LE_X + 0.0, 228.0), (WING_LE_X + 62.0, 228.0), (WING_LE_X + 62.0, 172.0)],
    # hinteres Seitenfenster
    [(WING_LE_X + 69.0, 172.0), (WING_LE_X + 69.0, 228.0), (WING_LE_X + 175.0, 228.0),
     (WING_LE_X + 218.0, 205.0), (WING_LE_X + 208.0, 172.0)],
]
WINDOW_TOP = [
    # Windschutzscheibe (Draufsicht)
    [(WING_LE_X - 74.0, -50.0), (WING_LE_X - 74.0, 50.0), (WING_LE_X - 8.0, 46.0), (WING_LE_X - 8.0, -46.0)],
    # Heckscheibe
    [(WING_LE_X + 212.0, -40.0), (WING_LE_X + 212.0, 40.0), (WING_LE_X + 250.0, 34.0), (WING_LE_X + 250.0, -34.0)],
]
