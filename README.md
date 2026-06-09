# eFootball Rewards

Plateforme de récompenses pour joueurs eFootball Mobile.

---

## Lancer le projet avec Docker

**Prérequis :** Docker Desktop installé et démarré.

### Première fois (ou après un changement de code)

```bash
# 1. Construire et lancer tous les services
docker-compose up -d --build

# 2. Créer un compte administrateur
docker-compose exec web python manage.py createsuperuser
```

> Les migrations et la collecte des fichiers statiques sont exécutées
> **automatiquement** au démarrage du conteneur web.

### Démarrage normal (après la première fois)

```bash
docker-compose up -d
```

### Vérifier que tout fonctionne

```bash
docker-compose ps
```

Tous les services doivent être `Up` :

```
efootball_db      Up (healthy)
efootball_redis   Up (healthy)
efootball_web     Up
efootball_nginx   Up
```

---

## Accès

| Page | URL |
|---|---|
| Site principal | http://localhost |
| Tableau de bord admin | http://localhost/admin-panel/ |
| Django admin | http://localhost/admin/ |
| Documentation API | http://localhost/api/docs/ |

---

## Commandes utiles

```bash
# Voir les logs en temps réel
docker-compose logs -f web

# Logs d'un service spécifique
docker-compose logs -f db

# Lancer les tests
docker-compose exec web python manage.py test tests/

# Accéder au shell Django
docker-compose exec web python manage.py shell

# Arrêter les services (sans supprimer les données)
docker-compose down

# Arrêter ET supprimer toutes les données (reset complet)
docker-compose down -v
```

---

## Variables d'environnement importantes (fichier `.env`)

| Variable | Description | Valeur Docker |
|---|---|---|
| `DB_HOST` | Hôte PostgreSQL | `db` ← nom du service Docker |
| `DB_PORT` | Port PostgreSQL | `5432` ← port interne |
| `REDIS_URL` | URL Redis | `redis://redis:6379/1` |
| `DEBUG` | Mode debug | `True` |
| `SECRET_KEY` | Clé secrète Django | À changer en production |

> **Important :** Ne jamais mettre `localhost` pour `DB_HOST` dans Docker.
> Le service PostgreSQL s'appelle `db` dans le réseau Docker interne.

---

## Lancer en local sans Docker

**Prérequis :** Python 3.13+, PostgreSQL, Redis.

```bash
# 1. Environnement virtuel
python -m venv .venv
.venv\Scripts\activate

# 2. Dépendances
pip install -r requirements.txt

# 3. Variables d'environnement
copy .env.example .env
# Dans .env, changer DB_HOST=localhost et REDIS_URL=redis://localhost:6379/1

# 4. Migrations
python manage.py migrate

# 5. Lancer
python manage.py runserver
```

---

## Résolution de problèmes

**Le conteneur web redémarre en boucle ?**
```bash
docker-compose logs web
```
Chercher l'erreur dans les logs. Souvent : DB_HOST incorrect ou PostgreSQL pas encore prêt.

**Erreur de connexion PostgreSQL ?**
Vérifier dans `.env` : `DB_HOST=db` (et non `localhost`).

**Page blanche ou erreur 500 ?**
```bash
docker-compose logs web | tail -50
```
