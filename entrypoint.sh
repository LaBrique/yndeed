#!/bin/bash
set -e

echo "[STARTUP] Demarrage de Yndeed..."

# Attendre que la base de données soit prête
if [ -n "$DATABASE_HOST" ]; then
    echo "[DB] Attente de la base de donnees PostgreSQL..."
    while ! python -c "import socket; socket.create_connection(('$DATABASE_HOST', ${DATABASE_PORT:-5432}), timeout=1)" 2>/dev/null; do
        echo "   Base de donnees non disponible, nouvelle tentative dans 2s..."
        sleep 2
    done
    echo "[DB] Base de donnees disponible !"
fi

# Appliquer les migrations
echo "[MIGRATE] Application des migrations..."
python manage.py migrate --noinput

# Collecter les fichiers statiques (au cas où)
echo "[STATIC] Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Lancer la commande passée en argument
echo "[RUN] Lancement: $@"
exec "$@"
