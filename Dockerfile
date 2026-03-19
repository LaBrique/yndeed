# Image slim Debian (packages precompiles, plus rapide)
FROM python:3.11-slim

WORKDIR /app

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . /app/

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput || true

# Créer un utilisateur non-root pour la sécurité
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Port exposé
EXPOSE 8000

# Script d'entrée
COPY entrypoint.sh /app/entrypoint.sh
USER root
RUN chmod +x /app/entrypoint.sh
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]