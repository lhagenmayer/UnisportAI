-- =====================================================================
-- UnisportAI - Database Schema (Tables + Views)
-- =====================================================================
-- This file defines the full relational schema for the UnisportAI app
-- on Supabase. It is the single source of truth for:
--   - core user accounts (linked to external auth via `sub`)
--   - scraped Unisport offers, courses, locations and trainers
--   - ETL bookkeeping and ML-facing views
--
-- The goal is to keep the logical model simple and ML‑friendly while
-- still being convenient to query from the Streamlit app.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. Schema and prerequisites
-- ---------------------------------------------------------------------
-- We keep everything in the default `public` schema on Supabase and
-- enable `pgcrypto` to generate UUIDs via `gen_random_uuid()`.

CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;

-- Enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------
-- 1. Core user table
-- ---------------------------------------------------------------------
-- `users` stores all app users. It is intentionally decoupled from the
-- Supabase auth schema; we link via the `sub` (subject) claim from the
-- IdP and optionally the email address.
--
-- Notes:
--   - `id` is our internal UUID primary key used everywhere as FK.
--   - `sub` is unique per identity provider user and used to look up
--     or create users after login.

CREATE TABLE IF NOT EXISTS public.users (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    email       text UNIQUE,  -- optional; may be NULL if provider does not share it
    sub         text UNIQUE,  -- stable subject identifier from the IdP (e.g. Google)
    name        text,         -- display name shown in the UI
    picture     text,         -- URL to avatar/profile picture

    created_at  timestamptz DEFAULT now(),
    updated_at  timestamptz DEFAULT now(),
    last_login  timestamptz
);

-- ---------------------------------------------------------------------
-- 2. Sport offers and related tables
-- ---------------------------------------------------------------------
-- This section contains the *content* model coming from the Unisport
-- website:
--   - `sportangebote`: the abstract offers (e.g. “Yoga für Einsteiger”)
--   - `sportkurse`: concrete bookable courses of an offer
--   - `unisport_locations`: physical locations of appointments
--   - `kurs_termine`: concrete time slots of a course
--   - `trainer` + `kurs_trainer`: responsible trainers per course

CREATE TABLE IF NOT EXISTS public.sportangebote (
    href        text PRIMARY KEY,  -- canonical URL on the Unisport website
    name        text NOT NULL,     -- human‑readable title of the offer
    description text,              -- long‑form description scraped from the page

    -- Intensity as plain text (expected values: 'low', 'moderate', 'high').
    -- This is intentionally coarse and later mapped to numeric values
    -- in the ML views.
    intensity   text,

    -- Focus and setting as simple tag lists.
    -- Examples for `focus`:     ['strength', 'endurance']
    -- Examples for `setting`:   ['team', 'fun']
    focus       text[],
    setting     text[],

    icon        text,      -- icon identifier used in the UI
    image_url   text       -- hero image URL used by the app
);

CREATE TABLE IF NOT EXISTS public.sportkurse (
    kursnr        text PRIMARY KEY,  -- course number as used by Unisport
    details       text,              -- additional descriptive text
    preis         text,              -- price information as scraped string
    buchung       text,              -- booking status / URL snippet
    offer_href    text,              -- FK to the parent offer
    zeitraum_href text,              -- identifier for the overall time period

    CONSTRAINT sportkurse_offer_href_fkey
        FOREIGN KEY (offer_href)
        REFERENCES public.sportangebote(href)
);

CREATE TABLE IF NOT EXISTS public.trainer (
    name       text PRIMARY KEY,  -- trainer's name as scraped from Unisport
    created_at timestamptz DEFAULT now()  -- first time we saw this trainer
);

CREATE TABLE IF NOT EXISTS public.unisport_locations (
    name           text PRIMARY KEY,  -- human‑readable location name from Unisport
    lat            double precision,  -- optional latitude for map display
    lng            double precision,  -- optional longitude for map display
    ort_href       text,              -- location URL on Unisport
    spid           text,              -- scraped location id (if available)

    -- Indoor / outdoor classification as plain text.
    -- Typical values: 'indoor', 'outdoor', 'mixed', 'unknown'.
    -- This is used for filtering and UX hints in the UI.
    indoor_outdoor text
);

