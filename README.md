# 🏭 Système de Gestion des Lancements - AIC Métallurgie

## Vue d'ensemble

Système complet de gestion des lancements de production développé en Django pour AIC Métallurgie. Cette application permet de gérer efficacement les collaborateurs, ateliers, affaires clients et lancements de production avec un système avancé de permissions et de notifications.

## ✨ Fonctionnalités principales

### 👥 Gestion des collaborateurs
- Système d'authentification personnalisé
- Gestion des rôles et permissions granulaires
- Profils collaborateurs avec historique des rôles
- Interface d'administration avancée

### 🏭 Gestion des ateliers et catégories
- Organisation des ateliers par type (fabrication, assemblage, finition, etc.)
- Classification par catégories de produits/services
- Associations automatiques entre collaborateurs, ateliers et catégories
- Responsables d'atelier

### 💼 Gestion des affaires
- Suivi des projets clients
- Association avec des catégories spécifiques
- Tracking du statut et des échéances
- Calcul de progression automatique

### 🚀 Gestion des lancements
- Création et suivi des ordres de fabrication
- Gestion des poids avec formatage français (débitage/assemblage)
- Statuts de suivi (planifié, en cours, terminé, en attente)
- Associations automatiques lors de la création
- Planning visuel

### 📊 Reporting et analytics
- Tableaux de bord interactifs
- Graphiques de production
- Export CSV/Excel
- Statistiques en temps réel

### 🔔 Système de notifications
- Notifications en temps réel
- Historique des activités système
- Préférences utilisateur
- API AJAX pour mise à jour dynamique

### 🔒 Sécurité et permissions
- Système de rôles modulaire
- Permissions granulaires par module et action
- Templates de rôles prédéfinis
- Import/export de configurations de rôles

## 🛠️ Technologies utilisées

- **Backend** : Django 5.2.4
- **Base de données** : PostgreSQL avec psycopg2
- **Frontend** : Bootstrap 5, JavaScript vanilla, AdminLTE
- **Export** : XlsxWriter, ReportLab
- **Configuration** : python-decouple

## 📋 Prérequis

- Python 3.8+
- PostgreSQL 12+
- Git

## ⚙️ Installation

### 1. Cloner le projet
```bash
git clone <votre-repo>
cd GESTION_LANCEMENTS
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configuration de la base de données

Créer une base de données PostgreSQL :
```sql
CREATE DATABASE lancements;
CREATE USER postgres WITH PASSWORD 'password123';
GRANT ALL PRIVILEGES ON DATABASE lancements TO postgres;
```

### 5. Configuration environnement
Créer un fichier `.env` à la racine :
```env
DB_NAME=lancements
DB_USER=postgres
DB_PASSWORD=password123
DB_HOST=127.0.0.1
DB_PORT=5432
```

### 6. Migrations et données initiales
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py init_permissions
python manage.py create_superuser_with_role
```

### 7. Collecter les fichiers statiques
```bash
python manage.py collectstatic
```

### 8. Lancer le serveur de développement
```bash
python manage.py runserver
```

L'application sera accessible à `http://127.0.0.1:8000/`

## 📁 Structure du projet

```
GESTION_LANCEMENTS/
├── apps/
│   ├── associations/       # Gestion des relations many-to-many
│   ├── ateliers/          # Gestion ateliers et catégories
│   ├── collaborateurs/    # Authentification et utilisateurs
│   ├── core/              # Fonctionnalités centrales (permissions, affaires)
│   ├── lancements/        # Gestion des ordres de fabrication
│   └── reporting/         # Rapports et statistiques
├── gestion_lancements/    # Configuration Django
├── templates/             # Templates HTML organisés par module
├── static/               # Fichiers CSS, JS, images
└── media/               # Uploads utilisateur
```

## 🎯 Utilisation

### Première connexion
1. Accédez à l'application
2. Connectez-vous avec le compte super-administrateur créé
3. Configurez les rôles et permissions
4. Créez les premiers collaborateurs, ateliers et catégories

