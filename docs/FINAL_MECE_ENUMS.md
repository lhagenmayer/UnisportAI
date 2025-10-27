# ✅ Finale MECE ENUMs

## Übersicht der Änderungen

### ❌ Entfernt für bessere MECE-Compliance:
1. **`casual`** (aus setting_type) - war 95x verwendet, ersetzt durch NULL
2. **`agility`** (aus focus_type) - war 4x, ersetzt durch `coordination`
3. **`power`** (aus focus_type) - war 10x, ersetzt durch `strength`

### ✅ Behalten:
- **`balance`** (26x verwendet) - ist spezifisch für Gleichgewicht
- **`speed`** (3x verwendet) - ist spezifisch für Schnelligkeit

---

## Finale ENUMs

### 1. focus_type (8 Werte)

```sql
CREATE TYPE focus_type AS ENUM (
    'strength',      -- Kraft (inkl. ehemals power)
    'endurance',     -- Ausdauer
    'flexibility',   -- Beweglichkeit
    'coordination',  -- Koordination (inkl. ehemals agility)
    'balance',      -- Gleichgewicht
    'speed',        -- Schnelligkeit
    'relaxation',   -- Entspannung
    'longevity'     -- Gesundheit
);
```

**Häufigkeit:**
1. endurance: 103x
2. coordination: 70x (inkl. ex-agility)
3. strength: 60x (inkl. ex-power)
4. relaxation: 40x
5. balance: 26x
6. flexibility: 18x
7. longevity: 17x
8. speed: 3x

---

### 2. intensity_type (3 Werte)

```sql
CREATE TYPE intensity_type AS ENUM (
    'low',      -- Entspannung, sanft
    'moderate', -- Durchschnittlich
    'high'      -- Intensiv
);
```

**Unverändert** - bereits MECE.

---

### 3. setting_type (5 Werte)

```sql
CREATE TYPE setting_type AS ENUM (
    'solo',       -- Gruppengröße: alleine
    'duo',        -- Gruppengröße: zu zweit
    'team',       -- Gruppengröße: Gruppe
    'competitive', -- Stil: wettbewerbsorientiert
    'fun'         -- Stil: spaßig/nicht-wettbewerbsorientiert
);
```

**Änderungen:**
- ❌ `casual` entfernt (war 95x, jetzt nur Gruppengröße)
- ❌ `social` entfernt (war redundant mit fun)

**Neue Verteilung:**
- solo: 84x
- fun: 43x
- competitive: 25x
- team: 21x
- duo: 21x

**Logik:**
- Jedes Angebot braucht EINE Gruppengröße (solo/duo/team)
- Kann optional EINEN Stil haben (competitive/fun)
- Wenn kein Stil, dann neutral

---

### 4. indoor_outdoor_type (2 Werte)

```sql
CREATE TYPE indoor_outdoor_type AS ENUM (
    'indoor',   -- Drinnen
    'outdoor'   -- Draußen
);
```

**Unverändert** - bereits MECE (Dichotomie).

---

## MECE Validierung

### ✅ Erlaubt:

```sql
-- Nur Gruppengröße
setting: ['solo']

-- Gruppengröße + Stil
setting: ['duo', 'competitive']
setting: ['team', 'fun']

-- Mehrere Foci
focus: ['endurance', 'coordination', 'strength']

-- Kombiniert
focus: ['strength', 'endurance']
intensity: 'high'
setting: ['solo']
indoor_outdoor: 'indoor'
```

### ❌ Nicht mehr erlaubt:

```sql
-- casual ist removed
setting: ['casual']

-- agility → coordination
focus: ['agility']

-- power → strength
focus: ['power']
```

---

## Migration Summary

**Entfernt:**
- `casual` (95 → 0 Einträge)
- `social` (16 → 0 Einträge)
- `agility` (4 → 0, ersetzt durch coordination)
- `power` (10 → 0, ersetzt durch strength)

**Neu:**
- `coordination` (66 → 70 Einträge)
- `strength` (50 → 60 Einträge)

**Total:** 182 Sportangebote haben jetzt MECE-konforme Daten!

