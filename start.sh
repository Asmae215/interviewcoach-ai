#!/bin/sh
# Démarre l'API FastAPI (accessible seulement à l'intérieur du conteneur),
# puis l'interface Streamlit sur le port public fourni par l'hébergeur.
set -e

uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

# Attend que l'API réponde avant d'ouvrir l'interface (au plus 30 s)
for i in $(seq 1 30); do
    if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>/dev/null; then
        break
    fi
    sleep 1
done

exec streamlit run frontend/app.py \
    --server.port "${PORT:-8501}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
