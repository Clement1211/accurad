# Product Requirements Document (PRD)
## API AccuRad PRD — Bibliothèque Open-Source de Communication

| Champ | Valeur |
|---|---|
| **Version** | 1.2 |
| **Date** | 2026-03-19 |
| **Statut** | Validated (hardware-tested) |
| **Appareil cible** | AccuRad PRD (Mirion Technologies) |
| **Document de référence** | DOC012721EN-E, Section 10.1 — Communication Protocol |

---

## 1. Executive Summary & Objectifs

### 1.1 Vision

Créer une bibliothèque Python open-source, propre et bien documentée, permettant à tout développeur de communiquer avec le détecteur de radiation personnel AccuRad PRD de Mirion Technologies via USB ou Bluetooth. Aucune API ouverte n'existe actuellement pour ce matériel ; cette bibliothèque comblera ce manque.

### 1.2 Objectifs stratégiques

1. **Démocratiser l'accès aux données** — Permettre aux chercheurs, techniciens en radioprotection et développeurs d'intégrer les mesures de l'AccuRad PRD dans leurs propres outils (dashboards, systèmes SCADA, logging, alertes personnalisées).
2. **Fiabilité industrielle** — Implémenter un parsing strict du protocole binaire avec validation CRC16, gestion des timeouts et interprétation complète des états système.
3. **Open-source & communauté** — Publier sous licence MIT sur GitHub/PyPI avec une documentation exemplaire pour encourager les contributions.

### 1.3 Cas d'usage cibles

| Cas d'usage | Description |
|---|---|
| **Monitoring en temps réel** | Lecture continue des mesures (dose rate, count rate, dose cumulée) avec polling configurable |
| **Logging & archivage** | Enregistrement horodaté des données dans un fichier CSV/JSON/base de données |
| **Intégration système** | Alimentation d'un dashboard web, d'un système d'alerte ou d'une plateforme IoT |
| **Scripting & automatisation** | Scripts de vérification d'état de l'appareil (batterie, calibration, erreurs matérielles) |
| **Recherche & analyse** | Collecte de données brutes pour analyse scientifique post-mission |

---

## 2. Périmètre (Scope) & Fonctionnalités Clés

### 2.1 In Scope (v1.0)

#### 2.1.1 Couche transport — Connexion à l'appareil

| Méthode | Signature | Description |
|---|---|---|
| `connect_usb()` | `connect_usb(port: str, baudrate: int = 921600) -> AccuRadConnection` | Connexion via USB Virtual COM Port |
| `connect_bluetooth()` | `connect_bluetooth(address: str, timeout: float = 5.0) -> AccuRadConnection` | Connexion via Bluetooth BLE (UART Service) |
| `disconnect()` | `disconnect() -> None` | Fermeture propre de la connexion |
| `is_connected` | `@property -> bool` | État de la connexion |

#### 2.1.2 Couche protocole — Requêtes et réponses

| Méthode | Signature | Description |
|---|---|---|
| `get_device_info()` | `get_device_info() -> DeviceInfo` | Envoie la séquence ID=0 et parse la réponse complète |
| `get_measurements()` | `get_measurements() -> DeviceData` | Envoie la séquence ID=1 et parse la réponse complète |

#### 2.1.3 Couche données — Modèles de données typés

Les structures retournées par l'API sont des **dataclasses Python immutables** mappant exactement les structures C du protocole :

```
DeviceInfo
├── manufacturer: str          # 16 bytes, zero-terminated
├── part_number: str           # 16 bytes, zero-terminated
├── serial_number: str         # 16 bytes, zero-terminated
├── firmware_number: int       # uint32
├── firmware_version: str      # "AA.BB.CC.DD"
├── datetime: datetime         # Python datetime from packed bitfields
└── timezone: TimezoneInfo     # Index + label UTC

DeviceData
├── merged: MergedMeasurement
│   ├── state: MergedState
│   │   ├── origin: MeasurementOrigin  # Enum: UNKNOWN, LOW_RANGE, HIGH_RANGE, BOTH
│   │   ├── prd_15kev_incoherence: bool
│   │   ├── overload: bool
│   │   └── initialized: bool
│   ├── dose_rate_usv_h: float         # µSv/h
│   ├── count_rate_cps: float          # coups par seconde
│   ├── background_dose_rate_usv_h: float
│   ├── background_count_rate_cps: float
│   └── level: float                   # 0-9 (indicateur d'affichage)
├── dose: DoseData
│   ├── datetime: datetime
│   ├── dose_usv: float                # µSv cumulé depuis startup/reset
│   └── duration_s: float              # durée d'intégration en secondes
├── battery: BatteryData
│   ├── state: BatteryState
│   │   ├── level_too_low: bool
│   │   ├── level_critical: bool
│   │   ├── usb_connected: bool
│   │   ├── failure: bool
│   │   └── initialized: bool
│   └── level_percent: int | None       # 0-100, ou None si USB connecté (valeur non fiable)
├── system_state: SystemState          # 32 flags individuels (voir §2.1.4)
└── measurement_id: int                # Compteur incrémenté toutes les 250ms
```

