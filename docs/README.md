# eFootball Rewards

Plateforme web de récompenses pour joueurs eFootball Mobile.  
Les utilisateurs gagnent des points grâce à leur activité et les échangent contre des récompenses exclusives.

---

## Stack technique

| Couche | Technologie |
|---|---|
| Backend | Python 3.13+, Django 5, Django REST Framework |
| Base de données | PostgreSQL 16 |
| Cache | Redis 7 |
| Frontend | Django Templates, HTML5, CSS3, JavaScript |
| Authentification | Custom User Model + JWT (DRF SimpleJWT) |
| Emails | SMTP (configurable) |
| Déploiement | Docker, Docker Compose, Gunicorn, Nginx |

---

## Architecture

```
efootball_rewards/
├── config/            # Paramètres Django (base/dev/prod)
├── accounts/          # Utilisateurs, profils, points, streaks
├── rewards/           # Catalogue et demandes de récompenses
├── missions/          # Système de missions
├── notifications/     # Notifications internes
├── logs/              # Journal d'activité
├── dashboard/         # Tableaux de bord utilisateur et admin
├── api/               # REST API avec JWT
├── templates/         # Templates HTML
├── static/            # CSS, JS, images
├── media/             # Fichiers uploadés
├── tests/             # Suite de tests
└── docs/              # Documentation
```

---

## Installation (développement)

### Prérequis

- Python 3.13+
- PostgreSQL 16+
- Redis 7+
- Docker (optionnel)

### Étapes

```bash
# 1. Cloner le repo
git clone <repo-url>
cd efootball_rewards

# 2. Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate   # Windows
# ou: source .venv/bin/activate  # Linux/macOS

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# 5. Créer la base de données
createdb efootball_rewards

# 6. Appliquer les migrations
python manage.py migrate

# 7. Créer un superutilisateur
python manage.py createsuperuser

# 8. Charger les données de démonstration (optionnel)
python manage.py loaddata fixtures/demo.json

# 9. Lancer le serveur
python manage.py runserver
```

L'application sera disponible sur [http://localhost:8000](http://localhost:8000).

---

## Déploiement avec Docker

```bash
# 1. Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env

# 2. Construire et lancer les conteneurs
docker-compose up -d --build

# 3. Appliquer les migrations
docker-compose exec web python manage.py migrate

# 4. Créer un superutilisateur
docker-compose exec web python manage.py createsuperuser

# 5. Collecter les fichiers statiques
docker-compose exec web python manage.py collectstatic --noinput
```

L'application sera disponible sur [http://localhost](http://localhost).

---

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé secrète Django | **Obligatoire** |
| `DEBUG` | Mode debug | `False` |
| `ALLOWED_HOSTS` | Hôtes autorisés | `localhost,127.0.0.1` |
| `DB_NAME` | Nom de la base de données | `efootball_rewards` |
| `DB_USER` | Utilisateur PostgreSQL | `efootball` |
| `DB_PASSWORD` | Mot de passe PostgreSQL | — |
| `DB_HOST` | Hôte PostgreSQL | `localhost` |
| `REDIS_URL` | URL Redis | `redis://localhost:6379/1` |
| `EMAIL_HOST` | Serveur SMTP | `smtp.gmail.com` |
| `EMAIL_HOST_USER` | Email d'envoi | — |
| `EMAIL_HOST_PASSWORD` | Mot de passe SMTP | — |
| `DEFAULT_FROM_EMAIL` | Adresse d'envoi | `no-reply@efootball-rewards.com` |
| `SITE_URL` | URL du site | `http://localhost:8000` |

---

## API REST

Documentation interactive disponible sur `/api/docs/` (Swagger UI).

### Endpoints principaux

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Inscription |
| POST | `/api/auth/token/` | Obtenir un token JWT |
| POST | `/api/auth/token/refresh/` | Rafraîchir le token |
| GET | `/api/profile/` | Profil utilisateur |
| GET | `/api/rewards/` | Liste des récompenses |
| POST | `/api/rewards/{id}/redeem/` | Demander une récompense |
| GET | `/api/missions/` | Liste des missions |
| GET | `/api/notifications/` | Notifications |
| GET | `/api/dashboard/` | Résumé du tableau de bord |

### Authentification JWT

```bash
# Obtenir un token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"yourpassword"}'

# Utiliser le token
curl http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Système de points

| Action | Points |
|---|---|
| Connexion quotidienne | +10 |
| Streak 7 jours | +50 bonus |
| Streak 14 jours | +100 bonus |
| Streak 30 jours | +300 bonus |
| Missions | variable |

## Niveaux

| Niveau | Points totaux requis |
|---|---|
| Bronze | 0 |
| Argent | 500 |
| Or | 1 500 |
| Platine | 5 000 |
| Diamant | 15 000 |

---

## Tests

```bash
# Lancer tous les tests avec couverture
pytest

# Tests spécifiques
pytest tests/test_accounts.py
pytest tests/test_rewards.py
pytest tests/test_api.py
pytest tests/test_security.py

# Rapport HTML de couverture
pytest --cov-report=html
```

Couverture minimale requise : **80%**

---

## Administration

Interface d'administration personnalisée disponible sur `/admin-panel/`.

Accès au Django admin standard sur `/admin/`.

---

## Sécurité

- CSRF protection sur tous les formulaires
- Rate limiting sur login (10/min) et register (5/min)
- Mots de passe hashés (PBKDF2)
- Sessions sécurisées avec Redis
- Headers de sécurité (HSTS, XSS, etc.) en production
- Protection XSS via auto-escape Django
- Protection SQL injection via l'ORM Django
- JWT avec rotation des refresh tokens