CREATE TABLE IF NOT EXISTS public.kurs_termine (
    kursnr        text NOT NULL,              -- FK to `sportkurse`
    ort_href      text,                       -- raw location URL
    canceled      boolean NOT NULL DEFAULT false,  -- true if Unisport marks it as cancelled
    location_name text,                       -- FK to `unisport_locations.name`
    start_time    timestamptz NOT NULL,       -- start of the appointment
    end_time      timestamptz,                -- end if known; may be NULL

    CONSTRAINT kurs_termine_pkey
        PRIMARY KEY (kursnr, start_time),

    CONSTRAINT kurs_termine_kursnr_fkey
        FOREIGN KEY (kursnr)
        REFERENCES public.sportkurse(kursnr),

    CONSTRAINT kurs_termine_location_fk
        FOREIGN KEY (location_name)
        REFERENCES public.unisport_locations(name)
);

CREATE TABLE IF NOT EXISTS public.kurs_trainer (
    kursnr       text NOT NULL,   -- FK to `sportkurse`
    trainer_name text NOT NULL,   -- FK to `trainer`

    CONSTRAINT kurs_trainer_pkey
        PRIMARY KEY (kursnr, trainer_name),

    CONSTRAINT kurs_trainer_kursnr_fkey
        FOREIGN KEY (kursnr)
        REFERENCES public.sportkurse(kursnr),

    CONSTRAINT kurs_trainer_trainer_name_fkey
        FOREIGN KEY (trainer_name)
        REFERENCES public.trainer(name)
);

-- ---------------------------------------------------------------------
-- 5. ETL bookkeeping
-- ---------------------------------------------------------------------
-- `etl_runs` tracks when which scraping / ingestion component last ran.
-- This is intentionally minimal, it can be joined with external logs
-- and dashboards for monitoring.

CREATE TABLE IF NOT EXISTS public.etl_runs (
    id        bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    ran_at    timestamptz NOT NULL DEFAULT now(),

    -- Component name stored as free text for simplicity, e.g.:
    --   'scrape_offers', 'scrape_courses', 'train_recommender', ...
    component text NOT NULL
);

-- =====================================================================
-- 6. Views (same structure as in main schema, but using simple types)
-- =====================================================================

-- 6.1 ml_training_data
-- ----------------------
-- This view flattens `sportangebote` into a purely numeric / one‑hot
-- encoded feature table used for model training and inference.
--
-- It keeps:
--   - `href` : stable identifier for joining predictions back
--   - `Angebot` : human‑readable label
--   - one column per focus tag (0.0/1.0)
--   - `intensity` mapped to [0.0, 1.0]
--   - one column per setting tag (0.0/1.0)

CREATE OR REPLACE VIEW public.ml_training_data AS
SELECT
    sa.href AS href,
    sa.name AS "Angebot",

    -- Each focus tag becomes a 0.0/1.0 feature using `= ANY (array)`:
    --   expr = ANY(array_column) is true if expr is contained in the array.
    CASE WHEN 'balance'     = ANY (sa.focus) THEN 1.0 ELSE 0.0 END AS balance,
    CASE WHEN 'flexibility' = ANY (sa.focus) THEN 1.0 ELSE 0.0 END AS flexibility,
    CASE WHEN 'coordination'= ANY (sa.focus) THEN 1.0 ELSE 0.0 END AS coordination,
    CASE WHEN 'relaxation'  = ANY (sa.focus) THEN 1.0 ELSE 0.0 END AS relaxation,
    CASE WHEN 'strength'    = ANY (sa.focus) THEN 1.0 ELSE 0.0 END AS strength,
    CASE WHEN 'endurance'   = ANY (sa.focus) THEN 1.0 ELSE 0.0 END AS endurance,
    CASE WHEN 'longevity'   = ANY (sa.focus) THEN 1.0 ELSE 0.0 END AS longevity,

    -- Map categorical `intensity` strings to a numeric scale in [0, 1]:
    -- `CASE` works like a switch expression that returns the first matching branch.
    CASE sa.intensity
        WHEN 'low'      THEN 0.33
        WHEN 'moderate' THEN 0.67
        WHEN 'high'     THEN 1.0
        ELSE 0.0
    END AS intensity,

    -- Same pattern for `setting` tags, again via `= ANY (array)`:
    CASE WHEN 'team'        = ANY (sa.setting) THEN 1.0 ELSE 0.0 END AS setting_team,
    CASE WHEN 'fun'         = ANY (sa.setting) THEN 1.0 ELSE 0.0 END AS setting_fun,
    CASE WHEN 'duo'         = ANY (sa.setting) THEN 1.0 ELSE 0.0 END AS setting_duo,
    CASE WHEN 'solo'        = ANY (sa.setting) THEN 1.0 ELSE 0.0 END AS setting_solo,
    CASE WHEN 'competitive' = ANY (sa.setting) THEN 1.0 ELSE 0.0 END AS setting_competitive

