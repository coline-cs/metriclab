# Déploiement MetricLab — Railway + Supabase

## 1. Supabase (base de données)

1. Crée un compte sur https://supabase.com
2. Nouveau projet → région Europe (Paris si dispo)
3. Dans l'éditeur SQL : colle et exécute le contenu de `supabase_schema.sql`
4. Dans **Project Settings → API** :
   - Copie `Project URL` → c'est ton `SUPABASE_URL`
   - Copie `service_role` key (pas anon) → c'est ton `SUPABASE_KEY`

## 2. GitHub

```bash
cd "/Volumes/LaCie/CODE/n8n claude/meta-ads-transcriber"
git init
git add .
git commit -m "Initial MetricLab commit"
git remote add origin https://github.com/coline-cs/metriclab.git
git push -u origin main
```

## 3. Railway

1. https://railway.app → New Project → Deploy from GitHub repo
2. Sélectionne `coline-cs/metriclab`
3. **Variables d'environnement** (Settings → Variables) :
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_KEY=eyJ...service_role...
   PORT=8501
   ```
4. Railway détecte automatiquement `railway.toml` et `nixpacks.toml`
5. Déploiement en ~3 min

## 4. Volume persistant (vidéos + frames)

Dans Railway → ton service → **Volumes** :
- Mount path : `/app/transcriptions`
- Taille : 5 GB minimum

Les fichiers JSON (fallback) et les frames vidéo y seront stockés.

## 5. Variables facultatives

```
WHISPER_MODEL_OVERRIDE=small   # base | small | medium
SCROLL_COUNT_OVERRIDE=5        # nombre de scrolls lors du scraping
```

## Architecture résultante

```
Railway (Streamlit app)
    ↕ supabase-py
Supabase (Postgres)
    - brands
    - transcriptions
    - sections
    - brand_history

Railway Volume
    - frames vidéo
    - JSON fallback
    - historique tracker
```
