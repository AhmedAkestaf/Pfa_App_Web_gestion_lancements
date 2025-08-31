#!/bin/bash

# =============================================================================
# Script d'installation automatique - Système de Gestion des Lancements
# AIC Métallurgie
# =============================================================================

set -e  # Arrêter le script en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher des messages colorés
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

# Variables de configuration
PROJECT_NAME="GESTION_LANCEMENTS"
PYTHON_VERSION="3.8"
VENV_NAME="venv_lancements"
DB_NAME="lancements"
DB_USER="postgres"
DB_PASSWORD="password123"
INSTALL_DIR="/opt/gestion-lancements"
SERVICE_USER="gestion-lancements"

print_header "INSTALLATION - SYSTÈME DE GESTION DES LANCEMENTS"
print_message "AIC Métallurgie - Version 1.0.0"
echo ""

# Vérifier les permissions root
if [[ $EUID -eq 0 ]]; then
   print_warning "Ce script est exécuté en tant que root."
   SUDO=""
else
   print_message "Vérification des permissions sudo..."
   SUDO="sudo"
fi

# Détecter l'OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [ -f /etc/debian_version ]; then
        DISTRO="debian"
        PKG_MANAGER="apt"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="redhat"
        PKG_MANAGER="yum"
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
    print_error "Installation Windows non supportée par ce script. Utilisez install_windows.bat"
    exit 1
else
    print_error "Système d'exploitation non supporté: $OSTYPE"
    exit 1
fi

print_message "Système détecté: $OS ($DISTRO)"

# 1. Mise à jour du système
print_header "ÉTAPE 1: MISE À JOUR DU SYSTÈME"
if [ "$DISTRO" = "debian" ]; then
    $SUDO apt update && $SUDO apt upgrade -y
elif [ "$DISTRO" = "redhat" ]; then
    $SUDO yum update -y
fi

# 2. Installation des dépendances système
print_header "ÉTAPE 2: INSTALLATION DES DÉPENDANCES SYSTÈME"

if [ "$DISTRO" = "debian" ]; then
    $SUDO apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        postgresql \
        postgresql-contrib \
        postgresql-server-dev-all \
        nginx \
        git \
        curl \
        build-essential \
        libpq-dev \
        supervisor
elif [ "$DISTRO" = "redhat" ]; then
    $SUDO yum install -y \
        python3 \
        python3-pip \
        python3-devel \
        postgresql \
        postgresql-server \
        postgresql-contrib \
        postgresql-devel \
        nginx \
        git \
        curl \
        gcc \
        supervisor
fi

# 3. Configuration PostgreSQL
print_header "ÉTAPE 3: CONFIGURATION DE LA BASE DE DONNÉES"

# Initialiser PostgreSQL (RedHat uniquement)
if [ "$DISTRO" = "redhat" ]; then
    $SUDO postgresql-setup initdb
fi

# Démarrer PostgreSQL
$SUDO systemctl start postgresql
$SUDO systemctl enable postgresql

print_message "Création de la base de données et de l'utilisateur..."

# Créer la base de données
$SUDO -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
$SUDO -u postgres psql -c "DROP USER IF EXISTS $DB_USER;"
$SUDO -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
$SUDO -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
$SUDO -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

print_message "Base de données créée avec succès!"

# 4. Créer utilisateur système
print_header "ÉTAPE 4: CRÉATION DE L'UTILISATEUR SYSTÈME"
if ! id "$SERVICE_USER" &>/dev/null; then
    $SUDO useradd --system --home /opt/gestion-lancements --shell /bin/bash $SERVICE_USER
    print_message "Utilisateur $SERVICE_USER créé"
else
    print_warning "L'utilisateur $SERVICE_USER existe déjà"
fi

# 5. Créer les répertoires
print_header "ÉTAPE 5: CRÉATION DES RÉPERTOIRES"
$SUDO mkdir -p $INSTALL_DIR
$SUDO mkdir -p $INSTALL_DIR/logs
$SUDO mkdir -p /var/log/gestion-lancements

