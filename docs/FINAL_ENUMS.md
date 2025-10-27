# ✅ Finale MECE ENUMs

## Status: Alle ENUMs sind jetzt MECE!

---

## 1. focus_type (7 Werte)

```sql
-- Finale ENUM Werte (in DB, aber nicht alle verwendet):
CREATE TYPE focus_type AS ENUM (
    'flexibility',   -- Beweglichkeit
    'endurance',     -- Ausdauer
    'strength',      -- Kraft
    'longevity',     -- Gesundheit
    'relaxation',    -- Entspannung
    'balance',       -- Gleichgewicht
    'coordination'   -- Koordination
);

-- Deprecated (werden nicht mehr verwendet):
-- 'speed' (3 → 0x, ersetzt durch coordination)
-- 'power' (10 → 0x, ersetzt durch strength)
-- 'agility' (4 → 0x, ersetzt durch coordination)
```

**Verteilung:**
1. endurance: 103x
2. coordination: 73x (inkl. ex-speed, ex-agility)
3. strength: 60x (inkl. ex-power)
4. relaxation: 40x
5. balance: 26x
6. flexibility: 18x
7. longevity: 17x

**MECE:** Keine Überschneidung zwischen:
- **Physical**: strength, endurance, flexibility
- **Kinesthetic**: coordination, balance
- **Mental**: relaxation, longevity

---

## 2. intensity_type (3 Werte)

```sql
CREATE TYPE intensity_type AS ENUM (
    'low',      -- Entspannung, sanft
    'moderate', -- Durchschnittlich
    'high'      -- Intensiv
);
```

**MECE:** Klare Abstufung ohne Lücken.

---

## 3. setting_type (5 Werte)

```sql
CREATE TYPE setting_type AS ENUM (
    'solo',       -- Gruppengröße: alleine
    'duo',        -- Gruppengröße: zu zweit
    'team',       -- Gruppengröße: Gruppe
    'competitive', -- Stil: wettbewerbsorientiert
    'fun'         -- Stil: spaßig
);

-- Deprecated:
-- 'casual' (95 → 0x, entfernt)
-- 'social' (16 → 0x, ersetzt durch fun)
```

**Verteilung:**
- solo: 84x
- fun: 43x
- competitive: 25x
- team: 21x
- duo: 21x

**Logik:**
- Jedes Angebot braucht MINDESTENS 1 Gruppengröße (solo/duo/team)
- Kann optional 1 Stil haben (competitive/fun)
- Wenn kein Stil angegeben → neutral

**MECE:** 
- Gruppengröße (1-1 Beziehung)
- Stil (Optional)

---

## 4. indoor_outdoor_type (2 Werte)

```sql
CREATE TYPE indoor_outdoor_type AS ENUM (
    'indoor',   -- Drinnen
    'outdoor'   -- Draußen
);
```

**MECE:** Vollständige Dichotomie.

---

## Distinction: Balance vs Coordination

### ✅ Balance (Gleichgewicht)
**Definition:** Fähigkeit das Gleichgewicht zu halten, nicht umzufallen.

**Beispiele:**
- Yoga (Arm-Balance)
- Skifahren (Balance auf Skiern)
- Surfen (Balance auf Brett)
- Segeln (Balance im Boot)
- Aikido (Balance-Kontrolle)

### ✅ Coordination (Koordination)
**Definition:** Fähigkeit präzise Bewegungen auszuführen, Hand-Auge-Koordination.

**Beispiele:**
- Tennis (Schlagtechnik)
- Badminton (Racket-Kontrolle)
- Basketball (Dribbling + Wurf)
- Tischtennis (präzise Schläge)
- Fechten (Waffen-Koordination)

**Unterschied:**
- Balance = Statik, Stabilität
- Coordination = Dynamik, Präzision

---

## Summary

✅ **Entfernt:** casual, social, speed, power, agility (total 127 Einträge ersetzt)
✅ **Behalten:** balance und coordination (unterschiedlich!)
✅ **Finale Werte:** 7 focus, 3 intensity, 5 setting, 2 indoor_outdoor
✅ **MECE Compliant:** Alle ENUMs sind jetzt mutually exclusive & collectively exhaustive