### Workflow type
1. **Créer les référentiels** : ateliers, catégories, collaborateurs
2. **Configurer les associations** : qui travaille où et sur quoi
3. **Créer les affaires** : projets clients avec catégories associées
4. **Lancer la production** : créer les lancements avec suivi temps réel
5. **Analyser** : consulter rapports et tableaux de bord

### Gestion des permissions
Le système utilise une approche modulaire :
- **Modules** : collaborateurs, ateliers, categories, affaires, lancements, rapports, administration
- **Actions** : create, read, update, delete, assign, export
- **Rôles prédéfinis** : Admin, Manager, Superviseur, Opérateur, Consultation

## 🔧 Commandes de gestion

```bash
# Initialiser les permissions système
python manage.py init_permissions

# Créer un super-utilisateur avec rôle
python manage.py create_superuser_with_role

# Nettoyer les anciennes notifications
python manage.py clean_notifications

# Créer un collaborateur de test
python manage.py create_collaborateur

# Lister toutes les permissions
python manage.py list_permissions

# Créer des données de test
python manage.py create_test_activity
```

## 📊 Fonctionnalités avancées

### Système d'associations automatiques
Lors de la création d'un lancement, le système crée automatiquement les relations :
- Collaborateur ↔ Atelier
- Collaborateur ↔ Catégorie  
- Atelier ↔ Catégorie

### Formatage français des poids
- Support des formats `1 234,567 kg`
- Validation avec 3 décimales maximum
- Interface utilisateur adaptée

### Notifications temps réel
- Notifications push dans l'interface
- Historique complet des activités
- Préférences utilisateur configurables

### Export avancé
- Export CSV avec caractères français
- Génération Excel avec formatage
- Rapports PDF (ReportLab)

## 🔐 Sécurité

- Authentification personnalisée basée sur email
- Hashage sécurisé des mots de passe (Django default)
- Protection CSRF activée
- Validation stricte des formulaires
- Logs des activités utilisateur

## 🚀 Production

### Variables d'environnement supplémentaires
```env
DEBUG=False
SECRET_KEY=votre-cle-secrete-forte
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
```

### Optimisations recommandées
- Serveur web : Nginx + Gunicorn
- Cache : Redis ou Memcached
- Monitoring : Sentry pour les erreurs
- Base de données : PostgreSQL avec optimisations

### Sauvegarde
```bash
# Sauvegarde base de données
pg_dump lancements > backup_$(date +%Y%m%d).sql

# Sauvegarde fichiers media
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/
```

## 🐛 Dépannage

### Problèmes courants

**Erreur de connexion base de données**
- Vérifier les paramètres dans `.env`
- S'assurer que PostgreSQL est démarré
- Vérifier les permissions utilisateur

**Problèmes de permissions**
```bash
python manage.py init_permissions
python manage.py migrate
```

**Fichiers statiques manquants**
```bash
python manage.py collectstatic --clear
```

### Logs de débogage
Les logs sont configurés pour les associations automatiques :
- Consultez la console pour les messages de création d'associations
- Les erreurs sont loggées avec détails

## 📝 Contribution

1. Créer une branche feature : `git checkout -b feature/nouvelle-fonctionnalite`
2. Commiter les changements : `git commit -m 'Ajout nouvelle fonctionnalité'`
3. Pousser vers la branche : `git push origin feature/nouvelle-fonctionnalite`
4. Ouvrir une Pull Request

## 📄 Licence

Projet propriétaire - AIC Métallurgie
Tous droits réservés.

## 🆘 Support

Pour toute question ou problème :
- Consulter le guide technique intégré (`/guide-technique/`)
- Vérifier les logs d'erreur Django
- Contacter l'équipe de développement

---

**Version** : 1.0.0  
**Dernière mise à jour** : Août 2024  
**Développé avec** ❤️ pour AIC Métallurgie