# eFootball Rewards

Plateforme de récompenses pour joueurs eFootball Mobile.

---

## Lancer le projet

### Option 1 — Docker (recommandé)

**Prérequis :** Docker Desktop installé et lancé.

```bash
# 1. Copier le fichier d'environnement
copy .env.example .env

# 2. Lancer tous les services
docker-compose up -d --build

# 3. Appliquer les migrations
docker-compose exec web python manage.py migrate

# 4. Créer un compte administrateur
docker-compose exec web python manage.py createsuperuser

# 5. Ouvrir dans le navigateur
# http://localhost
```

---

### Option 2 — En local (sans Docker)

**Prérequis :** Python 3.13+, PostgreSQL, Redis.

```bash
# 1. Créer et activer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Copier et configurer l'environnement
copy .env.example .env
# Ouvrir .env et renseigner DB_HOST=localhost, DB_USER, DB_PASSWORD

# 4. Créer la base de données PostgreSQL
# (dans psql ou pgAdmin)
# CREATE DATABASE efootball_rewards;

# 5. Appliquer les migrations
python manage.py migrate

# 6. Créer un compte administrateur
python manage.py createsuperuser

# 7. Lancer le serveur
python manage.py runserver
```

Ouvrir [http://localhost:8000](http://localhost:8000)

---

## Accès

| Page | URL |
|---|---|
| Site principal | http://localhost:8000 |
| Tableau de bord admin | http://localhost:8000/admin-panel/ |
| Django admin | http://localhost:8000/admin/ |
| Documentation API | http://localhost:8000/api/docs/ |

---

## Variables d'environnement importantes

Fichier `.env` à la racine du projet :

| Variable | Description |
|---|---|
| `SECRET_KEY` | Clé secrète Django (obligatoire) |
| `DEBUG` | `True` en développement, `False` en production |
| `DB_*` | Connexion PostgreSQL |
| `EMAIL_HOST_USER` | Email pour l'envoi des mails |
| `EMAIL_HOST_PASSWORD` | Mot de passe de l'email |

En développement, les emails s'affichent dans la console (pas besoin de configurer SMTP).

---

## Lancer les tests

```bash
pip install pytest-django pytest-cov
pytest
```

---

## Arrêter Docker

```bash
docker-compose down
```
