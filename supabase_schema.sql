-- MetricLab — Supabase schema
-- Coller dans l'éditeur SQL de Supabase (https://supabase.com/dashboard)

-- 1. Marques surveillées
CREATE TABLE IF NOT EXISTS brands (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  url         TEXT NOT NULL,
  label       TEXT DEFAULT 'Top Performers',
  notes       TEXT DEFAULT '',
  niche       TEXT DEFAULT '🐾 Animaux',
  tags        JSONB DEFAULT '[]',
  last_scraped TIMESTAMPTZ,
  ad_count    INTEGER DEFAULT 0,
  avg_score   FLOAT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Sections / catégories custom
CREATE TABLE IF NOT EXISTS sections (
  name        TEXT PRIMARY KEY,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO sections (name) VALUES ('Top Performers'), ('Nouvelles Créas') ON CONFLICT DO NOTHING;

-- 3. Transcriptions & analyses de pubs
CREATE TABLE IF NOT EXISTS transcriptions (
  id              BIGSERIAL PRIMARY KEY,
  ad_id           TEXT UNIQUE,
  position        INTEGER,
  page_name       TEXT,
  label           TEXT,
  transcript      TEXT,
  hook_3s         TEXT,
  lang            TEXT,
  eu_reach        BIGINT,
  start_date      TEXT,
  ad_format       TEXT,
  ad_format_source TEXT,
  video_url       TEXT,
  scoring         JSONB,
  hook_scoring    JSONB,
  body_scoring    JSONB,
  performance     JSONB,
  segments        JSONB,
  visual_analysis JSONB,
  text_overlays   TEXT,
  scraped_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trans_label    ON transcriptions(label);
CREATE INDEX IF NOT EXISTS idx_trans_page     ON transcriptions(page_name);
CREATE INDEX IF NOT EXISTS idx_trans_format   ON transcriptions(ad_format);
CREATE INDEX IF NOT EXISTS idx_trans_reach    ON transcriptions(eu_reach DESC);

-- 4. Historique temporel par marque (tracker)
CREATE TABLE IF NOT EXISTS brand_history (
  id          BIGSERIAL PRIMARY KEY,
  brand_name  TEXT NOT NULL,
  scraped_at  TIMESTAMPTZ DEFAULT NOW(),
  ads         JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_brand ON brand_history(brand_name, scraped_at DESC);

-- Row Level Security (désactivé pour usage mono-utilisateur avec service key)
-- ALTER TABLE brands         ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sections       ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE brand_history  ENABLE ROW LEVEL SECURITY;
