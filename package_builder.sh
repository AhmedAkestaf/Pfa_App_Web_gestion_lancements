
#!/bin/bash

# =============================================================================
# Script de création du package de déploiement - Gestion des Lancements
# AIC Métallurgie - Version modifiée pour Windows/Git Bash
# =============================================================================

set -e

# Configuration
PROJECT_NAME="GESTION_LANCEMENTS"
VERSION="1.0.0"
PACKAGE_NAME="gestion-lancements-deploy-v${VERSION}"
BUILD_DIR="./build"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERREUR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1 ${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Vérifier les prérequis
check_prerequisites() {
    print_header "VÉRIFICATION DES PRÉREQUIS"
    
    # Vérifier que nous sommes dans le bon répertoire
    if [ ! -f "manage.py" ] && [ ! -d "$PROJECT_NAME" ]; then
        print_error "Ce script doit être exécuté depuis le répertoire racine du projet Django"
        print_error "Le fichier manage.py ou le répertoire $PROJECT_NAME doit être présent"
        exit 1
    fi
    
    # Vérifier les outils nécessaires (version Windows compatible)
    if command -v tar &> /dev/null; then
        print_message "tar trouvé"
    else
        print_warning "tar non trouvé, utilisation d'alternatives"
    fi
    
    if command -v zip &> /dev/null; then
        print_message "zip trouvé"
    else
        print_warning "zip non trouvé, seule l'archive tar sera créée"
    fi
    
    print_message "✅ Prérequis validés"
}

# Nettoyer et créer les répertoires
prepare_directories() {
    print_header "PRÉPARATION DES RÉPERTOIRES"
    
    # Nettoyer l'ancien build
    if [ -d "$BUILD_DIR" ]; then
        print_message "Suppression de l'ancien build..."
        rm -rf "$BUILD_DIR"
    fi
    
    # Créer la structure
    mkdir -p "$PACKAGE_DIR"
    mkdir -p "$PACKAGE_DIR/scripts"
    mkdir -p "$PACKAGE_DIR/docs"
    mkdir -p "$PACKAGE_DIR/maintenance"
    mkdir -p "$PACKAGE_DIR/configs"
    
    print_message "✅ Répertoires préparés"
}

# Fonction pour copier en excluant certains fichiers/dossiers
copy_with_exclusions() {
    local src="$1"
    local dest="$2"
    
    # Créer le répertoire de destination
    mkdir -p "$dest"
    
    # Liste des exclusions
    local exclude_patterns=(
        "*.pyc"
        "__pycache__"
        ".git"
        ".gitignore"
        "*.log"
        "db.sqlite3"
        "venv*"
        "env"
        "*.env"
        "staticfiles"
        "media"
        "build"
        "dist"
        "*.egg-info"
        "node_modules"
        ".DS_Store"
        "Thumbs.db"
    )
    
    print_message "Copie des fichiers depuis $src vers $dest..."
    
    # Fonction récursive pour copier avec exclusions
    copy_recursive() {
        local current_src="$1"
        local current_dest="$2"
        
        for item in "$current_src"/*; do
            # Vérifier si le fichier/dossier existe
            if [ ! -e "$item" ]; then
                continue
            fi
            
            local basename_item=$(basename "$item")
            local should_exclude=false
            
            # Vérifier les exclusions
            for pattern in "${exclude_patterns[@]}"; do
                case "$basename_item" in
                    $pattern)
                        should_exclude=true
                        break
                        ;;
                esac
            done
            
            if [ "$should_exclude" = false ]; then
                if [ -d "$item" ]; then
                    # C'est un dossier
                    mkdir -p "$current_dest/$basename_item"
                    copy_recursive "$item" "$current_dest/$basename_item"
                else
                    # C'est un fichier
                    cp "$item" "$current_dest/$basename_item"
                fi
            fi
        done
    }
    
    copy_recursive "$src" "$dest"
}

# Copier le code source
copy_source_code() {
    print_header "COPIE DU CODE SOURCE"
    
    if [ -f "manage.py" ]; then
        # Nous sommes directement dans le projet
        print_message "Copie depuis le répertoire courant..."
        copy_with_exclusions "." "$PACKAGE_DIR/$PROJECT_NAME"
            
    elif [ -d "$PROJECT_NAME" ]; then
        # Le projet est dans un sous-répertoire
        print_message "Copie depuis $PROJECT_NAME/..."
        copy_with_exclusions "$PROJECT_NAME" "$PACKAGE_DIR/$PROJECT_NAME"
    fi
    
    print_message "✅ Code source copié"
}

# Créer les scripts d'installation
create_installation_scripts() {
    print_header "CRÉATION DES SCRIPTS D'INSTALLATION"
    
    # Script d'installation Linux
    print_message "Création du script d'installation Linux..."
    cat > "$PACKAGE_DIR/install.sh" <<'EOF'
#!/bin/bash

# Script d'installation automatique - Gestion des Lancements
# AIC Métallurgie

set -e

# Configuration
PROJECT_NAME="GESTION_LANCEMENTS"
INSTALL_DIR="/opt/gestion-lancements"
SERVICE_USER="gestion-lancements"
DB_NAME="gestion_lancements_aic"
DB_USER="aic_user"
VENV_NAME="venv_lancements"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERREUR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1 ${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Vérifier les privilèges root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Ce script doit être exécuté en tant que root"
        print_message "Utilisez: sudo $0"
        exit 1
    fi
}

# Installation des dépendances système
install_dependencies() {
    print_header "INSTALLATION DES DÉPENDANCES"
    
    # Détecter la distribution
    if [ -f /etc/debian_version ]; then
        # Ubuntu/Debian
        print_message "Distribution Debian/Ubuntu détectée"
        apt update
        apt install -y python3 python3-pip python3-venv python3-dev \
                      postgresql postgresql-contrib nginx git curl \
                      build-essential libpq-dev
    elif [ -f /etc/redhat-release ]; then
        # CentOS/RHEL/Fedora
        print_message "Distribution RedHat/CentOS/Fedora détectée"
        yum update -y
        yum install -y python3 python3-pip python3-devel postgresql \
                      postgresql-server postgresql-contrib nginx git curl \
                      gcc gcc-c++ make libpq-devel
    else
        print_warning "Distribution non reconnue, installation manuelle requise"
    fi
}

# Configuration de PostgreSQL
setup_database() {
    print_header "CONFIGURATION DE LA BASE DE DONNÉES"
    
    # Démarrer PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Créer l'utilisateur et la base de données
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD 'password123';" || true
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" || true
    
    print_message "✅ Base de données configurée"
}

# Créer l'utilisateur système
create_system_user() {
    print_header "CRÉATION DE L'UTILISATEUR SYSTÈME"
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$INSTALL_DIR" "$SERVICE_USER"
        print_message "Utilisateur $SERVICE_USER créé"
    else
        print_message "Utilisateur $SERVICE_USER existe déjà"
    fi
}

# Installation de l'application
install_application() {
    print_header "INSTALLATION DE L'APPLICATION"
    
    # Créer le répertoire d'installation
    mkdir -p "$INSTALL_DIR"
    
    # Copier les fichiers
    cp -r "$PROJECT_NAME"/* "$INSTALL_DIR/"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    # Créer l'environnement virtuel
    print_message "Création de l'environnement virtuel..."
    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/$VENV_NAME"
    
    # Installer les dépendances Python
    print_message "Installation des dépendances Python..."
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/$VENV_NAME/bin/pip" install --upgrade pip
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/$VENV_NAME/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/$VENV_NAME/bin/pip" install gunicorn
    
    print_message "✅ Application installée"
}

# Configuration Django
configure_django() {
    print_header "CONFIGURATION DJANGO"
    
    # Créer le fichier .env
    cat > "$INSTALL_DIR/.env" <<ENV_EOF
DEBUG=False
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=password123
DB_HOST=127.0.0.1
DB_PORT=5432
STATIC_ROOT=$INSTALL_DIR/staticfiles
MEDIA_ROOT=$INSTALL_DIR/media
ENV_EOF
    
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
    
    # Exécuter les migrations
    print_message "Exécution des migrations Django..."
    cd "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/$VENV_NAME/bin/python" manage.py migrate
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/$VENV_NAME/bin/python" manage.py collectstatic --noinput
    
    print_message "✅ Django configuré"
}

# Configuration du service systemd
setup_systemd_service() {
    print_header "CONFIGURATION DU SERVICE SYSTEMD"
    
    cp configs/gestion-lancements.service /etc/systemd/system/
    
    systemctl daemon-reload
    systemctl enable gestion-lancements
    
    print_message "✅ Service systemd configuré"
}

# Configuration Nginx
setup_nginx() {
    print_header "CONFIGURATION NGINX"
    
    # Copier la configuration
    cp configs/nginx.conf /etc/nginx/sites-available/gestion-lancements
    ln -sf /etc/nginx/sites-available/gestion-lancements /etc/nginx/sites-enabled/
    
    # Supprimer la configuration par défaut
    rm -f /etc/nginx/sites-enabled/default
    
    # Tester la configuration
    nginx -t
    
    systemctl restart nginx
    systemctl enable nginx
    
    print_message "✅ Nginx configuré"
}

# Créer les répertoires de logs
setup_logging() {
    print_header "CONFIGURATION DES LOGS"
    
    mkdir -p /var/log/gestion-lancements
    chown "$SERVICE_USER:$SERVICE_USER" /var/log/gestion-lancements
    
    print_message "✅ Logging configuré"
}

# Démarrer les services
start_services() {
    print_header "DÉMARRAGE DES SERVICES"
    
    systemctl start gestion-lancements
    systemctl start nginx
    
    print_message "✅ Services démarrés"
}

# Vérification finale
final_check() {
    print_header "VÉRIFICATION FINALE"
    
    sleep 5
    
    if systemctl is-active --quiet gestion-lancements; then
        print_message "✅ Service gestion-lancements: Actif"
    else
        print_error "❌ Service gestion-lancements: Inactif"
    fi
    
    if systemctl is-active --quiet nginx; then
        print_message "✅ Service nginx: Actif"
    else
        print_error "❌ Service nginx: Inactif"
    fi
    
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
        print_message "✅ Application accessible sur http://localhost"
    else
        print_warning "⚠️  Application non accessible, vérifiez les logs"
    fi
}

# Script principal
main() {
    print_header "INSTALLATION - GESTION DES LANCEMENTS"
    
    check_root
    install_dependencies
    setup_database
    create_system_user
    install_application
    configure_django
    setup_systemd_service
    setup_nginx
    setup_logging
    start_services
    final_check
    
    print_header "INSTALLATION TERMINÉE"
    print_message "🚀 Application disponible sur: http://localhost"
    print_message "📁 Répertoire: $INSTALL_DIR"
    print_message "👤 Utilisateur: $SERVICE_USER"
    print_message "📊 Logs: /var/log/gestion-lancements/"
    
    echo ""
    print_message "Commandes utiles:"
    echo "  sudo systemctl status gestion-lancements"
    echo "  sudo systemctl restart gestion-lancements"
    echo "  sudo journalctl -u gestion-lancements -f"
    echo "  ./maintenance/backup_restore.sh backup"
}

main "$@"
EOF
    
    # Script d'installation Windows
    print_message "Création du script d'installation Windows..."
    cat > "$PACKAGE_DIR/install_windows.bat" <<'EOF'
@echo off
echo ========================================
echo Installation - Gestion des Lancements
echo AIC Metallurgie
echo ========================================

REM Vérifier les privilèges administrateur
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERREUR: Ce script doit être execute en tant qu'administrateur
    echo Clic droit sur le fichier et "Executer en tant qu'administrateur"
    pause
    exit /b 1
)

echo.
echo [INFO] Verification de Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERREUR: Python n'est pas installe ou non trouve dans le PATH
    echo Installez Python depuis https://python.org
    echo N'oubliez pas de cocher "Add Python to PATH"
    pause
    exit /b 1
) else (
    echo [INFO] Python trouve
)

echo.
echo [INFO] Verification de PostgreSQL...
where psql >nul 2>&1
if %errorLevel% neq 0 (
    echo ERREUR: PostgreSQL non trouve
    echo Installez PostgreSQL depuis https://postgresql.org
    pause
    exit /b 1
) else (
    echo [INFO] PostgreSQL trouve
)

echo.
echo [INFO] Creation du repertoire d'installation...
set INSTALL_DIR=C:\gestion-lancements
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo.
echo [INFO] Copie des fichiers...
xcopy /E /I /H /Y "GESTION_LANCEMENTS\*" "%INSTALL_DIR%\"

echo.
echo [INFO] Creation de l'environnement virtuel...
cd /d "%INSTALL_DIR%"
python -m venv venv_lancements

echo.
echo [INFO] Activation de l'environnement virtuel...
call venv_lancements\Scripts\activate.bat

echo.
echo [INFO] Installation des dependances...
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

echo.
echo [INFO] Configuration de la base de donnees...
echo Veuillez creer manuellement:
echo 1. Une base de donnees 'gestion_lancements_aic'
echo 2. Un utilisateur PostgreSQL avec les droits
echo.
pause

echo.
echo [INFO] Configuration Django...
copy configs\env.example .env
echo Editez le fichier .env avec vos parametres de base de donnees
pause

echo.
echo [INFO] Execution des migrations...
python manage.py migrate
python manage.py collectstatic --noinput

echo.
echo [INFO] Creation d'un superutilisateur...
python manage.py createsuperuser

echo.
echo ========================================
echo Installation terminee !
echo ========================================
echo.
echo Pour demarrer l'application:
echo 1. cd C:\gestion-lancements
echo 2. venv_lancements\Scripts\activate.bat  
echo 3. python manage.py runserver
echo.
echo Application disponible sur: http://127.0.0.1:8000
echo.
pause
EOF
    
    # Rendre les scripts exécutables (si possible)
    chmod +x "$PACKAGE_DIR/install.sh" 2>/dev/null || true
    
    print_message "✅ Scripts d'installation créés"
}

# Créer la documentation
create_documentation() {
    print_header "CRÉATION DE LA DOCUMENTATION"
    
    # README principal
    cat > "$PACKAGE_DIR/README.md" <<'EOF'
# 🚀 Package de Déploiement - Gestion des Lancements

## Installation Rapide

### Linux/Unix
```bash
chmod +x install.sh
sudo ./install.sh
```

### Windows
```cmd
# Exécuter en tant qu'administrateur
install_windows.bat
```

## Contenu du Package

- `GESTION_LANCEMENTS/` : Code source de l'application
- `install.sh` : Script d'installation Linux/Unix
- `install_windows.bat` : Script d'installation Windows  
- `maintenance/` : Scripts de maintenance et sauvegarde
- `docs/` : Documentation complète
- `configs/` : Fichiers de configuration

## Support

Consultez `docs/README_DEPLOYMENT.md` pour le guide complet.
EOF

    # Guide de déploiement complet
    cat > "$PACKAGE_DIR/docs/README_DEPLOYMENT.md" <<'EOF'
# 📋 Guide de Déploiement Complet
## Gestion des Lancements - AIC Métallurgie

### Prérequis Système

#### Minimum
- **OS**: Ubuntu 18.04+, CentOS 7+, Windows 10+
- **RAM**: 4 GB (8 GB recommandé)
- **Disque**: 10 GB libre
- **Réseau**: Accès Internet pour l'installation

#### Logiciels Requis
- Python 3.8+
- PostgreSQL 12+
- Nginx (Linux) / IIS (Windows)

### Installation Automatique

#### Linux
```bash
# Extraire le package
tar -xzf gestion-lancements-deploy-v1.0.0.tar.gz
cd gestion-lancements-deploy-v1.0.0

# Installation complète
chmod +x install.sh
sudo ./install.sh
```

#### Windows
```cmd
# Extraire le package ZIP
# Exécuter en tant qu'administrateur:
install_windows.bat
```

### Configuration Post-Installation

#### 1. Vérification des Services
```bash
# Linux
sudo systemctl status gestion-lancements
sudo systemctl status nginx
sudo systemctl status postgresql

# Logs
sudo journalctl -u gestion-lancements -f
```

#### 2. Accès Application
- URL: http://localhost
- Admin: http://localhost/admin/

#### 3. Création du Premier Utilisateur
```bash
cd /opt/gestion-lancements
source venv_lancements/bin/activate
python manage.py createsuperuser
```

### Maintenance

#### Sauvegarde
```bash
./maintenance/backup_restore.sh backup
```

#### Restauration
```bash
./maintenance/backup_restore.sh restore backup_YYYYMMDD_HHMMSS.tar.gz
```

#### Mise à Jour
```bash
./maintenance/update_app.sh
```

#### Surveillance
```bash
./maintenance/check_health.sh
```

### Dépannage

#### Application Inaccessible
1. Vérifier les services
2. Consulter les logs
3. Vérifier la configuration nginx
4. Tester la connectivité base de données

#### Performance Lente
1. Vérifier l'utilisation RAM/CPU
2. Analyser les logs Gunicorn
3. Optimiser les requêtes Django
4. Nettoyer les logs anciens

### Configuration Avancée

#### Variables d'Environnement
Fichier `.env`:
```
DEBUG=False
SECRET_KEY=votre-cle-secrete
ALLOWED_HOSTS=localhost,votre-domaine.com
DB_NAME=gestion_lancements_aic
DB_USER=aic_user
DB_PASSWORD=mot-de-passe-securise
```

#### SSL/HTTPS
```bash
# Génération certificat Let's Encrypt
./scripts/setup_ssl.sh votre-domaine.com
```

### Support
- Documentation: docs/
- Logs: /var/log/gestion-lancements/
- Contact: support@aic-metallurgie.com
EOF

    # Guide de dépannage
    cat > "$PACKAGE_DIR/docs/TROUBLESHOOTING.md" <<'EOF'
# 🔧 Guide de Dépannage

## Problèmes Courants

### Installation

#### "Permission denied"
```bash
chmod +x install.sh
sudo ./install.sh
```

#### PostgreSQL non trouvé
- Installez PostgreSQL depuis le site officiel
- Ajoutez le répertoire bin au PATH
- Redémarrez le terminal

#### Python non trouvé
- Installez Python 3.8+ depuis python.org
- Cochez "Add Python to PATH" lors de l'installation

### Après Installation

#### Service non démarré
```bash
sudo systemctl status gestion-lancements
sudo journalctl -u gestion-lancements -f
```

#### Base de données inaccessible
```bash
sudo systemctl status postgresql
sudo -u postgres psql -l
```

#### Page web inaccessible
- Vérifiez que nginx est démarré
- Vérifiez les logs : `/var/log/nginx/error.log`
- Testez la connectivité : `curl http://localhost`

## Logs Importants

- Application : `/var/log/gestion-lancements/`
- Nginx : `/var/log/nginx/`
- PostgreSQL : `/var/log/postgresql/`

## Commandes Utiles

```bash
# Redémarrer tous les services
sudo systemctl restart postgresql gestion-lancements nginx

# Vérifier la santé du système
./maintenance/check_health.sh

# Sauvegarde manuelle
./maintenance/backup_restore.sh backup

# Voir les logs en temps réel
sudo journalctl -u gestion-lancements -f
```
EOF

    print_message "✅ Documentation créée"
}

# Créer les fichiers de configuration
create_config_files() {
    print_header "CRÉATION DES FICHIERS DE CONFIGURATION"
    
    # Configuration environnement par défaut
    cat > "$PACKAGE_DIR/configs/env.example" <<'EOF'
# Configuration de production
DEBUG=False
SECRET_KEY=CHANGEZ-CETTE-CLE-EN-PRODUCTION
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données
DB_NAME=gestion_lancements_aic
DB_USER=aic_user
DB_PASSWORD=password123
DB_HOST=127.0.0.1
DB_PORT=5432

# Paths
STATIC_ROOT=/opt/gestion-lancements/staticfiles
MEDIA_ROOT=/opt/gestion-lancements/media
EOF

    # Configuration Nginx exemple
    cat > "$PACKAGE_DIR/configs/nginx.conf" <<'EOF'
server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 50M;
    
    location /static/ {
        alias /opt/gestion-lancements/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /opt/gestion-lancements/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30;
        proxy_send_timeout 30;
        proxy_read_timeout 30;
    }
}
EOF

    # Configuration systemd service
    cat > "$PACKAGE_DIR/configs/gestion-lancements.service" <<'EOF'
[Unit]
Description=Gestion Lancements Django Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=forking
User=gestion-lancements
Group=gestion-lancements
WorkingDirectory=/opt/gestion-lancements
Environment=PATH=/opt/gestion-lancements/venv_lancements/bin
ExecStart=/opt/gestion-lancements/venv_lancements/bin/gunicorn gestion_lancements.wsgi:application -c /opt/gestion-lancements/gunicorn_config.py --daemon
ExecReload=/bin/kill -s HUP $MAINPID
PIDFile=/opt/gestion-lancements/gunicorn.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Configuration Gunicorn
    cat > "$PACKAGE_DIR/configs/gunicorn_config.py" <<'EOF'
# Configuration Gunicorn pour production
import multiprocessing

# Serveur
bind = "127.0.0.1:8000"
backlog = 2048

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Redémarrage automatique
preload_app = True
reload = False

# Logging
accesslog = "/var/log/gestion-lancements/gunicorn_access.log"
errorlog = "/var/log/gestion-lancements/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process
user = "gestion-lancements"
group = "gestion-lancements"
pidfile = "/opt/gestion-lancements/gunicorn.pid"
chdir = "/opt/gestion-lancements"

# Sécurité
umask = 0
tmp_upload_dir = None
EOF

    print_message "✅ Fichiers de configuration créés"
}

# Créer les scripts de maintenance
create_maintenance_scripts() {
    print_header "CRÉATION DES SCRIPTS DE MAINTENANCE"
    
    # Script de sauvegarde/restauration
    cat > "$PACKAGE_DIR/maintenance/backup_restore.sh" <<'EOF'
#!/bin/bash

# Script de sauvegarde et restauration
INSTALL_DIR="/opt/gestion-lancements"
BACKUP_DIR="/opt/backups/gestion-lancements"
DB_NAME="gestion_lancements_aic"
DB_USER="aic_user"
SERVICE_NAME="gestion-lancements"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_message() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[ATTENTION]${NC} $1"; }
print_error() { echo -e "${RED}[ERREUR]${NC} $1"; }

# Créer une sauvegarde
backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/backup_${timestamp}.tar.gz"
    
    print_message "Création de la sauvegarde..."
    mkdir -p "$BACKUP_DIR"
    
    # Arrêter le service temporairement
    systemctl stop "$SERVICE_NAME"
    
    # Sauvegarde de la base de données
    sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_DIR/db_${timestamp}.sql"
    
    # Sauvegarde des fichiers
    tar -czf "$backup_file" \
        -C "$(dirname "$INSTALL_DIR")" \
        "$(basename "$INSTALL_DIR")" \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        --exclude="*.log" \
        --exclude="venv_lancements"
    
    # Ajouter la sauvegarde DB à l'archive
    tar -rf "${backup_file%.gz}" -C "$BACKUP_DIR" "db_${timestamp}.sql"
    gzip "${backup_file%.gz}"
    
    # Redémarrer le service
    systemctl start "$SERVICE_NAME"
    
    # Nettoyer les anciennes sauvegardes (garder 7 dernières)
    ls -t "$BACKUP_DIR"/backup_*.tar.gz | tail -n +8 | xargs -r rm
    
    print_message "✅ Sauvegarde créée: $backup_file"
}

# Restaurer une sauvegarde
restore() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Fichier de sauvegarde non trouvé: $backup_file"
        return 1
    fi
    
    print_warning "ATTENTION: Cette opération va écraser l'installation actuelle"
    read -p "Continuer? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_message "Restauration annulée"
        return 0
    fi
    
    print_message "Restauration depuis: $backup_file"
    
    # Arrêter les services
    systemctl stop "$SERVICE_NAME"
    systemctl stop nginx
    
    # Extraire la sauvegarde
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"
    
    # Restaurer la base de données
    local db_file=$(find "$temp_dir" -name "db_*.sql" | head -1)
    if [ -f "$db_file" ]; then
        print_message "Restauration de la base de données..."
        sudo -u postgres psql -d "$DB_NAME" < "$db_file"
    fi
    
    # Restaurer les fichiers
    print_message "Restauration des fichiers..."
    rm -rf "$INSTALL_DIR.backup" 2>/dev/null || true
    mv "$INSTALL_DIR" "$INSTALL_DIR.backup" 2>/dev/null || true
    mv "$temp_dir/$(basename "$INSTALL_DIR")" "$INSTALL_DIR"
    
    # Restaurer les permissions
    chown -R gestion-lancements:gestion-lancements "$INSTALL_DIR"
    
    # Redémarrer les services
    systemctl start "$SERVICE_NAME"
    systemctl start nginx
    
    # Nettoyer
    rm -rf "$temp_dir"
    
    print_message "✅ Restauration terminée"
}

# Vérifier la santé du système
health() {
    print_message "=== VÉRIFICATION DE SANTÉ ==="
    
    # Services
    for service in postgresql "$SERVICE_NAME" nginx; do
        if systemctl is-active --quiet "$service"; then
            print_message "✅ $service: Actif"
        else
            print_error "❌ $service: Inactif"
        fi
    done
    
    # Espace disque
    local usage=$(df "$INSTALL_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$usage" -lt 80 ]; then
        print_message "✅ Espace disque: ${usage}% utilisé"
    else
        print_warning "⚠️  Espace disque critique: ${usage}% utilisé"
    fi
    
    # Connectivité
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
        print_message "✅ Application accessible"
    else
        print_error "❌ Application inaccessible"
    fi
    
    print_message "=== FIN DE LA VÉRIFICATION ==="
}

# Usage
case "$1" in
    backup)
        backup
        ;;
    restore)
        restore "$2"
        ;;
    health)
        health
        ;;
    *)
        echo "Usage: $0 {backup|restore <fichier>|health}"
        echo "  backup                    Créer une sauvegarde"
        echo "  restore <fichier>         Restaurer une sauvegarde"
        echo "  health                    Vérifier la santé du système"
        ;;
esac
EOF

    # Script de mise à jour
    cat > "$PACKAGE_DIR/maintenance/update_app.sh" <<'EOF'
#!/bin/bash

# Script de mise à jour automatique
INSTALL_DIR="/opt/gestion-lancements"
SERVICE_NAME="gestion-lancements"
SERVICE_USER="gestion-lancements"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_message() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[ATTENTION]${NC} $1"; }
print_error() { echo -e "${RED}[ERREUR]${NC} $1"; }

update_application() {
    print_message "=== MISE À JOUR DE L'APPLICATION ==="
    
    # Vérifier les prérequis
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Application non trouvée dans $INSTALL_DIR"
        exit 1
    fi
    
    # Sauvegarde automatique avant mise à jour
    print_message "Création d'une sauvegarde de sécurité..."
    ./backup_restore.sh backup
    
    # Arrêter le service
    print_message "Arrêt du service..."
    systemctl stop "$SERVICE_NAME"
    
    # Mise à jour des dépendances
    print_message "Mise à jour des dépendances Python..."
    cd "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" venv_lancements/bin/pip install --upgrade pip
    sudo -u "$SERVICE_USER" venv_lancements/bin/pip install -r requirements.txt --upgrade
    
    # Exécuter les migrations
    print_message "Exécution des migrations..."
    sudo -u "$SERVICE_USER" venv_lancements/bin/python manage.py migrate
    
    # Collecter les fichiers statiques
    print_message "Collection des fichiers statiques..."
    sudo -u "$SERVICE_USER" venv_lancements/bin/python manage.py collectstatic --noinput
    
    # Redémarrer le service
    print_message "Redémarrage du service..."
    systemctl start "$SERVICE_NAME"
    
    # Vérification
    sleep 5
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_message "✅ Mise à jour terminée avec succès"
    else
        print_error "❌ Problème lors du redémarrage, restauration de la sauvegarde..."
        # Ici on pourrait automatiquement restaurer la dernière sauvegarde
    fi
}

update_application
EOF

    # Script de vérification de santé
    cat > "$PACKAGE_DIR/maintenance/check_health.sh" <<'EOF'
#!/bin/bash

# Script de vérification de santé
INSTALL_DIR="/opt/gestion-lancements"
SERVICE_NAME="gestion-lancements"

echo "=== VÉRIFICATION DE SANTÉ - $(date) ==="

# Vérifier les services
echo "Services:"
for service in postgresql "$SERVICE_NAME" nginx; do
    if systemctl is-active --quiet "$service"; then
        echo "  ✅ $service: Actif"
    else
        echo "  ❌ $service: Inactif"
    fi
done

# Vérifier l'espace disque
echo -e "\nEspace disque:"
df -h "$INSTALL_DIR" | awk 'NR==2 {printf "  Utilisation: %s/%s (%s)\n", $3, $2, $5}'

# Vérifier la mémoire
echo -e "\nMémoire:"
free -h | awk '/^Mem:/ {printf "  RAM: %s/%s utilisée\n", $3, $2}'

# Test de connectivité
echo -e "\nConnectivité:"
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo "  ✅ Application web accessible"
else
    echo "  ❌ Application web inaccessible"
fi

echo -e "\n=== FIN DE LA VÉRIFICATION ==="
EOF

    # Script de nettoyage des logs
    cat > "$PACKAGE_DIR/maintenance/cleanup_logs.sh" <<'EOF'
#!/bin/bash

# Script de nettoyage des logs
LOG_DIRS=(
    "/var/log/gestion-lancements"
    "/var/log/nginx"
    "/opt/gestion-lancements/logs"
)

RETENTION_DAYS=30

echo "=== NETTOYAGE DES LOGS - $(date) ==="

for log_dir in "${LOG_DIRS[@]}"; do
    if [ -d "$log_dir" ]; then
        echo "Nettoyage de $log_dir..."
        find "$log_dir" -name "*.log" -mtime +$RETENTION_DAYS -delete
        find "$log_dir" -name "*.log.*" -mtime +$RETENTION_DAYS -delete
    fi
done

# Rotation manuelle des logs volumineux
if [ -f "/var/log/gestion-lancements/gunicorn_access.log" ]; then
    size=$(du -m "/var/log/gestion-lancements/gunicorn_access.log" | cut -f1)
    if [ "$size" -gt 100 ]; then
        echo "Rotation du log d'accès Gunicorn (${size}MB)..."
        mv "/var/log/gestion-lancements/gunicorn_access.log" "/var/log/gestion-lancements/gunicorn_access.log.$(date +%Y%m%d)"
        systemctl reload gestion-lancements
    fi
fi

echo "=== NETTOYAGE TERMINÉ ==="
EOF

    # Script de monitoring
    cat > "$PACKAGE_DIR/maintenance/monitor.sh" <<'EOF'
#!/bin/bash

# Script de monitoring simple
INSTALL_DIR="/opt/gestion-lancements"
SERVICE_NAME="gestion-lancements"
ALERT_EMAIL=""  # Configurer si nécessaire

check_service() {
    local service=$1
    if ! systemctl is-active --quiet "$service"; then
        echo "ALERTE: Service $service arrêté à $(date)"
        systemctl restart "$service"
        if [ -n "$ALERT_EMAIL" ]; then
            echo "Service $service redémarré automatiquement" | mail -s "Alerte Gestion Lancements" "$ALERT_EMAIL"
        fi
    fi
}

check_disk_space() {
    local usage=$(df "$INSTALL_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$usage" -gt 85 ]; then
        echo "ALERTE: Espace disque critique: ${usage}% utilisé"
        if [ -n "$ALERT_EMAIL" ]; then
            echo "Espace disque critique: ${usage}% utilisé" | mail -s "Alerte Espace Disque" "$ALERT_EMAIL"
        fi
    fi
}

# Exécuter les vérifications
check_service postgresql
check_service "$SERVICE_NAME"  
check_service nginx
check_disk_space
EOF

    # Rendre les scripts exécutables
    chmod +x "$PACKAGE_DIR/maintenance"/*.sh 2>/dev/null || true
    
    print_message "✅ Scripts de maintenance créés"
}

# Créer le manifeste du package
create_manifest() {
    print_header "CRÉATION DU MANIFESTE"
    
    cat > "$PACKAGE_DIR/MANIFEST.txt" <<EOF
PACKAGE DE DÉPLOIEMENT - GESTION DES LANCEMENTS
==============================================

Version: $VERSION
Date de création: $(date)
Créé par: $(whoami)
Système: $(uname -a)

CONTENU DU PACKAGE:
==================

📁 $PROJECT_NAME/
   └── Code source complet de l'application Django

📁 scripts/
   ├── install.sh              # Installation automatique Linux/Unix
   ├── install_windows.bat     # Installation automatique Windows
   └── setup_ssl.sh            # Configuration SSL (optionnel)

📁 maintenance/
   ├── backup_restore.sh       # Sauvegarde et restauration
   ├── update_app.sh          # Mise à jour automatique
   ├── check_health.sh        # Vérification de santé
   ├── cleanup_logs.sh        # Nettoyage des logs
   └── monitor.sh             # Monitoring basique

📁 configs/
   ├── env.example            # Configuration environnement
   ├── nginx.conf             # Configuration Nginx
   ├── gunicorn_config.py     # Configuration Gunicorn
   └── gestion-lancements.service # Service systemd

📁 docs/
   ├── README_DEPLOYMENT.md   # Guide de déploiement complet
   ├── TROUBLESHOOTING.md     # Guide de dépannage
   └── ARCHITECTURE.md        # Documentation architecture

📄 README.md                  # Instructions rapides
📄 MANIFEST.txt              # Ce fichier

INSTALLATION RAPIDE:
===================

Linux/Unix:
  chmod +x install.sh && sudo ./install.sh

Windows:
  Exécuter install_windows.bat en tant qu'administrateur

PRÉREQUIS:
=========

- Python 3.8+
- PostgreSQL 12+
- 4 GB RAM (8 GB recommandé)
- 10 GB espace disque

SUPPORT:
========

Documentation complète: docs/README_DEPLOYMENT.md
Dépannage: docs/TROUBLESHOOTING.md
Contact: support@aic-metallurgie.com

AIC Métallurgie - Tous droits réservés
EOF

    print_message "✅ Manifeste créé"
}

# Calculer les checksums
generate_checksums() {
    print_header "GÉNÉRATION DES CHECKSUMS"
    
    cd "$PACKAGE_DIR"
    
    # Générer les checksums MD5 (si md5sum est disponible)
    if command -v md5sum >/dev/null 2>&1; then
        find . -type f -exec md5sum {} \; > checksums.md5
    elif command -v md5 >/dev/null 2>&1; then
        # macOS/BSD version
        find . -type f -exec md5 {} \; > checksums.md5
    fi
    
    # Générer les checksums SHA256 (si sha256sum est disponible)
    if command -v sha256sum >/dev/null 2>&1; then
        find . -type f -exec sha256sum {} \; > checksums.sha256
    elif command -v shasum >/dev/null 2>&1; then
        # macOS version
        find . -type f -exec shasum -a 256 {} \; > checksums.sha256
    fi
    
    print_message "✅ Checksums générés"
    cd - > /dev/null
}

# Créer les archives
create_archives() {
    print_header "CRÉATION DES ARCHIVES"
    
    cd "$BUILD_DIR"
    
    # Archive tar.gz (Linux) - si tar est disponible
    if command -v tar >/dev/null 2>&1; then
        print_message "Création de l'archive tar.gz..."
        tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME/"
        
        # Calculer la taille
        if command -v du >/dev/null 2>&1; then
            local tar_size=$(du -h "${PACKAGE_NAME}.tar.gz" 2>/dev/null | cut -f1 || echo "N/A")
            print_message "✅ Archive tar.gz créée (${tar_size})"
        else
            print_message "✅ Archive tar.gz créée"
        fi
    else
        print_warning "tar non disponible, archive tar.gz non créée"
    fi
    
    # Archive zip (Windows) - si zip est disponible
    if command -v zip >/dev/null 2>&1; then
        print_message "Création de l'archive zip..."
        zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME/" > /dev/null 2>&1
        
        # Calculer la taille
        if command -v du >/dev/null 2>&1; then
            local zip_size=$(du -h "${PACKAGE_NAME}.zip" 2>/dev/null | cut -f1 || echo "N/A")
            print_message "✅ Archive zip créée (${zip_size})"
        else
            print_message "✅ Archive zip créée"
        fi
    else
        print_warning "zip non disponible, archive zip non créée"
    fi
    
    cd - > /dev/null
}

# Validation finale
validate_package() {
    print_header "VALIDATION DU PACKAGE"
    
    local issues=0
    
    # Vérifier la présence des fichiers essentiels
    essential_files=(
        "$PACKAGE_DIR/README.md"
        "$PACKAGE_DIR/MANIFEST.txt"
        "$PACKAGE_DIR/$PROJECT_NAME"
        "$PACKAGE_DIR/install.sh"
        "$PACKAGE_DIR/install_windows.bat"
    )
    
    for file in "${essential_files[@]}"; do
        if [ -e "$file" ]; then
            print_message "✅ $(basename "$file")"
        else
            print_error "❌ $(basename "$file") manquant"
            issues=$((issues + 1))
        fi
    done
    
    # Vérifier les permissions
    if [ -x "$PACKAGE_DIR/install.sh" ]; then
        print_message "✅ Permissions install.sh"
    else
        print_warning "⚠️  install.sh n'est pas exécutable"
    fi
    
    # Vérifier la taille des archives
    if [ -f "${BUILD_DIR}/${PACKAGE_NAME}.tar.gz" ] && command -v du >/dev/null 2>&1; then
        local size=$(du -m "${BUILD_DIR}/${PACKAGE_NAME}.tar.gz" 2>/dev/null | cut -f1 || echo "0")
        if [ "$size" -gt 0 ] && [ "$size" -lt 100 ]; then
            print_message "✅ Taille d'archive normale (${size}MB)"
        elif [ "$size" -ge 100 ]; then
            print_warning "⚠️  Archive volumineuse: ${size}MB"
        fi
    fi
    
    if [ $issues -eq 0 ]; then
        print_message "✅ Package validé avec succès"
    else
        print_error "❌ $issues problème(s) détecté(s)"
        return 1
    fi
}

# Afficher le résumé final
show_summary() {
    print_header "RÉSUMÉ DE LA CRÉATION DU PACKAGE"
    
    local total_size_tar="N/A"
    local total_size_zip="N/A"
    
    if [ -f "${BUILD_DIR}/${PACKAGE_NAME}.tar.gz" ] && command -v du >/dev/null 2>&1; then
        total_size_tar=$(du -h "${BUILD_DIR}/${PACKAGE_NAME}.tar.gz" 2>/dev/null | cut -f1 || echo "N/A")
    fi
    
    if [ -f "${BUILD_DIR}/${PACKAGE_NAME}.zip" ] && command -v du >/dev/null 2>&1; then
        total_size_zip=$(du -h "${BUILD_DIR}/${PACKAGE_NAME}.zip" 2>/dev/null | cut -f1 || echo "N/A")
    fi
    
    echo ""
    print_message "📦 Package créé avec succès:"
    echo "   Nom: $PACKAGE_NAME"
    echo "   Version: $VERSION"
    echo "   Date: $(date)"
    echo ""
    print_message "📁 Fichiers générés:"
    echo "   ${BUILD_DIR}/${PACKAGE_NAME}/ (répertoire)"
    if [ -f "${BUILD_DIR}/${PACKAGE_NAME}.tar.gz" ]; then
        echo "   ${BUILD_DIR}/${PACKAGE_NAME}.tar.gz ($total_size_tar)"
    fi
    if [ -f "${BUILD_DIR}/${PACKAGE_NAME}.zip" ]; then
        echo "   ${BUILD_DIR}/${PACKAGE_NAME}.zip ($total_size_zip)"
    fi
    echo ""
    print_message "🚀 Pour déployer:"
    echo "   1. Copiez l'archive sur le serveur cible"
    echo "   2. Extrayez: tar -xzf ${PACKAGE_NAME}.tar.gz"
    echo "   3. Installez: chmod +x install.sh && sudo ./install.sh"
    echo ""
    print_message "📖 Documentation:"
    echo "   Guide complet: docs/README_DEPLOYMENT.md"
    echo "   Dépannage: docs/TROUBLESHOOTING.md"
    echo ""
    print_message "✅ Package prêt pour le déploiement!"
}

# Menu d'aide
show_help() {
    echo "Usage: $0 [COMMANDE]"
    echo ""
    echo "COMMANDES:"
    echo "  build           Crée le package de déploiement complet"
    echo "  clean           Nettoie les fichiers de build"
    echo "  validate        Valide un package existant"
    echo "  help            Affiche cette aide"
    echo ""
    echo "CONFIGURATION:"
    echo "  PROJECT_NAME: $PROJECT_NAME"
    echo "  VERSION: $VERSION"
    echo "  BUILD_DIR: $BUILD_DIR"
    echo ""
    echo "EXEMPLE:"
    echo "  $0 build        # Crée le package complet"
    echo ""
}

# Fonction de nettoyage
clean_build() {
    print_header "NETTOYAGE"
    
    if [ -d "$BUILD_DIR" ]; then
        print_message "Suppression de $BUILD_DIR..."
        rm -rf "$BUILD_DIR"
        print_message "✅ Nettoyage terminé"
    else
        print_message "Aucun fichier de build à nettoyer"
    fi
}

# Script principal
main() {
    case "$1" in
        "build"|"")
            check_prerequisites
            prepare_directories
            copy_source_code
            create_installation_scripts
            create_documentation  
            create_config_files
            create_maintenance_scripts
            create_manifest
            generate_checksums
            create_archives
            validate_package
            show_summary
            ;;
        "clean")
            clean_build
            ;;
        "validate")
            validate_package
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            print_error "Commande inconnue: $1"
            show_help
            exit 1
            ;;
    esac
}

# Exécution
main "$@"

