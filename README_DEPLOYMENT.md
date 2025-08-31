# 🚀 Guide de Déploiement - Système de Gestion des Lancements

## Vue d'ensemble

Ce guide vous accompagne dans le déploiement complet de l'application Gestion des Lancements sur les postes de l'entreprise AIC Métallurgie.

## 📦 Package de déploiement

Le package contient tous les éléments nécessaires pour une installation automatisée :

```
deployment-package/
├── GESTION_LANCEMENTS/          # Code source de l'application
├── install.sh                  # Script d'installation Linux/Unix
├── install_windows.bat         # Script d'installation Windows
├── README_DEPLOYMENT.md         # Ce guide
├── requirements.txt            # Dépendances Python
├── backup_restore.sh           # Scripts de sauvegarde/restauration
├── maintenance/                # Scripts de maintenance
│   ├── update_app.sh
│   ├── backup_db.sh
│   └── check_health.sh
└── docs/                      # Documentation technique
    ├── architecture.md
    └── troubleshooting.md
```

## 🛠️ Prérequis système

### Minimum requis
- **CPU**: 2 cœurs
- **RAM**: 4 GB
- **Disque**: 10 GB d'espace libre
- **OS**: 
  - Linux: Ubuntu 18.04+, CentOS 7+, RHEL 7+
  - Windows: Windows 10, Windows Server 2016+
- **Réseau**: Accès internet pour l'installation des dépendances

### Recommandé
- **CPU**: 4 cœurs
- **RAM**: 8 GB
- **Disque**: 50 GB (SSD recommandé)
- **Sauvegarde**: Solution de backup automatisée

## 📋 Instructions d'installation

### 🐧 Installation Linux/Unix

1. **Téléchargez le package** sur le serveur cible
2. **Extrayez les fichiers** :
   ```bash
   tar -xzf gestion-lancements-deploy.tar.gz
   cd gestion-lancements-deploy
   ```
3. **Rendez le script exécutable** :
   ```bash
   chmod +x install.sh
   ```
4. **Exécutez l'installation** :
   ```bash
   sudo ./install.sh
   ```
5. **Suivez les instructions** affichées à l'écran

### 🪟 Installation Windows

1. **Téléchargez le package** et extrayez-le
2. **Ouvrez PowerShell/CMD en tant qu'administrateur**
3. **Naviguez vers le dossier** :
   ```cmd
   cd C:\chemin\vers\gestion-lancements-deploy
   ```
4. **Exécutez l'installation** :
   ```cmd
   install_windows.bat
   ```
5. **Suivez les instructions** affichées

## 🔧 Configuration post-installation

### 1. Vérification des services

**Linux:**
```bash
sudo systemctl status gestion-lancements
sudo systemctl status nginx
sudo systemctl status postgresql
```

**Windows:**
- Vérifiez que PostgreSQL est démarré
- Testez l'accès à l'application via http://localhost:8000

### 2. Configuration réseau

#### Accès depuis d'autres postes
Modifiez la configuration pour permettre l'accès réseau :

**Linux** - Éditez `/etc/nginx/sites-available/gestion-lancements` :
```nginx
server {
    listen 80;
    server_name votre-serveur.local 192.168.1.100;  # Ajoutez votre IP
    # ... reste de la configuration
}
```

**Windows** - Dans `start_server.bat`, remplacez :
```batch
waitress-serve --host=0.0.0.0 --port=8000 gestion_lancements.wsgi:application
```

### 3. Configuration de la base de données

Si besoin de personnaliser la base de données, modifiez `.env` :
```env
DB_NAME=votre_base
DB_USER=votre_utilisateur  
DB_PASSWORD=votre_mot_de_passe
DB_HOST=serveur_db.local
DB_PORT=5432
```

Puis redémarrez l'application.

### 4. Configuration SSL/HTTPS (Production)

Pour sécuriser l'application en production :

**Linux avec Let's Encrypt :**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.com
```

### 5. Sauvegarde automatique

Configurez la sauvegarde automatique avec cron (Linux) :
```bash
sudo crontab -e
# Ajoutez cette ligne pour une sauvegarde quotidienne à 2h
0 2 * * * /opt/gestion-lancements/maintenance/backup_db.sh
```

## 🔐 Sécurité

### Bonnes pratiques
1. **Changez le SECRET_KEY** en production
2. **Limitez ALLOWED_HOSTS** aux domaines autorisés
3. **Configurez un pare-feu** approprié
4. **Mettez à jour régulièrement** le système et les dépendances
5. **Surveillez les logs** d'accès et d'erreur

### Configuration du pare-feu

**Linux (ufw) :**
```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**Windows :**
- Ouvrez le Pare-feu Windows Defender
- Créez une règle d'entrée pour le port 8000

## 📊 Monitoring et maintenance

### Scripts de maintenance inclus

1. **Vérification de santé** :
   ```bash
   ./maintenance/check_health.sh
   ```

2. **Sauvegarde manuelle** :
   ```bash
   ./maintenance/backup_db.sh
   ```

3. **Mise à jour de l'application** :
   ```bash
   ./maintenance/update_app.sh
   ```

### Logs à surveiller

**Linux :**
- Application : `/var/log/gestion-lancements/`
- Nginx : `/var/log/nginx/`
- PostgreSQL : `/var/log/postgresql/`

