-- Migration : ajout user_id pour isoler les données par utilisateur
-- Coller dans l'éditeur SQL de Supabase

-- 1. Ajouter user_id aux tables existantes
ALTER TABLE brands         ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE sections       ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE brand_history  ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- 2. Supprimer l'ancienne contrainte UNIQUE sur ad_id (on va en créer une composite)
ALTER TABLE transcriptions DROP CONSTRAINT IF EXISTS transcriptions_ad_id_key;
ALTER TABLE transcriptions ADD CONSTRAINT transcriptions_ad_id_user_id_key UNIQUE (ad_id, user_id);

-- 3. Modifier la PRIMARY KEY des sections (name → name + user_id)
ALTER TABLE sections DROP CONSTRAINT IF EXISTS sections_pkey;
ALTER TABLE sections ADD PRIMARY KEY (name, user_id);

-- 4. Index pour les performances
CREATE INDEX IF NOT EXISTS idx_brands_user         ON brands(user_id);
CREATE INDEX IF NOT EXISTS idx_sections_user       ON sections(user_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_user ON transcriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_history_user        ON brand_history(user_id);

-- 5. Activer Row Level Security
ALTER TABLE brands         ENABLE ROW LEVEL SECURITY;
ALTER TABLE sections       ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_history  ENABLE ROW LEVEL SECURITY;

-- 6. Policies : chaque utilisateur voit et modifie uniquement ses données
CREATE POLICY "brands_user_policy" ON brands
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "sections_user_policy" ON sections
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "transcriptions_user_policy" ON transcriptions
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "brand_history_user_policy" ON brand_history
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
