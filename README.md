# eFootball Rewards

Plateforme de récompenses pour joueurs eFootball Mobile — missions, points, invitations, échanges de Coins.

---

## Table des matières

1. [Prérequis](#prérequis)
2. [Lancement rapide avec Docker](#lancement-rapide-avec-docker)
3. [Première configuration complète](#première-configuration-complète)
4. [Accès au site](#accès-au-site)
5. [Commandes courantes](#commandes-courantes)
6. [Après une mise à jour du code](#après-une-mise-à-jour-du-code)
7. [Lancer sans Docker (local)](#lancer-sans-docker-local)
8. [Variables d'environnement](#variables-denvironnement)
9. [Résolution de problèmes](#résolution-de-problèmes)

---

## Prérequis

- **Docker Desktop** — [télécharger ici](https://www.docker.com/products/docker-desktop/)
- Docker Desktop doit être **démarré** avant toute commande

Vérifier que Docker fonctionne :
```bash
docker --version
docker-compose --version
```

---

## Lancement rapide avec Docker

> Si vous avez déjà tout configuré et voulez juste relancer le site :

```bash
docker-compose up -d
```

Le site est accessible sur **http://localhost**

---

## Première configuration complète

Suivez ces étapes dans l'ordre la **première fois** (ou après un `docker-compose down -v`).

### Étape 1 — Cloner / ouvrir le projet

```bash
cd D:\Efootbal\eFootball-Mobile
```

### Étape 2 — Vérifier le fichier `.env`

Le fichier `.env` doit être présent à la racine du projet. Contenu minimum requis :

```env
SECRET_KEY=votre-cle-secrete-ici
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=efootball_rewards
DB_USER=efootball
DB_PASSWORD=efootball_secret
DB_HOST=db
DB_PORT=5432

REDIS_URL=redis://redis:6379/1

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
SITE_URL=http://localhost
```

> **Important :** `DB_HOST` doit être `db` (nom du service Docker), jamais `localhost`.

### Étape 3 — Construire et démarrer les conteneurs

```bash
docker-compose up -d --build
```

Cette commande :
- Construit l'image Docker du projet
- Démarre PostgreSQL, Redis, l'application Django et Nginx
- Exécute automatiquement les migrations
- Collecte les fichiers statiques

Attendez que tous les services soient `Up` :
```bash
docker-compose ps
```

Résultat attendu :
```
NAME                  STATUS
efootball_db          Up (healthy)
efootball_redis       Up (healthy)
efootball_web         Up
efootball_nginx       Up
```

### Étape 4 — Appliquer les migrations

```bash
docker-compose exec web python manage.py migrate
```

### Étape 5 — Créer le compte administrateur

```bash
docker-compose exec web python manage.py createsuperuser
```

Vous devrez saisir :
- **Email** — votre email admin
- **Username** — votre nom d'utilisateur
- **Password** — mot de passe (8 caractères minimum)

### Étape 6 — Importer les missions réelles

```bash
docker-compose exec web python manage.py seed_data --clear-missions
```

Cette commande supprime les missions fictives et crée les 6 missions réelles :
1. Suivre Instagram officiel (100 pts, validation manuelle)
2. Compléter le profil (100 pts, automatique)
3. Visiter 3 jours consécutifs (150 pts, automatique)
4. Visiter 7 jours consécutifs (250 pts, automatique)
5. Inviter des amis (50 pts/invitation, max 10/mois)
6. Toutes les missions terminées (300 pts bonus, automatique)

### Étape 7 — Accéder au site

| Page | URL |
|---|---|
| Site principal | http://localhost |
| Tableau de bord admin | http://localhost/admin-panel/ |
| Django Admin | http://localhost/admin/ |
| Documentation API | http://localhost/api/docs/ |

---

## Accès au site

| Page | URL | Qui peut y accéder |
|---|---|---|
| Page d'accueil | http://localhost | Tous |
| Inscription | http://localhost/accounts/register/ | Non connectés |
| Connexion | http://localhost/accounts/login/ | Non connectés |
| Tableau de bord | http://localhost/dashboard/ | Utilisateurs connectés |
| Missions | http://localhost/missions/ | Utilisateurs connectés |
| Récompenses | http://localhost/rewards/ | Utilisateurs connectés |
| Mes échanges | http://localhost/rewards/exchange/ | Utilisateurs connectés |
| Mon profil | http://localhost/accounts/profile/ | Utilisateurs connectés |
| Panel admin | http://localhost/admin-panel/ | Staff/Admin uniquement |
| Django Admin | http://localhost/admin/ | Staff/Admin uniquement |
| API Swagger | http://localhost/api/docs/ | Tous |

---

## Commandes courantes

```bash
# Démarrer tous les services
docker-compose up -d

# Arrêter les services (les données sont conservées)
docker-compose down

# Voir les logs en temps réel
docker-compose logs -f web

# Voir les logs d'un service précis
docker-compose logs -f db
docker-compose logs -f redis
docker-compose logs -f nginx

# Accéder au shell Python Django
docker-compose exec web python manage.py shell

# Accéder à la base de données PostgreSQL
docker-compose exec db psql -U efootball -d efootball_rewards

# Créer un superuser
docker-compose exec web python manage.py createsuperuser

# Appliquer les migrations
docker-compose exec web python manage.py migrate

# Importer les missions (sans supprimer les existantes)
docker-compose exec web python manage.py seed_data

# Importer les missions (en supprimant les anciennes)
docker-compose exec web python manage.py seed_data --clear-missions

# Lancer les tests
docker-compose exec web python manage.py test tests/

# Collecter les fichiers statiques manuellement
docker-compose exec web python manage.py collectstatic --noinput

# Redémarrer seulement le service web (après modification du code)
docker-compose restart web
```

---

## Après une mise à jour du code

Quand vous modifiez des fichiers Python, HTML ou CSS :

```bash
# Option 1 — Rebuild complet (recommandé après changements de requirements.txt)
docker-compose up -d --build

# Option 2 — Redémarrage rapide (si seulement des fichiers .py/.html/.css ont changé)
docker-compose restart web

# Si vous avez ajouté/modifié des modèles, appliquer les migrations
docker-compose exec web python manage.py migrate
```

---

## Lancer sans Docker (local)

**Prérequis :** Python 3.11+, PostgreSQL 14+, Redis 7+.

### 1 — Créer un environnement virtuel

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 2 — Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3 — Configurer les variables d'environnement

Copier et adapter le fichier `.env` :
```bash
copy .env .env.local
```

Dans `.env`, changer :
```env
DB_HOST=localhost
REDIS_URL=redis://localhost:6379/1
DEBUG=True
```

### 4 — Appliquer les migrations

```bash
python manage.py migrate
```

### 5 — Créer un superuser

```bash
python manage.py createsuperuser
```

### 6 — Importer les missions

```bash
python manage.py seed_data --clear-missions
```

### 7 — Lancer le serveur de développement

```bash
python manage.py runserver
```

Site accessible sur **http://localhost:8000**

---

## Variables d'environnement

Liste complète des variables du fichier `.env` :

| Variable | Description | Valeur par défaut |
|---|---|---|
| `SECRET_KEY` | Clé secrète Django (obligatoire) | — |
| `DEBUG` | Mode debug (`True`/`False`) | `False` |
| `ALLOWED_HOSTS` | Domaines autorisés | `localhost,127.0.0.1` |
| `DB_NAME` | Nom de la base de données | `efootball_rewards` |
| `DB_USER` | Utilisateur PostgreSQL | `efootball` |
| `DB_PASSWORD` | Mot de passe PostgreSQL | `efootball_secret` |
| `DB_HOST` | Hôte PostgreSQL | `db` (Docker) / `localhost` (local) |
| `DB_PORT` | Port PostgreSQL | `5432` |
| `REDIS_URL` | URL Redis | `redis://redis:6379/1` |
| `EMAIL_BACKEND` | Backend email | Console (dev) / SMTP (prod) |
| `EMAIL_HOST` | Serveur SMTP | `smtp.gmail.com` |
| `EMAIL_PORT` | Port SMTP | `587` |
| `EMAIL_HOST_USER` | Adresse email d'envoi | — |
| `EMAIL_HOST_PASSWORD` | Mot de passe SMTP | — |
| `DEFAULT_FROM_EMAIL` | Email expéditeur | `no-reply@efootball-rewards.com` |
| `SITE_URL` | URL publique du site | `http://localhost` |

---

## Résolution de problèmes

### Le conteneur web redémarre en boucle

```bash
docker-compose logs web
```
Causes fréquentes :
- `DB_HOST` mal configuré (mettre `db`, pas `localhost`)
- PostgreSQL pas encore prêt au démarrage → relancer `docker-compose up -d`

### Erreur "unapplied migrations"

```bash
docker-compose exec web python manage.py migrate
```

### Erreur 500 sur le site

```bash
docker-compose logs web | tail -100
```
Chercher la ligne `ERROR` ou `Exception` dans les logs.

### Les fichiers statiques ne s'affichent pas (CSS manquant)

```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart web
```

### Reset complet de la base de données

> **Attention :** supprime toutes les données.

```bash
docker-compose down -v
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py seed_data --clear-missions
```

### Voir la base de données directement

```bash
docker-compose exec db psql -U efootball -d efootball_rewards

# Quelques commandes SQL utiles :
\dt                          -- lister les tables
SELECT * FROM accounts_user; -- voir les utilisateurs
\q                           -- quitter
```

### Port 80 déjà utilisé

Si le port 80 est occupé par un autre programme, modifier `docker-compose.yml` :
```yaml
nginx:
  ports:
    - "8080:80"   # changer 80 par un autre port
```
Puis relancer : `docker-compose up -d`
Le site sera sur **http://localhost:8080**

---

## Structure du projet

```
eFootball-Mobile/
├── accounts/          # Authentification, profils, points, invitations
├── missions/          # Missions et demandes de validation
├── rewards/           # Récompenses et échanges de Coins
├── notifications/     # Système de notifications
├── logs/              # Journal d'activité
├── dashboard/         # Tableaux de bord utilisateur et admin
├── api/               # API REST (JWT)
├── config/            # Settings Django, URLs principales
├── templates/         # Templates HTML
├── static/            # CSS, JS, images
├── docker-compose.yml # Orchestration Docker
├── Dockerfile         # Image Docker
├── requirements.txt   # Dépendances Python
└── .env               # Variables d'environnement (ne pas committer)
```

---

## Fonctionnalités principales

| Fonctionnalité | Description |
|---|---|
| **Missions** | 6 missions réelles (Instagram, profil, streaks, invitations) |
| **Code d'invitation** | Chaque utilisateur a un code EFOOT-XXXX unique |
| **Échanges** | 1000 points = 500 Coins eFootball (validés par admin) |
| **Connexion quotidienne** | +50 pts/jour, bonus de streak |
| **Notifications** | Temps réel pour toutes les actions |
| **Admin panel** | Gestion missions, échanges, demandes, utilisateurs |
| **API REST** | Endpoints JWT pour intégration mobile |

---

## Accès Administrateur

> **CONFIDENTIEL — Ne pas partager ces informations**

| Champ | Valeur |
|---|---|
| **URL panneau admin** | `/admin-panel/` |
| **URL Django admin** | `/admin/` |
| **Email** | `admin@efootball.com` |
| **Mot de passe** | `Admin@eFootball2024!` |
| **Username** | `admin` |

### Créer le compte admin
```bash
python manage.py create_site_admin
# ou avec Docker :
docker compose exec web python manage.py create_site_admin
```

### Vider le catalogue des récompenses
```bash
python manage.py clear_rewards
# ou avec Docker :
docker compose exec web python manage.py clear_rewards
```

### Vérification des comptes utilisateurs
Les utilisateurs doivent faire vérifier leur compte pour accéder aux fonctionnalités.
Le flux est :
1. L'utilisateur clique sur "Vérifier mon compte" dans son tableau de bord
2. L'admin reçoit la demande dans `/admin-panel/verifications/`
3. L'admin copie le code affiché et l'envoie manuellement par email à l'utilisateur
4. L'utilisateur entre le code sur le site
5. L'admin clique "Valider" → le compte est activé
