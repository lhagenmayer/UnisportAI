# ENUM Design: MECE Prinzip

## Übersicht

Alle ENUMs in der Datenbank folgen dem **MECE Prinzip** (Mutually Exclusive, Collectively Exhaustive):

- **Mutually Exclusive**: Werte überschneiden sich NICHT
- **Collectively Exhaustive**: Alle Fälle sind abgedeckt

---

## 1. Focus Type (10 Werte)

**Was trainiert wird:**

```sql
CREATE TYPE focus_type AS ENUM (
    'strength',      -- Kraft
    'flexibility',   -- Beweglichkeit
    'endurance',     -- Ausdauer
    'power',         -- Explosivkraft
    'balance',       -- Gleichgewicht
    'coordination',  -- Koordination
    'speed',         -- Schnelligkeit
    'agility',       -- Beweglichkeit/Agilität
    'relaxation',    -- Entspannung
    'longevity'      -- Gesundheit/Langlebigkeit
);
```

**Gruppenbildung:**
- **Körperliche Fähigkeiten**: strength, endurance, power, flexibility, balance
- **Koordinative Fähigkeiten**: coordination, speed, agility
- **Gesundheit & Wellness**: relaxation, longevity

---

## 2. Intensity Type (3 Werte)

**Wie intensiv ist es:**

```sql
CREATE TYPE intensity_type AS ENUM (
    'low',      -- Entspannung, sanft
    'moderate', -- Durchschnittlich
    'high'      -- Intensiv
);
```

**MECE**: Klare Abstufung ohne Überschneidung.

---

## 3. Setting Type (6 Werte)

**Wie wird es betrieben:**

```sql
CREATE TYPE setting_type AS ENUM (
    'solo',      -- Gruppengröße: alleine
    'duo',       -- Gruppengröße: zu zweit
    'team',      -- Gruppengröße: Gruppe
    'competitive', -- Stil: wettbewerbsorientiert
    'casual',    -- Stil: entspannt/für alle
    'fun'        -- Stil: spaßig/spielerisch
);
```

**MECE Struktur:**

| Gruppengröße | Stil |
|-------------|------|
| solo        | competitive, casual, fun |
| duo         | competitive, casual, fun |
| team        | competitive, casual, fun |

**Beispiele:**
- `['solo', 'casual']` - alleine, entspannt (Yoga)
- `['duo', 'competitive']` - zu zweit, wettbewerbsorientiert (Tennis Level 6)
- `['team', 'fun']` - Gruppe, spaßig (Volleyball Freizeit)

**WICHTIG**: Ein Sportangebot kann MEHRERE Settings haben:
- Gruppengröße: EINE von (solo, duo, team)
- Stil: MEHRERE möglich (competitive, casual, fun)

**Deprecated:**
- ❌ `social` - durch `fun` ersetzt (war redundant)

---

## 4. Indoor Outdoor Type (2 Werte)

**Wo findet es statt:**

```sql
CREATE TYPE indoor_outdoor_type AS ENUM (
    'indoor',   -- Drinnen
    'outdoor'   -- Draußen
);
```

**MECE**: Vollständige Dichotomie ohne Überschneidung.

---

## MECE Validierung

### ✅ Erlaubte Kombinationen

```sql
-- Gruppengröße + Stil
focus: ['strength', 'endurance']
intensity: 'high'
setting: ['duo', 'competitive']

-- Mehrere Foci
focus: ['flexibility', 'strength', 'balance']
intensity: 'low'
setting: ['solo', 'casual']
```

### ❌ Ungültige Kombinationen

```sql
-- Widersprüchliche Settings
setting: ['solo', 'duo']  -- Nur EINE Gruppengröße!
setting: ['casual', 'competitive']  -- Widersprüchliche Stile!
```

---

## Best Practices

1. **Focus**: Kann MEHRERE Werte haben (Array)
2. **Intensity**: EIN Wert
3. **Setting**: MEHRERE Werte erlaubt, aber nur EINE Gruppengröße
4. **Indoor/Outdoor**: EIN Wert

**Beispiel-Eintrag:**

```json
{
  "focus": ["endurance", "coordination"],
  "intensity": "moderate",
  "setting": ["duo", "casual"],
  "indoor_outdoor": "indoor"
}
```