#### 2.1.4 Parsing des System States — Méthodes utilitaires

Le `SystemState` (mot de 32 bits) expose chaque flag comme attribut booléen :

| Attribut | Bit | Description |
|---|---|---|
| `counting_fault` | 0 | Défaut de comptage SED PRD et/ou SED 15 keV |
| `temp_sensor_fault` | 1 | Défaillance capteur de température |
| `temp_out_of_range` | 2 | Température hors plage de fonctionnement |
| `check_datetime` | 3 | Date/heure non à jour |
| `accumulation_enabled` | 4 | Accumulation spectrale activée |
| `accumulation_in_progress` | 5 | Accumulation en cours |
| `acknowledged` | 6 | Appareil en état acquitté |
| `low_alarm` | 7 | Alarme basse activée |
| `high_alarm` | 8 | Alarme haute activée |
| `danger` | 9 | Alarme danger activée |
| `dose_alarm` | 10 | Alarme dose activée |
| `dose_danger` | 11 | Alarme dose danger activée |
| `low_power` | 12 | Mode basse consommation |
| `search_mode` | 13 | Mode recherche actif |
| `calibration_expired` | 15 | Calibration à vérifier |
| `vbs` | 16 | VBS déclenché (variation de bruit de fond) |
| `magnetometer_fault` | 17 | Magnétomètre en panne |
| `acc_gyrometer_fault` | 18 | Accéléromètre/Gyroscope en panne |
| `e2p_fault` | 19 | Mémoire E2PROM en défaut |
| `flash_fault` | 20 | Mémoire Flash en défaut |
| `audio_fault` | 21 | Défaillance audio |
| `ble_fault` | 22 | Défaillance Bluetooth |
| `discreet` | 23 | Mode discret activé |
| `alarm_thresholds_not_consistent` | 24 | Seuils d'alarme incohérents |
| `initialized` | 30 | Séquence d'initialisation terminée |
| `remote_ctrl` | 31 | Contrôle à distance activé |

Méthodes utilitaires :

| Méthode | Description |
|---|---|
| `has_alarms() -> bool` | `True` si au moins une alarme est active (bits 7-11) |
| `has_faults() -> bool` | `True` si au moins un défaut matériel est détecté |
| `get_active_alarms() -> list[str]` | Liste des noms des alarmes actives |
| `get_active_faults() -> list[str]` | Liste des noms des défauts actifs |
| `is_ready() -> bool` | `True` si initialized et aucun défaut critique |

#### 2.1.5 Monitoring continu (haut niveau)

| Méthode | Signature | Description |
|---|---|---|
| `stream_measurements()` | `stream_measurements(interval: float = 0.5, callback: Callable = None) -> Iterator[DeviceData]` | Générateur de mesures en continu avec gestion du keep-alive Bluetooth |
| `start_logging()` | `start_logging(path: str, format: str = "csv", interval: float = 1.0) -> None` | Démarre l'enregistrement des données dans un fichier |
| `stop_logging()` | `stop_logging() -> None` | Arrête l'enregistrement |

### 2.2 Out of Scope (v1.0)

