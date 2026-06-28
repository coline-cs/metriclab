#!/bin/bash
# Installation de l'outil Meta Ads Transcriber
set -e

echo "=== Installation Meta Ads Transcriber ==="

# Vérifier Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 requis. Installe-le depuis https://python.org"
    exit 1
fi

# Vérifier ffmpeg (requis par Whisper)
if ! command -v ffmpeg &>/dev/null; then
    echo "⚠ ffmpeg non trouvé — installation via Homebrew..."
    if command -v brew &>/dev/null; then
        brew install ffmpeg
    else
        echo "❌ Homebrew non trouvé. Installe ffmpeg manuellement : https://ffmpeg.org/download.html"
        exit 1
    fi
fi

echo "✓ ffmpeg OK"

# Créer un environnement virtuel
if [ ! -d ".venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Installer les dépendances Python
echo "Installation des packages Python..."
pip install --upgrade pip -q
pip install -r requirements.txt

# Installer le navigateur Chromium pour Playwright
echo "Installation du navigateur Chromium..."
playwright install chromium

echo ""
echo "✅ Installation terminée !"
echo ""
echo "Pour lancer l'outil :"
echo "  source .venv/bin/activate"
echo '  python transcriber.py "https://www.facebook.com/ads/library/?q=TON_MOT_CLE&..."'
