# Yndeed - Plateforme de Recherche d'Emploi pour les étudiants d'Ynov

Application web Django permettant la recherche et l'agrégation d'offres d'emploi, déployée avec Docker Compose.

---


### Prérequis
- Docker et Docker Compose installés
- Port 8080 disponible

### Démarrer l'application

```bash
# Cloner le projet et se placer dans le répertoire
cd yndeed

# Lancer tous les services
docker compose up -d

# Vérifier que les conteneurs sont actifs
docker compose ps
```

### Accéder à l'application

| Service | URL |
|---------|-----|
| Application Web | http://localhost:8080 |
| API REST | http://localhost:8080/api/ |
| Admin Django | http://localhost:8080/admin/ |

### Commandes utiles

```bash
# Voir les logs de tous les services
docker compose logs -f

# Voir les logs d'un service spécifique
docker compose logs -f web
docker compose logs -f worker

# Arrêter l'application
docker compose down

# Arrêter et supprimer les volumes (reset complet)
docker compose down -v
```

---

## Architecture

### Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT                                │
│                    (Navigateur Web)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ :8080
┌─────────────────────▼───────────────────────────────────────┐
│                      NGINX                                   │
│              (Reverse Proxy / Load Balancer)                 │
│         - Sert les fichiers statiques                        │
│         - Proxy vers Django                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ :8000 (interne)
┌─────────────────────▼───────────────────────────────────────┐
│                    DJANGO + GUNICORN                         │
│                  (Application Web)                           │
│         - API REST                                           │
│         - Authentification                                   │
│         - Interface utilisateur                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    POSTGRESQL                                │
│                  (Base de données)                           │
└─────────────────────────────────────────────────────────────┘
                      ▲
┌─────────────────────┴───────────────────────────────────────┐
│                      WORKER                                  │
│         (Collecte automatique des offres d'emploi)           │
│         - Exécution toutes les 4 heures                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Conteneurs Docker

### Services implémentés

| Conteneur | Image | Rôle | Port | Status |
|-----------|-------|------|------|--------|
| `yndeed_nginx` | `nginx:alpine` | Reverse proxy, serveur de fichiers statiques | 8080:80 | ✅ Implémenté |
| `yndeed_web` | `python:3.11-slim` (build) | Application Django avec Gunicorn (3 workers) | 8000 (interne) | ✅ Implémenté |
| `yndeed_db` | `postgres:15-alpine` | Base de données PostgreSQL | 5432 (interne) | ✅ Implémenté |
| `yndeed_worker` | `python:3.11-slim` (build) | Worker de collecte d'offres d'emploi | - | ✅ Implémenté |

### Services non implémentés (améliorations futures)

| Service | Image suggérée | Rôle | Status |
|---------|----------------|------|--------|
| Grafana | `grafana/grafana` | Monitoring et dashboards | ❌ Non implémenté |
| Prometheus | `prom/prometheus` | Collecte de métriques | ❌ Non implémenté |
| Redis | `redis:alpine` | Cache et file de messages | ❌ Non implémenté |
| Celery | - | File de tâches asynchrones | ❌ Non implémenté |

---

## Choix Technologiques

| Technologie | Alternatives | Pourquoi ce choix |
|-------------|--------------|-------------------|
| **Django** | Flask, FastAPI | Framework complet (ORM, admin, auth intégrés), idéal pour un MVP rapide |
| **PostgreSQL** | MySQL, SQLite | Robuste, performant, meilleur support JSON et full-text search |
| **Nginx** | Apache, Traefik | Léger, performant pour les fichiers statiques, configuration simple |
| **Gunicorn** | uWSGI, Daphne | Standard Python WSGI, simple à configurer, stable |
| **Docker Compose** | Kubernetes, Swarm | Adapté aux projets de petite/moyenne taille, courbe d'apprentissage faible |
| **Alpine images** | Debian, Ubuntu | Images légères (~5MB vs ~100MB), démarrage plus rapide |

---

## Configuration

### Variables d'environnement

Créez un fichier `.env` à la racine du projet pour personnaliser la configuration :

```env
# Base de données
DATABASE_NAME=yndeed
DATABASE_USER=yndeed
DATABASE_PASSWORD=yndeed_secret_2026

# Django
DEBUG=False
SECRET_KEY=votre-cle-secrete-production
ALLOWED_HOSTS=localhost,127.0.0.1,votre-domaine.com
CSRF_TRUSTED_ORIGINS=http://localhost,http://votre-domaine.com

# Email (pour la vérification des comptes)
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-application
```

### Volumes Docker

| Volume | Chemin conteneur | Description |
|--------|------------------|-------------|
| `yndeed_postgres_data` | `/var/lib/postgresql/data` | Données PostgreSQL persistantes |
| `yndeed_static` | `/app/staticfiles` | Fichiers statiques (CSS, JS, images) |

---

##  Sécurité

### Mesures implémentées

| Mesure | Description | 
|--------|-------------|
| Reverse Proxy | Nginx masque l'application Django |
| Utilisateur non-root | Application exécutée avec `appuser` |
| Headers de sécurité | X-Real-IP, X-Forwarded-For, etc. |
| Healthchecks | Vérification de disponibilité des services |
| Secrets externalisés | Variables d'environnement |
| Réseau interne | Seul Nginx exposé publiquement |

### Améliorations recommandées

- [ ] Ajouter HTTPS avec Let's Encrypt
- [ ] Configurer rate limiting sur Nginx

---

##  Structure du Projet

```
yndeed/
├── AppYndeed/              # Application Django principale
│   ├── models.py           # Modèles de données
│   ├── views/              # Vues (API, Auth, Index)
│   ├── templates/          # Templates HTML
│   ├── static/             # Fichiers statiques sources
│   └── management/         # Commandes personnalisées (collect_jobs)
├── Yndeed/                 # Configuration Django
│   ├── settings.py
│   └── urls.py
├── nginx/
│   └── nginx.conf          # Configuration Nginx
├── docker-compose.yml      # Orchestration des conteneurs
├── Dockerfile              # Image de l'application
├── entrypoint.sh           # Script de démarrage
├── requirements.txt        # Dépendances Python
└── README.md               # Ce fichier
```