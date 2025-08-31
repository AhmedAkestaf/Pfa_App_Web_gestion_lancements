#!/bin/bash

# =============================================================================
# Script de mise à jour automatique - Gestion des Lancements
# AIC Métallurgie
# =============================================================================

set -e

# Configuration
INSTALL_DIR="/opt/gestion-lancements"
BACKUP_DIR="/opt/gestion-lancements/backups"
SERVICE_NAME="gestion-lancements"
VENV_NAME="venv_lancements"
UPDATE_LOG="/var/log/gestion-lancements/update.log"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "$(date): [INFO] $1" >> "$UPDATE_LOG"
}

print_warning() {
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
    echo "$(date): [WARNING] $1" >> "$UPDATE_LOG"
}

print_error() {
    echo -e "${RED}[ERREUR]${NC} $1"
    echo "$(date): [ERROR] $1" >> "$UPDATE_LOG"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1 ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "$(date): ======== $1 ========" >> "$UPDATE_LOG"
}

# Vérifier les prérequis
check_prerequisites() {
    print_header "VÉRIFICATION DES PRÉREQUIS"
    
    # Vérifier les permissions root
    if [[ $EUID -ne 0 ]]; then
        print_error "Ce script doit être exécuté en tant que root"
        exit 1
    fi
    
    # Vérifier l'existence du répertoire d'installation
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Répertoire d'installation non trouvé: $INSTALL_DIR"
        exit 1
    fi
    
    # Vérifier que les services sont installés
    if ! systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
        print_error "Service $SERVICE_NAME non trouvé"
        exit 1
    fi
    
    # Créer le répertoire de logs si nécessaire
    mkdir -p "$(dirname "$UPDATE_LOG")"
    
    print_message "✅ Prérequis validés"
}

# Fonction de sauvegarde avant mise à jour
backup_before_update() {
    print_header "SAUVEGARDE AVANT MISE À JOUR"
    
    if [ -f "$INSTALL_DIR/maintenance/backup_db.sh" ]; then
        print_message "Exécution du script de sauvegarde..."
        bash "$INSTALL_DIR/maintenance/backup_db.sh" backup
    else
        print_warning "Script de sauvegarde non trouvé, création d'une sauvegarde simple..."
        
        local timestamp=$(date +"%Y%m%d_%H%M%S")
        local backup_path="${BACKUP_DIR}/pre_update_${timestamp}"
        
        mkdir -p "$backup_path"
        
        # Sauvegarde base de données
        sudo -u postgres pg_dump -d gestion_lancements_aic > "$backup_path/database.sql"
        
        # Sauvegarde configuration
        cp "$INSTALL_DIR/.env" "$backup_path/"
        
        # Sauvegarde media
        if [ -d "$INSTALL_DIR/media" ]; then
            tar -czf "$backup_path/media.tar.gz" -C "$INSTALL_DIR" media/
        fi
        
        print_message "✅ Sauvegarde créée: $backup_path"
    fi
}

# Arrêter les services
stop_services() {
    print_header "ARRÊT DES SERVICES"
    
    services=("$SERVICE_NAME" "nginx")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            print_message "Arrêt de $service..."
            systemctl stop "$service"
            
            # Attendre que le service soit complètement arrêté
            timeout=30
            while systemctl is-active --quiet "$service" && [ $timeout -gt 0 ]; do
                sleep 1
                timeout=$((timeout - 1))
            done
            
            if systemctl is-active --quiet "$service"; then
                print_warning "$service ne s'est pas arrêté proprement"
            else
                print_message "✅ $service arrêté"
            fi
        else
            print_message "$service n'était pas en cours d'exécution"
        fi
    done
}

# Mettre à jour les dépendances système
update_system_dependencies() {
    print_header "MISE À JOUR DES DÉPENDANCES SYSTÈME"
    
    # Détecter la distribution
    if [ -f /etc/debian_version ]; then
        print_message "Mise à jour des paquets (Debian/Ubuntu)..."
        apt update
        apt upgrade -y python3 python3-pip postgresql nginx
    elif [ -f /etc/redhat-release ]; then
        print_message "Mise à jour des paquets (RedHat/CentOS)..."
        yum update -y python3 python3-pip postgresql nginx
    else
        print_warning "Distribution non reconnue, dépendances système non mises à jour"
    fi
    
    print_message "✅ Dépendances système mises à jour"
}