**Windows :**
- Application : Logs dans la console du serveur
- PostgreSQL : Logs dans le répertoire d'installation PostgreSQL

### Commandes de dépannage

**Redémarrer tous les services (Linux) :**
```bash
sudo systemctl restart postgresql
sudo systemctl restart gestion-lancements  
sudo systemctl restart nginx
```

**Réinitialiser la base de données :**
```bash
cd /opt/gestion-lancements
sudo -u gestion-lancements ./venv_lancements/bin/python manage.py flush
sudo -u gestion-lancements ./venv_lancements/bin/python manage.py migrate
sudo -u gestion-lancements ./venv_lancements/bin/python manage.py init_permissions
```

## 📈 Performance et optimisation

### Optimisations recommandées

1. **Base de données** :
   ```sql
   -- Optimisations PostgreSQL dans postgresql.conf
   shared_buffers = 256MB
   effective_cache_size = 1GB
   work_mem = 4MB
   ```

2. **Cache Redis** (optionnel) :
   ```bash
   sudo apt install redis-server
   pip install django-redis
   ```

3. **Monitoring avec Prometheus** (optionnel) :
   ```bash
   pip install django-prometheus
   ```

### Métriques à surveiller
- Utilisation CPU et mémoire
- Temps de réponse de l'application
- Taille de la base de données
- Espace disque disponible
- Erreurs dans les logs

## 🔄 Sauvegarde et restauration

### Sauvegarde complète

**Script automatique** (inclus dans le package) :
```bash
./maintenance/backup_db.sh
tar -czf backup_complet_$(date +%Y%m%d).tar.gz \
    /opt/gestion-lancements/media \
    /opt/gestion-lancements/.env \
    backup_db_$(date +%Y%m%d).sql
```

### Restauration

1. **Arrêter l'application** :
   ```bash
   sudo systemctl stop gestion-lancements
   ```

2. **Restaurer la base de données** :
   ```bash
   sudo -u postgres psql -d lancements < backup_db_YYYYMMDD.sql
   ```

3. **Restaurer les fichiers media** :
   ```bash
   tar -xzf backup_complet_YYYYMMDD.tar.gz
   ```

4. **Redémarrer l'application** :
   ```bash
   sudo systemctl start gestion-lancements
   ```

## 🌐 Configuration multi-postes

### Architecture recommandée

Pour un déploiement sur plusieurs postes :

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Poste Client 1 │    │  Poste Client 2 │    │  Poste Client N │
│   (Navigateur)  │    │   (Navigateur)  │    │   (Navigateur)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │      Serveur Central        │
                  │  (Application + Base)       │
                  │   IP: 192.168.1.100        │
                  └─────────────────────────────┘
```

### Configuration serveur central

1. **Installez sur le serveur principal** avec les scripts fournis
2. **Modifiez la configuration** pour accepter les connexions externes :
   ```env
   ALLOWED_HOSTS=192.168.1.100,serveur.local,*
   ```
3. **Configurez les postes clients** pour pointer vers le serveur :
   - URL : `http://192.168.1.100`

## ❗ Dépannage courant

### Problèmes fréquents

1. **"Permission denied"** :
   ```bash
   sudo chmod -R 755 /opt/gestion-lancements
   sudo chown -R gestion-lancements:gestion-lancements /opt/gestion-lancements
   ```

2. **Base de données inaccessible** :
   - Vérifiez que PostgreSQL est démarré
   - Contrôlez les paramètres dans `.env`
   - Testez la connexion : `psql -h localhost -U postgres -d lancements`

3. **Page blanche ou erreur 500** :
   - Consultez les logs : `sudo journalctl -u gestion-lancements -f`
   - Vérifiez les permissions des fichiers statiques
   - Relancez `collectstatic` : `python manage.py collectstatic`

4. **Lenteur de l'application** :
   - Vérifiez l'utilisation des ressources : `top`, `htop`
   - Analysez les logs pour identifier les requêtes lentes
   - Optimisez la base de données

### Contacts support

- **Support technique** : support@aic-metallurgie.com
- **Documentation** : `/opt/gestion-lancements/docs/`
- **Logs système** : `sudo journalctl -u gestion-lancements`

## ✅ Checklist de déploiement

### Avant la mise en production

- [ ] Tests de fonctionnalité sur environnement de test
- [ ] Sauvegarde des données existantes
- [ ] Configuration des permissions utilisateurs
- [ ] Test des performances sous charge
- [ ] Configuration SSL/HTTPS
- [ ] Plan de rollback défini

### Après le déploiement

- [ ] Vérification de tous les services
- [ ] Test des fonctionnalités critiques
- [ ] Configuration de la sauvegarde automatique
- [ ] Formation des utilisateurs finaux
- [ ] Documentation des procédures spécifiques
- [ ] Planification de la maintenance

## 📞 Support et maintenance

### Plan de maintenance recommandé

**Quotidien :**
- Vérification des logs d'erreur
- Monitoring des performances

**Hebdomadaire :**
- Sauvegarde complète
- Nettoyage des logs anciens
- Vérification de l'espace disque

**Mensuel :**
- Mise à jour de sécurité système
- Analyse des performances
- Test de restauration

**Trimestriel :**
- Mise à jour de l'application
- Audit de sécurité
- Formation continue des utilisateurs

---

🎯 **Installation réussie = Application opérationnelle en moins de 30 minutes !**