# 6. Copier les fichiers du projet
print_header "ÉTAPE 6: COPIE DES FICHIERS DU PROJET"
if [ -d "./$PROJECT_NAME" ]; then
    $SUDO cp -r ./$PROJECT_NAME/* $INSTALL_DIR/
    print_message "Fichiers du projet copiés"
elif [ -f "./manage.py" ]; then
    $SUDO cp -r ./* $INSTALL_DIR/
    print_message "Fichiers du projet copiés depuis le répertoire courant"
else
    print_error "Fichiers du projet non trouvés!"
    print_message "Assurez-vous d'exécuter le script depuis le répertoire contenant le projet"
    exit 1
fi

# Définir les permissions
$SUDO chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
$SUDO chmod -R 755 $INSTALL_DIR

# 7. Création de l'environnement virtuel Python
print_header "ÉTAPE 7: CRÉATION DE L'ENVIRONNEMENT VIRTUEL"
cd $INSTALL_DIR
$SUDO -u $SERVICE_USER python3 -m venv $VENV_NAME
print_message "Environnement virtuel créé"

# 8. Installation des dépendances Python
print_header "ÉTAPE 8: INSTALLATION DES DÉPENDANCES PYTHON"
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/pip install --upgrade pip
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/pip install -r $INSTALL_DIR/requirements.txt
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/pip install gunicorn
print_message "Dépendances Python installées"

# 9. Configuration de l'environnement
print_header "ÉTAPE 9: CONFIGURATION DE L'ENVIRONNEMENT"
$SUDO tee $INSTALL_DIR/.env > /dev/null <<EOF
# Configuration de production
DEBUG=False
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=localhost,127.0.0.1,$(hostname -I | awk '{print $1}')

# Base de données
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=5432

# Paths
STATIC_ROOT=$INSTALL_DIR/staticfiles
MEDIA_ROOT=$INSTALL_DIR/media
EOF

$SUDO chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/.env
$SUDO chmod 600 $INSTALL_DIR/.env
print_message "Fichier de configuration créé"

# 10. Initialisation de Django
print_header "ÉTAPE 10: INITIALISATION DE DJANGO"
cd $INSTALL_DIR

print_message "Exécution des migrations..."
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/python manage.py makemigrations
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/python manage.py migrate

print_message "Initialisation des permissions..."
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/python manage.py init_permissions

print_message "Collecte des fichiers statiques..."
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/python manage.py collectstatic --noinput

print_message "Création du super-utilisateur..."
$SUDO -u $SERVICE_USER $INSTALL_DIR/$VENV_NAME/bin/python manage.py create_superuser_with_role

# 11. Configuration de Gunicorn
print_header "ÉTAPE 11: CONFIGURATION DE GUNICORN"
$SUDO tee $INSTALL_DIR/gunicorn_config.py > /dev/null <<EOF
# Configuration Gunicorn
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 5
user = "$SERVICE_USER"
group = "$SERVICE_USER"
chdir = "$INSTALL_DIR"
pidfile = "$INSTALL_DIR/gunicorn.pid"
accesslog = "/var/log/gestion-lancements/gunicorn_access.log"
errorlog = "/var/log/gestion-lancements/gunicorn_error.log"
loglevel = "info"
EOF

# 12. Configuration du service systemd
print_header "ÉTAPE 12: CONFIGURATION DU SERVICE SYSTEMD"
$SUDO tee /etc/systemd/system/gestion-lancements.service > /dev/null <<EOF
[Unit]
Description=Gestion Lancements Django Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=forking
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/$VENV_NAME/bin
ExecStart=$INSTALL_DIR/$VENV_NAME/bin/gunicorn gestion_lancements.wsgi:application -c $INSTALL_DIR/gunicorn_config.py --daemon
ExecReload=/bin/kill -s HUP \$MAINPID
PIDFile=$INSTALL_DIR/gunicorn.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 13. Configuration de Nginx
print_header "ÉTAPE 13: CONFIGURATION DE NGINX"
$SUDO tee /etc/nginx/sites-available/gestion-lancements > /dev/null <<EOF
server {
    listen 80;
    server_name localhost $(hostname -I | awk '{print $1}');
    
    client_max_body_size 50M;
    
    location /static/ {
        alias $INSTALL_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias $INSTALL_DIR/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30;
        proxy_send_timeout 30;
        proxy_read_timeout 30;
    }
}
EOF

# Activer le site
if [ -d "/etc/nginx/sites-enabled" ]; then
    $SUDO ln -sf /etc/nginx/sites-available/gestion-lancements /etc/nginx/sites-enabled/
    $SUDO rm -f /etc/nginx/sites-enabled/default
fi

# Tester la configuration Nginx
$SUDO nginx -t

# 14. Démarrage des services
print_header "ÉTAPE 14: DÉMARRAGE DES SERVICES"

# Recharger systemd
$SUDO systemctl daemon-reload

# Activer et démarrer les services
$SUDO systemctl enable gestion-lancements
$SUDO systemctl start gestion-lancements

$SUDO systemctl enable nginx
$SUDO systemctl restart nginx

# Vérifier le statut des services
print_message "Vérification du statut des services..."
$SUDO systemctl status gestion-lancements --no-pager -l
$SUDO systemctl status nginx --no-pager -l

# 15. Configuration du pare-feu (si ufw est installé)
if command -v ufw &> /dev/null; then
    print_header "ÉTAPE 15: CONFIGURATION DU PARE-FEU"
    $SUDO ufw allow 22/tcp  # SSH
    $SUDO ufw allow 80/tcp  # HTTP
    $SUDO ufw allow 443/tcp # HTTPS
    $SUDO ufw --force enable
    print_message "Pare-feu configuré"
fi

# 16. Installation terminée
print_header "INSTALLATION TERMINÉE AVEC SUCCÈS!"
echo ""
print_message "🎉 L'application Gestion des Lancements est maintenant installée et en cours d'exécution!"
echo ""
print_message "📍 Informations de connexion:"
echo "   URL: http://$(hostname -I | awk '{print $1}')"
echo "   URL locale: http://localhost"
echo ""
print_message "📂 Répertoire d'installation: $INSTALL_DIR"
print_message "👤 Utilisateur système: $SERVICE_USER"
print_message "🗃️ Base de données: $DB_NAME"
echo ""
print_message "🔧 Commandes utiles:"
echo "   • Redémarrer l'application: sudo systemctl restart gestion-lancements"
echo "   • Voir les logs: sudo journalctl -u gestion-lancements -f"
echo "   • Statut des services: sudo systemctl status gestion-lancements"
echo "   • Logs Nginx: sudo tail -f /var/log/nginx/error.log"
echo ""
print_warning "⚠️  N'oubliez pas de:"
echo "   • Configurer votre domaine dans /etc/nginx/sites-available/gestion-lancements"
echo "   • Mettre à jour ALLOWED_HOSTS dans $INSTALL_DIR/.env"
echo "   • Configurer un certificat SSL pour la production"
echo "   • Planifier des sauvegardes régulières"
echo ""
print_message "✅ Installation terminée - Vous pouvez maintenant accéder à l'application!"