FROM public.sportangebote sa;

-- 6.2 vw_offers_complete
-- -----------------------
-- High‑level *offer* view for the app. It enriches `sportangebote` with:
--   - number of *future* events (for availability indicators)
--   - list of trainers per offer

CREATE OR REPLACE VIEW public.vw_offers_complete AS
WITH future_events AS (
    SELECT
        sk.offer_href AS href,

        -- `COUNT(*) FILTER (WHERE ...)` is a conditional aggregate:
        -- it only counts rows that satisfy the filter condition (>= now, not cancelled).
        COUNT(*) FILTER (
            WHERE kt.start_time >= now()
              AND kt.canceled = false
        ) AS future_events_count
    FROM public.sportkurse sk
    JOIN public.kurs_termine kt
      ON kt.kursnr = sk.kursnr
    GROUP BY sk.offer_href
),
offer_trainers AS (
    SELECT
        sk.offer_href AS href,
        -- `jsonb_build_object` constructs a JSON object from key/value pairs.
        -- `jsonb_agg(DISTINCT ...)` aggregates all distinct objects into
        -- a JSON array. The result is one JSONB array per offer that lists
        -- all associated trainers.
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'name', t.name
            )
        ) AS trainers
    FROM public.sportkurse sk
    JOIN public.kurs_trainer kt
      ON kt.kursnr = sk.kursnr
    JOIN public.trainer t
      ON t.name = kt.trainer_name
    GROUP BY sk.offer_href
)
SELECT
    sa.href,
    sa.name,
    sa.description,
    sa.intensity,
    sa.focus,
    sa.setting,
    sa.icon,
    sa.image_url,

    -- `COALESCE(a, b)` returns the first non‑NULL argument.
    -- We use it to provide sensible defaults when there is no data
    -- in the joined tables:
    --   - no future events -> 0
    --   - no trainers      -> empty JSON array instead of NULL
    COALESCE(fe.future_events_count, 0)      AS future_events_count,
    COALESCE(ot.trainers, '[]'::jsonb)       AS trainers
FROM public.sportangebote sa
LEFT JOIN future_events  fe ON fe.href = sa.href
LEFT JOIN offer_trainers ot ON ot.href = sa.href;

-- 6.3 vw_termine_full
-- --------------------
-- This view returns *appointments* (single course dates) enriched with
-- offer name and trainer list. It is optimized for the timetable UI.

CREATE OR REPLACE VIEW public.vw_termine_full AS
WITH trainer_per_course AS (
    SELECT
        kt.kursnr,  -- join key back to `kurs_termine` / `sportkurse`

        -- Same pattern as in `vw_offers_complete`:
        -- build one JSONB array of distinct trainers per course number.
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'name', t.name
            )
        ) AS trainers
    FROM public.kurs_trainer kt
    JOIN public.trainer t
      ON t.name = kt.trainer_name
    GROUP BY kt.kursnr
)
SELECT
    kt.kursnr,
    sk.offer_href,
    sa.name AS sport_name,
    kt.location_name,
    kt.start_time,
    kt.end_time,
    kt.canceled,
    COALESCE(tpc.trainers, '[]'::jsonb) AS trainers
FROM public.kurs_termine kt
JOIN public.sportkurse sk
  ON sk.kursnr = kt.kursnr
JOIN public.sportangebote sa
  ON sa.href = sk.offer_href
LEFT JOIN trainer_per_course tpc
  ON tpc.kursnr = kt.kursnr;

-- Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
-- All outputs generated by such systems were reviewed, validated, and modified by the author.