- **Écriture de configuration** sur l'appareil (le protocole ne documente intentionnellement pas les séquences de configuration pour éviter les corruptions — cf. §10.1.2)
- **Interface graphique (GUI)**
- **Support des fichiers .n42 / .xlsx** (export fait par l'AccuRad App, pas par cette API)
- **Gestion multi-appareils simultanés** (possible mais non garanti en v1.0)

---

## 3. Architecture & Stack Technique Recommandée

### 3.1 Langage : Python 3.10+

**Justification :**
- Écosystème riche pour la communication série et Bluetooth
- Adoption massive dans la communauté scientifique et radioprotection
- `struct` natif pour le parsing binaire little-endian
- Type hints et dataclasses pour une API propre et auto-documentée
- Facilité de publication sur PyPI

### 3.2 Bibliothèques recommandées

| Dépendance | Version min. | Rôle |
|---|---|---|
| `pyserial` | 3.5 | Communication USB Virtual COM Port |
| `bleak` | 0.21+ | Communication Bluetooth Low Energy (BLE) cross-platform |
| `struct` (stdlib) | — | Décodage des trames binaires (little-endian floats, uint32, bitfields) |
| `dataclasses` (stdlib) | — | Modèles de données immutables |
| `enum` (stdlib) | — | Enums pour MeasurementOrigin, TimezoneIndex, etc. |
| `logging` (stdlib) | — | Logging structuré configurable |

**Dépendances de développement :**

| Outil | Rôle |
|---|---|
| `pytest` | Tests unitaires et d'intégration |
| `pytest-mock` | Mocking des ports série/BLE pour tests sans matériel |
| `ruff` | Linting et formatting |
| `mypy` | Vérification de types statique |
| `mkdocs` + `mkdocstrings` | Documentation auto-générée |
| `hatch` / `setuptools` | Build et packaging PyPI |

### 3.3 Architecture des modules

```
accurad/
├── __init__.py              # Exports publics : connect_usb, connect_bluetooth, AccuRad
├── connection/
│   ├── __init__.py
│   ├── base.py              # AccuRadConnection (classe abstraite)
│   ├── serial.py            # SerialConnection (USB COM Port via pyserial)
│   └── bluetooth.py         # BluetoothConnection (BLE via bleak)
├── protocol/
│   ├── __init__.py
│   ├── frame.py             # Parsing de trame : start marker, LEN, ID, payload, CRC
│   ├── crc.py               # Implémentation CRC16 (polynôme 0xAC5E)
│   ├── requests.py          # Séquences de requêtes brutes (ID=0, ID=1)
│   └── parsers.py           # Décodage des payloads en dataclasses
├── models/
│   ├── __init__.py
│   ├── device_info.py       # DeviceInfo dataclass
│   ├── device_data.py       # DeviceData, MergedMeasurement, DoseData, BatteryData
│   ├── system_state.py      # SystemState avec méthodes utilitaires
│   ├── datetime.py          # Parsing des bitfields Date_t et Time_t
│   └── enums.py             # MeasurementOrigin, TimezoneIndex, etc.
├── client.py                # AccuRad — classe principale haut niveau
├── streaming.py             # stream_measurements(), logging continu
├── exceptions.py            # Hiérarchie d'exceptions personnalisées
└── _constants.py            # Constantes : START_MARKER, POLYNOM16, UUIDs BLE, timeouts
```

### 3.4 Diagramme de flux d'une requête

```
Application
    │
    ▼
AccuRad.get_measurements()
    │
    ├─► requests.py : bytes DEVICE_DATA_REQUEST = b'\x7E\x04\x00\x11\xA7\x1E\x43\xE7'
    │
    ├─► connection.send(DEVICE_DATA_REQUEST)
    │
    ├─► connection.receive() → raw bytes
    │
    ├─► frame.py : validate_frame(raw)
    │   ├─ Vérifier start marker "#!AccuRad!#"
    │   ├─ Extraire LEN (2 bytes LE) — LEN inclut ID + Payload + CRC
    │   ├─ Extraire ID (2 bytes LE)
    │   ├─ Extraire payload (LEN - 4 bytes : -2 ID, -2 CRC)
    │   ├─ Extraire CRC reçu (2 derniers bytes LE)
    │   └─ crc.py : crc16(payload) == CRC reçu ?
    │
    ├─► parsers.py : parse_device_data(payload) → DeviceData
    │
    └─► return DeviceData
```

---

## 4. Sécurité, Fiabilité & Gestion des Erreurs

### 4.1 Validation de l'intégrité des données — CRC16

L'intégrité de chaque trame est vérifiée via un CRC16 avec polynôme custom `0xAC5E`.

**Algorithme (traduit fidèlement du C de la documentation) :**

```python
POLYNOM16 = 0xAC5E

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        if crc == 0:
            crc = 1
        for _ in range(8):
            parity = crc & 1
            crc >>= 1
            if parity:
                crc ^= POLYNOM16
    return crc
```

**Règles :**
- Le CRC est calculé sur **ID + payload** (= tout entre LEN et CRC dans la trame, noté « XXXXX » dans le manuel)
- Si le CRC calculé ne correspond pas au CRC reçu → lever `CRCMismatchError`
- Aucune donnée n'est jamais retournée à l'utilisateur si le CRC échoue
- **Note :** Le manuel indique « CRC computed on payload » ce qui est ambigu. L'analyse des trames d'exemple prouve que le CRC couvre ID + payload (vérifié : CRC(ID+Payload) = 0x5B02 pour device info). La valeur CRC de device data dans le manuel (0xA94F / 0x5B02) est une erreur de documentation ; la valeur correcte est 0x599E.

### 4.2 Gestion des timeouts

#### 4.2.1 Timeouts Bluetooth (spécifications du manuel §10.1.3.3.3)

| Timeout | Valeur | Comportement |
|---|---|---|
| **Post-connexion** | 1 seconde | Après établissement de la connexion BLE, attendre 1s avant d'envoyer toute requête, sinon la communication peut échouer |
| **Keep-alive** | 2.5 secondes max | L'AccuRad doit recevoir un message valide au moins toutes les 2.5s, sinon il passe en mode discoverable (déconnexion) |
| **Discoverable** | 60 secondes | Après perte de connexion ou scan NFC, l'appareil est visible pendant 60s puis coupe le Bluetooth (sauf en mode "opened") |

**Implémentation :**
- En mode `stream_measurements()`, un heartbeat automatique (requête ID=1) est envoyé toutes les 2 secondes maximum pour maintenir la connexion BLE
- Un timer interne avertit si le délai entre deux communications approche 2.5s
- Après connexion BLE, un `await asyncio.sleep(1.0)` est inséré automatiquement

#### 4.2.2 Timeouts généraux

| Paramètre | Valeur par défaut | Configurable |
|---|---|---|
| `read_timeout` | 3.0s | Oui |
| `write_timeout` | 1.0s | Oui |
| `connect_timeout` | 15.0s (BLE) / 2.0s (USB) | Oui |

### 4.3 Hiérarchie des exceptions

```
AccuRadError (base)
├── ConnectionError
│   ├── USBConnectionError
│   ├── BluetoothConnectionError
│   └── ConnectionTimeoutError
├── ProtocolError
│   ├── InvalidFrameError        # Start marker absent ou trame malformée
│   ├── CRCMismatchError         # CRC calculé ≠ CRC reçu
│   ├── UnexpectedFrameIDError   # ID de trame inattendu
│   └── IncompleteFrameError     # Trame tronquée (LEN ne correspond pas)
├── DeviceError
│   ├── DeviceNotInitializedError  # Flag initialized = 0
│   └── DeviceNotReadyError        # Défauts critiques détectés
└── TimeoutError                   # Timeout de lecture/écriture
```

### 4.4 Parsing des états matériels

L'API **ne masque aucune information** mais fournit des niveaux d'interprétation :

**Niveau 1 — Brut :** Accès direct à chaque flag booléen via `system_state.low_alarm`, etc.

**Niveau 2 — Catégorisé :**
```python
# Alarmes radiologiques
system_state.has_alarms()        # low_alarm OR high_alarm OR danger OR dose_alarm OR dose_danger
system_state.get_active_alarms() # ["low_alarm", "danger"]

# Défauts matériels
system_state.has_faults()        # counting_fault OR temp_sensor_fault OR ... OR ble_fault
system_state.get_active_faults() # ["temp_out_of_range", "flash_fault"]

# État batterie
battery.is_critical()            # level_critical flag
battery.is_usb_powered()         # usb_connected flag
```

**Niveau 3 — Opérationnel :**
```python
system_state.is_ready()          # initialized AND NOT has_faults()
```

### 4.5 Robustesse de la connexion

- **Reconnexion automatique** : Optionnelle, désactivée par défaut. Si activée, l'API tente une reconnexion après perte de connexion BLE (dans la fenêtre de 60s discoverable)
- **Buffer flush** : À chaque nouvelle connexion, le buffer de réception est vidé pour éviter de parser des données résiduelles
- **Validation du start marker** : Chaque réponse est scannée pour le pattern `#!AccuRad!#` (11 bytes : `0x23 0x21 0x41 0x63 0x63 0x75 0x52 0x61 0x64 0x21 0x23`). Les bytes précédant ce marker sont ignorés (synchronisation)

---

## 5. Dépendances et Prérequis Système

### 5.1 Pour l'utilisateur de l'API

| Prérequis | Détail |
|---|---|
| **Python** | 3.10 ou supérieur |
| **OS** | Windows 10+, Linux (Ubuntu 20.04+), macOS 12+ |
| **Matériel** | AccuRad PRD avec firmware V1.1+ |
| **USB** | Câble USB-C, driver COM port installé (automatique sur la plupart des OS) |
| **Bluetooth** | Adaptateur BLE 4.0+ (intégré ou USB). L'AccuRad doit avoir le Bluetooth activé et être en mode discoverable ou "opened" |

### 5.2 Installation

```bash
# Installation standard (USB uniquement)
pip install accurad

# Installation avec support Bluetooth
pip install accurad[bluetooth]

# Installation développeur
pip install accurad[dev]
```

### 5.3 Matrice de compatibilité Bluetooth

| OS | Backend BLE | Notes |
|---|---|---|
| Windows 10+ | WinRT (via bleak) | Fonctionne nativement |
| Linux | BlueZ 5.43+ (via bleak) | `sudo` peut être requis pour le scan BLE |
| macOS 12+ | CoreBluetooth (via bleak) | Permissions Bluetooth à accorder dans Préférences Système |

### 5.4 Configuration minimale recommandée

```python
from accurad import AccuRad

# USB — le plus simple
device = AccuRad.connect_usb("COM3")  # Windows
device = AccuRad.connect_usb("/dev/ttyUSB0")  # Linux
device = AccuRad.connect_usb("/dev/cu.usbmodem1234")  # macOS

# Bluetooth
device = AccuRad.connect_bluetooth("XX:XX:XX:XX:XX:XX")

# Lecture
info = device.get_device_info()
print(f"S/N: {info.serial_number}, FW: {info.firmware_version}")

data = device.get_measurements()
print(f"Dose rate: {data.merged.dose_rate_usv_h:.4f} µSv/h")
print(f"Battery: {data.battery.level_percent}%")

if data.system_state.has_alarms():
    print(f"ALARMES ACTIVES: {data.system_state.get_active_alarms()}")

device.disconnect()
```

---

## 6. Plan d'Implémentation (Milestones)

### Milestone 0 — Setup projet ✅

- [x] Repository Git, structure de dossiers, `pyproject.toml`, `ruff`, `mypy`, `pytest`
- [x] CI GitHub Actions (multi-OS, multi-Python)
- [x] `README.md`, `.gitignore`, `CLAUDE.md`

### Milestone 1 — Couche protocole brut ✅

- [x] `_constants.py`, `crc.py`, `frame.py`, `models/datetime.py`, `models/enums.py`, `exceptions.py`
- [x] CRC16 validé contre trames du manuel (0x5B02 device info, 0x599E device data)
- [x] **Découverte :** CRC porte sur ID + Payload (pas juste payload). Erreur doc manuelle corrigée.
- [x] 33 tests unitaires passent

### Milestone 2 — Parsers de payload ✅

- [x] Tous les modèles : `DeviceInfo`, `DeviceData`, `MergedMeasurement`, `DoseData`, `BatteryData`, `SystemState`
- [x] Parsers validés champ par champ contre les exemples du manuel
- [x] Règle métier batterie USB implémentée

### Milestone 3 — Couche transport USB ✅ (hardware-tested)

- [x] `SerialConnection` avec synchronisation start marker, timeouts, buffer flush
- [x] `AccuRad` client avec `connect_usb()`, `get_device_info()`, `get_measurements()`
- [x] Testé sur AccuRad réel (S/N 003CEE, FW 1.6.0.0) — USB COM3

### Milestone 4 — Couche transport Bluetooth ✅ (hardware-tested)

- [x] `BluetoothConnection` via bleak avec event loop threadé (fix Windows WinRT)
- [x] Scan-first obligatoire (Windows ne trouve pas le device par adresse seule)
- [x] Délai post-connexion 1s, keep-alive, timeout 15s (GATT discovery lent sur Windows)
- [x] Testé sur AccuRad réel via BLE (FC:0F:E7:A7:D8:9F)

### Milestone 5 — Streaming & haut niveau ✅ (hardware-tested)

- [x] `stream_measurements()` — générateur sync avec keep-alive naturel (chaque poll reset le timer BLE)
- [x] `start_logging()` / `stop_logging()` — CSV et JSON lines, thread background
- [x] Context manager sur `AccuRad` et `AccuRadConnection`
- [x] Testé USB + BLE streaming, CSV logging vérifié

### Milestone 6 — Documentation & packaging (en cours)

- [x] Docstrings Google style sur toutes les méthodes publiques
- [x] 4 exemples : `basic_usb.py`, `basic_bluetooth.py`, `continuous_monitoring.py`, `alarm_watcher.py`
- [x] `demo/live_dashboard.py` — dashboard terminal temps réel
- [ ] Documentation MkDocs
- [ ] Publication PyPI
- [ ] `CONTRIBUTING.md` et `LICENSE` (MIT)

---

## Annexe 0 — Notes d'implémentation critiques (LIRE EN PREMIER)

> Ces points sont les pièges les plus probables lors de l'implémentation. Chaque développeur doit lire cette section avant d'écrire la moindre ligne de code.

### N1. Le champ LEN inclut l'ID (CORRIGÉ en v1.1)

Le texte du manuel dit « length of XXXXX + CRC » ce qui est ambigu. **L'analyse des trames d'exemple prouve que LEN = ID(2) + Payload(N) + CRC(2) = N + 4.**

| Trame | Payload réel | LEN attendu | LEN dans le manuel |
|---|---|---|---|
| Device Info (ID=0) | 65 bytes | 65 + 2 + 2 = 69 | 0x0045 = 69 ✓ |
| Device Data (ID=1) | 47 bytes | 47 + 2 + 2 = 51 | 0x0033 = 51 ✓ |

**Impact code :** `payload_size = LEN - 4` (pas LEN - 2). Erreur = désynchronisation + échec CRC systématique.

### N2. Bitfields C ≠ struct Python

Python `struct` ne supporte pas les champs de bits. Pour `Time_t` et `Date_t`, il faut :
1. `struct.unpack("<I", data)` → uint32 little-endian
2. Masques binaires pour isoler chaque champ

Exemple vérifié : `0x066841EE` → Hours=14, Minutes=15, Seconds=8, Ms=820, Daylight=0

### N3. Battery level_percent non fiable en USB

Quand `BatteryState.usb_connected == True`, le hardware rapporte un `level_percent` qui ne reflète pas la charge réelle. Le parser doit forcer cette valeur à `None` pour éviter que l'utilisateur final ne base des décisions sur une donnée erronée.

### N4. Bluetooth : délai post-connexion de 1s obligatoire

Après `BleakClient.connect()`, il faut **impérativement** attendre 1 seconde complète avant d'envoyer la première requête. Sans ce délai, la communication échoue de manière intermittente et non-reproductible — ce qui en fait un bug particulièrement difficile à diagnostiquer.

### N5. Bluetooth : keep-alive toutes les 2.5s

L'AccuRad coupe la connexion BLE si aucun message valide n'est reçu pendant 2.5s. Le timer de heartbeat doit être intégré dans la couche transport Bluetooth, pas dans le code utilisateur.

### N6. CRC calculé sur ID + Payload (CORRIGÉ en v1.2)

Le manuel dit « CRC computed on XXXXX » où XXXXX représente tout entre LEN et CRC dans la trame, soit **ID + Payload**. L'implémentation initiale supposait « payload only » — c'était faux. Vérifié : `CRC16(ID + Payload) = 0x5B02` correspond exactement à la trame device info du manuel. La valeur CRC device data dans le manuel (0xA94F dans les bytes, décodé comme 0x5B02) est une erreur de copier-coller ; la valeur correcte est **0x599E**.

### N7. Bluetooth Windows : scan-first obligatoire (ajouté en v1.2)

Sur Windows (backend WinRT), `BleakClient(address)` ne trouve pas l'appareil par adresse MAC seule. Il faut d'abord scanner avec `BleakScanner.find_device_by_address()` puis passer le `BLEDevice` résultant à `BleakClient`. De plus, le timeout de connexion par défaut doit être **15s** (pas 5s) car la découverte GATT est lente sur Windows.

---

## Annexe A — Référence rapide du protocole

### Séquences de requêtes (à envoyer telles quelles)

| Requête | ID | Séquence hexadécimale |
|---|---|---|
| Device Information | 0 | `7E 04 00 10 A7 07 46 E7` |
| Device Measurements | 1 | `7E 04 00 11 A7 1E 43 E7` |

### Format de trame réponse

```
┌─────────────┬──────────┬──────────┬─────────────────┬──────────┐
│ #!AccuRad!# │  LEN     │   ID     │    Payload      │  CRC16   │
│  11 bytes   │ 2 bytes  │ 2 bytes  │   N bytes       │ 2 bytes  │
│  (ASCII)    │  (LE)    │  (LE)    │                 │  (LE)    │
└─────────────┴──────────┴──────────┴─────────────────┴──────────┘
                          ◄──────── LEN = N + 4 ────────►
```

> **ATTENTION — Calcul de LEN :** Le champ LEN inclut l'ID (2 bytes) + le Payload (N bytes) + le CRC (2 bytes), soit **LEN = N + 4**. Ce n'est PAS uniquement Payload + CRC.
>
> **Preuve par les trames du manuel :**
> - Device Info (ID=0) : Payload = 65 bytes → LEN = 65 + 2 + 2 = **69 = 0x0045** ✓
> - Device Data (ID=1) : Payload = 47 bytes → LEN = 47 + 2 + 2 = **51 = 0x0033** ✓

- **LEN** = ID (2 bytes) + Payload (N bytes) + CRC (2 bytes) = **N + 4**
- **Payload size** = LEN - 4 (pour extraire le payload brut depuis LEN)
- **CRC16** calculé sur **ID + payload** (polynôme 0xAC5E) — voir Annexe 0, N6
- Byte order : little-endian pour les mots multi-octets
- Bit order : MSB first dans chaque byte

### UUIDs Bluetooth BLE

| Caractéristique | UUID |
|---|---|
| UART Service | `49535343-FE7D-4AE5-8FA9-9FAFD205E455` |
| UART TX (Notify/Write) | `49535343-1E4D-4BD9-BA61-23C647249616` |

---

## Annexe B — Tailles des payloads

| Frame ID | Payload (N) | LEN = N + 4 | Taille totale trame (11 + 2 + LEN) |
|---|---|---|---|
| 0 (Device Info) | 65 bytes (16+16+16+4+4+8+1) | 69 (0x0045) | 11 + 2 + 69 = **82 bytes** |
| 1 (Device Data) | 47 bytes (21+16+2+4+4) | 51 (0x0033) | 11 + 2 + 51 = **64 bytes** |

> **Décomposition de la trame complète :** Start Marker (11) + LEN (2) + ID (2) + Payload (N) + CRC (2).
> Le champ LEN couvre les bytes après lui-même : ID (2) + Payload (N) + CRC (2) = N + 4.

### Détail payload ID=0 (Device Information)

| Offset | Taille | Champ |
|---|---|---|
| 0 | 16 | Manufacturer (string, zero-terminated) |
| 16 | 16 | Part Number (string, zero-terminated) |
| 32 | 16 | Serial Number (string, zero-terminated) |
| 48 | 4 | Firmware Number (uint32 LE) |
| 52 | 4 | Firmware Version (uint32 LE → AA.BB.CC.DD) |
| 56 | 8 | DateTime (Time_t 4B + Date_t 4B) |
| 64 | 1 | Timezone Index (uint8) |

### Détail payload ID=1 (Device Data)

| Offset | Taille | Champ |
|---|---|---|
| 0 | 1 | Merged State (uint8, bitfield) |
| 1 | 4 | Dose Rate µSv/h (float32 LE) |
| 5 | 4 | Count Rate cps (float32 LE) |
| 9 | 4 | Background Dose Rate µSv/h (float32 LE) |
| 13 | 4 | Background Count Rate cps (float32 LE) |
| 17 | 4 | Level 0-9 (float32 LE) |
| 21 | 4 | Dose Time (Time_t, uint32 LE bitfield) |
| 25 | 4 | Dose Date (Date_t, uint32 LE bitfield) |
| 29 | 4 | Dose µSv (float32 LE) |
| 33 | 4 | Dose Duration s (float32 LE) |
| 37 | 1 | Battery State (uint8, bitfield) |
| 38 | 1 | Battery Level % (uint8) |
| 39 | 4 | System State (uint32 LE, bitfield) |
| 43 | 4 | Measurement ID (uint32 LE) |

---

*Fin du PRD — Ce document constitue la référence complète pour le développement de l'API AccuRad PRD.*