# Mettre à jour l'application
update_application() {
    print_header "MISE À JOUR DE L'APPLICATION"
    
    cd "$INSTALL_DIR"
    
    # Sauvegarder l'ancien code si ce n'est pas déjà fait
    if [ ! -d "backup_code_$(date +%Y%m%d)" ]; then
        print_message "Sauvegarde de l'ancien code..."
        mkdir -p "backup_code_$(date +%Y%m%d)"
        
        # Copier les fichiers importants
        cp -r apps/ "backup_code_$(date +%Y%m%d)/" 2>/dev/null || true
        cp -r gestion_lancements/ "backup_code_$(date +%Y%m%d)/" 2>/dev/null || true
        cp -r templates/ "backup_code_$(date +%Y%m%d)/" 2>/dev/null || true
        cp requirements.txt "backup_code_$(date +%Y%m%d)/" 2>/dev/null || true
        cp manage.py "backup_code_$(date +%Y%m%d)/" 2>/dev/null || true
    fi
    
    # Si les nouveaux fichiers sont fournis dans un répertoire update/
    if [ -d "update/" ]; then
        print_message "Application des nouveaux fichiers..."
        
        # Copier les nouveaux fichiers
        cp -r update/* . 2>/dev/null || true
        
        # Définir les bonnes permissions
        chown -R gestion-lancements:gestion-lancements .
        chmod -R 755 .
        
        print_message "✅ Nouveaux fichiers appliqués"
    else
        print_message "Aucun répertoire de mise à jour trouvé, mise à jour des dépendances Python uniquement"
    fi
    
    # Mettre à jour l'environnement virtuel Python
    print_message "Mise à jour de l'environnement virtuel..."
    
    # Activer l'environnement virtuel
    source "$VENV_NAME/bin/activate"
    
    # Mettre à jour pip
    pip install --upgrade pip
    
    # Mettre à jour les dépendances
    if [ -f "requirements.txt" ]; then
        pip install --upgrade -r requirements.txt
        print_message "✅ Dépendances Python mises à jour"
    else
        print_warning "Fichier requirements.txt non trouvé"
    fi
    
    # S'assurer que gunicorn est installé
    pip install --upgrade gunicorn
    
    deactivate
}

# Mettre à jour la base de données
update_database() {
    print_header "MISE À JOUR DE LA BASE DE DONNÉES"
    
    cd "$INSTALL_DIR"
    
    # Activer l'environnement virtuel
    source "$VENV_NAME/bin/activate"
    
    # Créer les nouvelles migrations
    print_message "Création des migrations..."
    sudo -u gestion-lancements python manage.py makemigrations
    
    # Appliquer les migrations
    print_message "Application des migrations..."
    sudo -u gestion-lancements python manage.py migrate
    
    # Mettre à jour les permissions si la commande existe
    if sudo -u gestion-lancements python manage.py help | grep -q "init_permissions"; then
        print_message "Mise à jour des permissions..."
        sudo -u gestion-lancements python manage.py init_permissions
    fi
    
    # Collecter les fichiers statiques
    print_message "Collecte des fichiers statiques..."
    sudo -u gestion-lancements python manage.py collectstatic --noinput --clear
    
    deactivate
    
    print_message "✅ Base de données mise à jour"
}

# Redémarrer les services
start_services() {
    print_header "REDÉMARRAGE DES SERVICES"
    
    # Recharger la configuration systemd
    systemctl daemon-reload
    
    services=("postgresql" "$SERVICE_NAME" "nginx")
    
    for service in "${services[@]}"; do
        print_message "Démarrage de $service..."
        systemctl start "$service"
        
        # Vérifier que le service a démarré
        sleep 3
        if systemctl is-active --quiet "$service"; then
            print_message "✅ $service démarré"
        else
            print_error "❌ Échec du démarrage de $service"
            print_message "Logs: journalctl -u $service -n 50"
            
            # Essayer de redémarrer une fois de plus
            print_message "Nouvelle tentative de démarrage..."
            systemctl restart "$service"
            sleep 5
            
            if systemctl is-active --quiet "$service"; then
                print_message "✅ $service démarré (2ème tentative)"
            else
                print_error "❌ $service n'a pas pu démarrer"
                return 1
            fi
        fi
    done
}

# Vérifier le bon fonctionnement
verify_update() {
    print_header "VÉRIFICATION DE LA MISE À JOUR"
    
    local issues=0
    
    # Vérifier les services
    services=("postgresql" "$SERVICE_NAME" "nginx")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            print_message "✅ $service: Actif"
        else
            print_error "❌ $service: Inactif"
            issues=$((issues + 1))
        fi
    done
    
    # Test de connectivité HTTP
    print_message "Test de l'accès web..."
    sleep 10  # Laisser le temps à l'application de démarrer
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost || echo "000")
    
    if [[ "$http_code" == "200" || "$http_code" == "302" ]]; then
        print_message "✅ Application web accessible (HTTP $http_code)"
    else
        print_error "❌ Application web inaccessible (HTTP $http_code)"
        issues=$((issues + 1))
    fi
    
    # Test de la base de données
    print_message "Test de la base de données..."
    cd "$INSTALL_DIR"
    source "$VENV_NAME/bin/activate"
    
    if sudo -u gestion-lancements python manage.py check --database default; then
        print_message "✅ Base de données accessible"
    else
        print_error "❌ Problème avec la base de données"
        issues=$((issues + 1))
    fi
    
    deactivate
    
    # Résumé
    if [ $issues -eq 0 ]; then
        print_header "✅ MISE À JOUR RÉUSSIE"
        print_message "L'application est opérationnelle"
    else
        print_header "⚠️  MISE À JOUR PARTIELLEMENT RÉUSSIE"
        print_warning "$issues problème(s) détecté(s)"
        print_message "Consultez les logs pour plus de détails"
    fi
    
    return $issues
}

# Fonction de rollback en cas d'échec
rollback_update() {
    print_header "ROLLBACK EN COURS"
    
    print_warning "Restauration de la dernière sauvegarde..."
    
    # Trouver la dernière sauvegarde
    local latest_backup=$(find "$BACKUP_DIR" -name "backup_gestion_lancements_*.tar.gz" -o -name "pre_update_*" | sort -r | head -1)
    
    if [ -n "$latest_backup" ] && [ -f "$latest_backup" ]; then
        print_message "Restauration depuis: $latest_backup"
        
        if [ -f "$INSTALL_DIR/maintenance/backup_db.sh" ]; then
            bash "$INSTALL_DIR/maintenance/backup_db.sh" restore "$latest_backup"
        else
            print_error "Script de restauration non trouvé"
            print_message "Restauration manuelle requise depuis: $latest_backup"
        fi
    else
        print_error "Aucune sauvegarde trouvée pour le rollback"
        print_message "Restauration manuelle requise"
    fi
}

# Fonction de mise à jour automatique
auto_update() {
    print_header "MISE À JOUR AUTOMATIQUE - GESTION DES LANCEMENTS"
    
    local start_time=$(date)
    local success=true
    
    # Étapes de mise à jour
    check_prerequisites || exit 1
    
    backup_before_update || {
        print_error "Échec de la sauvegarde"
        exit 1
    }
    
    stop_services || {
        print_error "Échec de l'arrêt des services"
        exit 1
    }
    
    update_system_dependencies || {
        print_warning "Problème avec la mise à jour des dépendances système"
    }
    
    update_application || {
        print_error "Échec de la mise à jour de l'application"
        success=false
    }
    
    if [ "$success" = true ]; then
        update_database || {
            print_error "Échec de la mise à jour de la base de données"
            success=false
        }
    fi
    
    start_services || {
        print_error "Échec du redémarrage des services"
        success=false
    }
    
    if [ "$success" = true ]; then
        verify_update || {
            print_warning "Problèmes détectés après la mise à jour"
            success=false
        }
    fi
    
    # Résumé final
    local end_time=$(date)
    
    if [ "$success" = true ]; then
        print_header "🎉 MISE À JOUR TERMINÉE AVEC SUCCÈS"
        print_message "Début: $start_time"
        print_message "Fin: $end_time"
        print_message "Application disponible à: http://localhost"
    else
        print_header "❌ ÉCHEC DE LA MISE À JOUR"
        print_error "La mise à jour a échoué"
        print_message "Début: $start_time"
        print_message "Fin: $end_time"
        
        read -p "Voulez-vous effectuer un rollback automatique? (o/N): " rollback_choice
        if [[ "$rollback_choice" =~ ^[Oo]$ ]]; then
            rollback_update
        else
            print_message "Rollback manuel requis"
            print_message "Consultez les logs: $UPDATE_LOG"
        fi
        
        exit 1
    fi
}

# Menu d'aide
show_help() {
    echo "Usage: $0 [COMMANDE]"
    echo ""
    echo "COMMANDES:"
    echo "  update          Lance la mise à jour automatique complète"
    echo "  check           Vérifie les prérequis sans faire de mise à jour"
    echo "  rollback        Effectue un rollback vers la dernière sauvegarde"
    echo "  help            Affiche cette aide"
    echo ""
    echo "EXEMPLES:"
    echo "  $0 update       # Mise à jour complète"
    echo "  $0 check        # Vérification seulement"
    echo "  $0 rollback     # Rollback"
    echo ""
    echo "FICHIERS:"
    echo "  Log: $UPDATE_LOG"
    echo "  Installation: $INSTALL_DIR"
    echo "  Sauvegardes: $BACKUP_DIR"
    echo ""
}

# Script principal
case "$1" in
    "update"|"")
        auto_update
        ;;
    "check")
        check_prerequisites
        ;;
    "rollback")
        rollback_update
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