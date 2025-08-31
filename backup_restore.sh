#!/bin/bash

# =============================================================================
# Scripts de sauvegarde et restauration - Gestion des Lancements
# AIC Métallurgie
# =============================================================================

set -e

# Configuration
INSTALL_DIR="/opt/gestion-lancements"
BACKUP_DIR="/opt/gestion-lancements/backups"
DB_NAME="gestion_lancements_aic"
DB_USER="aic_user"
SERVICE_NAME="gestion-lancements"
RETENTION_DAYS=30

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

# Fonction de sauvegarde complète
backup_full() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_name="backup_gestion_lancements_${timestamp}"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    print_header "SAUVEGARDE COMPLÈTE - ${timestamp}"
    
    # Créer le répertoire de sauvegarde
    mkdir -p "${backup_path}"
    mkdir -p "${BACKUP_DIR}/logs"
    
    # 1. Sauvegarde de la base de données
    print_message "Sauvegarde de la base de données..."
    pg_dump -h localhost -U ${DB_USER} -d ${DB_NAME} > "${backup_path}/database.sql"
    
    if [ $? -eq 0 ]; then
        print_message "✅ Base de données sauvegardée"
    else
        print_error "❌ Échec de la sauvegarde de la base de données"
        return 1
    fi
    
    # 2. Sauvegarde des fichiers media
    print_message "Sauvegarde des fichiers media..."
    if [ -d "${INSTALL_DIR}/media" ]; then
        tar -czf "${backup_path}/media.tar.gz" -C "${INSTALL_DIR}" media/
        print_message "✅ Fichiers media sauvegardés"
    else
        print_warning "Répertoire media non trouvé, ignoré"
    fi
    
    # 3. Sauvegarde de la configuration
    print_message "Sauvegarde de la configuration..."
    cp "${INSTALL_DIR}/.env" "${backup_path}/"
    cp "${INSTALL_DIR}/gunicorn_config.py" "${backup_path}/" 2>/dev/null || true
    
    # Copier les configurations système importantes
    if [ -f "/etc/nginx/sites-available/gestion-lancements" ]; then
        cp "/etc/nginx/sites-available/gestion-lancements" "${backup_path}/nginx_config"
    fi
    
    if [ -f "/etc/systemd/system/gestion-lancements.service" ]; then
        cp "/etc/systemd/system/gestion-lancements.service" "${backup_path}/systemd_service"
    fi
    
    print_message "✅ Configuration sauvegardée"
    
    # 4. Sauvegarde des logs récents (7 derniers jours)
    print_message "Sauvegarde des logs récents..."
    mkdir -p "${backup_path}/logs"
    
    if [ -d "/var/log/gestion-lancements" ]; then
        find /var/log/gestion-lancements -name "*.log" -mtime -7 -exec cp {} "${backup_path}/logs/" \;
    fi
    
    # 5. Créer un manifeste de la sauvegarde
    print_message "Création du manifeste..."
    cat > "${backup_path}/manifest.txt" <<EOF
SAUVEGARDE GESTION DES LANCEMENTS
=================================
Date: $(date)
Timestamp: ${timestamp}
Version: 1.0.0

Contenu:
- database.sql : Dump complet de la base PostgreSQL
- media.tar.gz : Fichiers uploadés par les utilisateurs
- .env : Configuration de l'application
- gunicorn_config.py : Configuration du serveur
- nginx_config : Configuration Nginx
- systemd_service : Service systemd
- logs/ : Logs des 7 derniers jours
- manifest.txt : Ce fichier

Installation source: ${INSTALL_DIR}
Base de données: ${DB_NAME}
Utilisateur DB: ${DB_USER}
EOF
    
    # 6. Compresser la sauvegarde complète
    print_message "Compression de la sauvegarde..."
    cd "${BACKUP_DIR}"
    tar -czf "${backup_name}.tar.gz" "${backup_name}/"
    
    # Supprimer le répertoire temporaire
    rm -rf "${backup_path}"
    
    # 7. Vérification de l'intégrité
    print_message "Vérification de l'intégrité..."
    if tar -tzf "${backup_name}.tar.gz" >/dev/null 2>&1; then
        local backup_size=$(du -h "${backup_name}.tar.gz" | cut -f1)
        print_message "✅ Sauvegarde créée avec succès: ${backup_name}.tar.gz (${backup_size})"
        
        # Log de la sauvegarde
        echo "$(date): Sauvegarde réussie - ${backup_name}.tar.gz (${backup_size})" >> "${BACKUP_DIR}/logs/backup.log"
    else
        print_error "❌ Erreur lors de la compression de la sauvegarde"
        return 1
    fi
    
    # 8. Nettoyage des anciennes sauvegardes
    cleanup_old_backups
    
    print_header "SAUVEGARDE TERMINÉE AVEC SUCCÈS"
    print_message "Fichier: ${BACKUP_DIR}/${backup_name}.tar.gz"
}

# Fonction de restauration
restore_from_backup() {
    local backup_file="$1"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    
    if [ -z "$backup_file" ]; then
        print_error "Usage: $0 restore <chemin_vers_backup.tar.gz>"
        list_backups
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "Fichier de sauvegarde non trouvé: $backup_file"
        return 1
    fi
    
    print_header "RESTAURATION DEPUIS LA SAUVEGARDE"
    print_warning "⚠️  ATTENTION: Cette opération va remplacer les données actuelles!"
    print_message "Fichier: $backup_file"
    
    read -p "Êtes-vous sûr de vouloir continuer? (tapez 'OUI' pour confirmer): " confirm
    if [ "$confirm" != "OUI" ]; then
        print_message "Restauration annulée"
        return 0
    fi
    
    # Créer une sauvegarde de sécurité avant restauration
    print_message "Création d'une sauvegarde de sécurité..."
    backup_full || {
        print_error "Échec de la sauvegarde de sécurité"
        return 1
    }
    
    # Extraire la sauvegarde
    local temp_dir="/tmp/restore_${timestamp}"
    mkdir -p "$temp_dir"
    
    print_message "Extraction de la sauvegarde..."
    tar -xzf "$backup_file" -C "$temp_dir" || {
        print_error "Échec de l'extraction"
        rm -rf "$temp_dir"
        return 1
    }
    
    # Trouver le répertoire de sauvegarde extrait
    local backup_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "backup_gestion_lancements_*" | head -1)
    
    if [ -z "$backup_dir" ]; then
        print_error "Structure de sauvegarde invalide"
        rm -rf "$temp_dir"
        return 1
    fi
    
    print_message "Structure de sauvegarde validée"
    
    # Arrêter les services
    print_message "Arrêt des services..."
    systemctl stop $SERVICE_NAME || true
    systemctl stop nginx || true
    
    # Restaurer la base de données
    if [ -f "$backup_dir/database.sql" ]; then
        print_message "Restauration de la base de données..."
        
        # Sauvegarder l'ancienne base
        sudo -u postgres pg_dump -d $DB_NAME > "/tmp/old_${DB_NAME}_${timestamp}.sql" 2>/dev/null || true
        
        # Restaurer la nouvelle base
        sudo -u postgres psql -d $DB_NAME -f "$backup_dir/database.sql" || {
            print_error "Échec de la restauration de la base de données"
            print_message "Tentative de restauration de l'ancienne base..."
            sudo -u postgres psql -d $DB_NAME -f "/tmp/old_${DB_NAME}_${timestamp}.sql" 2>/dev/null || true
            rm -rf "$temp_dir"
            return 1
        }
        
        print_message "✅ Base de données restaurée"
    fi
    
    # Restaurer les fichiers media
    if [ -f "$backup_dir/media.tar.gz" ]; then
        print_message "Restauration des fichiers media..."
        rm -rf "${INSTALL_DIR}/media.bak" 2>/dev/null || true
        mv "${INSTALL_DIR}/media" "${INSTALL_DIR}/media.bak" 2>/dev/null || true
        
        tar -xzf "$backup_dir/media.tar.gz" -C "$INSTALL_DIR" || {
            print_warning "Échec de la restauration des fichiers media"
            mv "${INSTALL_DIR}/media.bak" "${INSTALL_DIR}/media" 2>/dev/null || true
        }
        
        chown -R gestion-lancements:gestion-lancements "${INSTALL_DIR}/media" 2>/dev/null || true
        print_message "✅ Fichiers media restaurés"
    fi
    
    # Restaurer la configuration
    if [ -f "$backup_dir/.env" ]; then
        print_message "Restauration de la configuration..."
        cp "${INSTALL_DIR}/.env" "${INSTALL_DIR}/.env.bak"
        cp "$backup_dir/.env" "${INSTALL_DIR}/"
        chown gestion-lancements:gestion-lancements "${INSTALL_DIR}/.env"
        print_message "✅ Configuration restaurée"
    fi
    
    # Redémarrer les services
    print_message "Redémarrage des services..."
    systemctl start $SERVICE_NAME
    systemctl start nginx
    
    # Vérifier que les services sont en cours d'exécution
    sleep 5
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_message "✅ Service application redémarré"
    else
        print_error "❌ Problème avec le service application"
        print_message "Consultez les logs: journalctl -u $SERVICE_NAME"
    fi
    
    if systemctl is-active --quiet nginx; then
        print_message "✅ Service nginx redémarré"
    else
        print_error "❌ Problème avec nginx"
    fi
    
    # Nettoyage
    rm -rf "$temp_dir"
    
    print_header "RESTAURATION TERMINÉE"
    print_message "La restauration a été effectuée depuis: $(basename $backup_file)"
    print_message "Les anciennes données ont été sauvegardées avec le suffixe .bak"
    print_warning "Testez l'application pour vous assurer que tout fonctionne correctement"
}

# Fonction pour lister les sauvegardes
list_backups() {
    print_header "SAUVEGARDES DISPONIBLES"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_warning "Aucun répertoire de sauvegarde trouvé"
        return 0
    fi
    
    local backups=($(find "$BACKUP_DIR" -name "backup_gestion_lancements_*.tar.gz" -type f | sort -r))
    
    if [ ${#backups[@]} -eq 0 ]; then
        print_warning "Aucune sauvegarde trouvée"
        return 0
    fi
    
    printf "%-5s %-25s %-15s %-10s\n" "N°" "Date/Heure" "Taille" "Fichier"
    printf "%s\n" "------------------------------------------------------------"
    
    local i=1
    for backup in "${backups[@]}"; do
        local filename=$(basename "$backup")
        local timestamp=$(echo "$filename" | sed 's/backup_gestion_lancements_\([0-9_]*\)\.tar\.gz/\1/')
        local date_formatted=$(echo "$timestamp" | sed 's/\([0-9]\{8\}\)_\([0-9]\{6\}\)/\1 \2/' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\) \([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\3\/\2\/\1 \4:\5:\6/')
        local size=$(du -h "$backup" | cut -f1)
        
        printf "%-5d %-25s %-15s %-10s\n" "$i" "$date_formatted" "$size" "$(basename $backup)"
        i=$((i+1))
    done
    
    echo ""
    print_message "Pour restaurer une sauvegarde: $0 restore <chemin_complet_vers_le_fichier>"
}

# Fonction de nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    print_message "Nettoyage des sauvegardes anciennes (>${RETENTION_DAYS} jours)..."
    
    if [ -d "$BACKUP_DIR" ]; then
        local deleted_count=0
        while IFS= read -r -d '' backup; do
            rm -f "$backup"
            deleted_count=$((deleted_count + 1))
            print_message "Supprimé: $(basename "$backup")"
        done < <(find "$BACKUP_DIR" -name "backup_gestion_lancements_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -print0)
        
        if [ $deleted_count -gt 0 ]; then
            print_message "✅ $deleted_count anciennes sauvegardes supprimées"
        else
            print_message "Aucune ancienne sauvegarde à supprimer"
        fi
    fi
}

# Fonction de vérification de santé
health_check() {
    print_header "VÉRIFICATION DE SANTÉ DU SYSTÈME"
    
    local issues=0
    
    # Vérifier les services
    print_message "Vérification des services..."
    
    services=("postgresql" "$SERVICE_NAME" "nginx")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            print_message "✅ $service: Actif"
        else
            print_error "❌ $service: Inactif"
            issues=$((issues + 1))
        fi
    done
    
    # Vérifier l'espace disque
    print_message "Vérification de l'espace disque..."
    local disk_usage=$(df "${INSTALL_DIR}" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -lt 80 ]; then
        print_message "✅ Espace disque: ${disk_usage}% utilisé"
    elif [ "$disk_usage" -lt 90 ]; then
        print_warning "⚠️  Espace disque: ${disk_usage}% utilisé (Attention)"
    else
        print_error "❌ Espace disque: ${disk_usage}% utilisé (Critique)"
        issues=$((issues + 1))
    fi
    
    # Vérifier la connectivité base de données
    print_message "Vérification de la base de données..."
    if sudo -u postgres psql -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        print_message "✅ Base de données: Accessible"
    else
        print_error "❌ Base de données: Inaccessible"
        issues=$((issues + 1))
    fi
    
    # Vérifier l'accès web
    print_message "Vérification de l'accès web..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
        print_message "✅ Application web: Accessible"
    else
        print_error "❌ Application web: Inaccessible"
        issues=$((issues + 1))
    fi
    
    # Résumé
    echo ""
    if [ $issues -eq 0 ]; then
        print_header "✅ SYSTÈME EN BONNE SANTÉ"
    else
        print_header "⚠️  $issues PROBLÈME(S) DÉTECTÉ(S)"
        print_message "Consultez les logs pour plus de détails:"
        print_message "  - Application: journalctl -u $SERVICE_NAME"
        print_message "  - Nginx: tail -f /var/log/nginx/error.log"
        print_message "  - PostgreSQL: tail -f /var/log/postgresql/postgresql-*.log"
    fi
}

# Menu principal
show_help() {
    echo "Usage: $0 [COMMANDE] [OPTIONS]"
    echo ""
    echo "COMMANDES:"
    echo "  backup          Effectue une sauvegarde complète"
    echo "  restore FILE    Restaure depuis un fichier de sauvegarde"
    echo "  list            Liste les sauvegardes disponibles"
    echo "  cleanup         Nettoie les anciennes sauvegardes"
    echo "  health          Vérifie la santé du système"
    echo "  help            Affiche cette aide"
    echo ""
    echo "EXEMPLES:"
    echo "  $0 backup"
    echo "  $0 restore /opt/gestion-lancements/backups/backup_gestion_lancements_20240827_143000.tar.gz"
    echo "  $0 list"
    echo "  $0 health"
    echo ""
    echo "CONFIGURATION:"
    echo "  Répertoire d'installation: $INSTALL_DIR"
    echo "  Répertoire de sauvegarde: $BACKUP_DIR"
    echo "  Base de données: $DB_NAME"
    echo "  Rétention: $RETENTION_DAYS jours"
    echo ""
}

# Script principal
main() {
    case "$1" in
        "backup")
            backup_full
            ;;
        "restore")
            restore_from_backup "$2"
            ;;
        "list")
            list_backups
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "health")
            health_check
            ;;
        "help"|"--help"|"-h"|"")
            show_help
            ;;
        *)
            print_error "Commande inconnue: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Vérifications préliminaires
if [[ $EUID -ne 0 ]] && [[ "$1" != "help" ]] && [[ "$1" != "--help" ]] && [[ "$1" != "-h" ]] && [[ "$1" != "list" ]]; then
   print_error "Ce script doit être exécuté avec des privilèges root (sauf pour 'list' et 'help')"
   exit 1
fi

# Créer le répertoire de sauvegarde si nécessaire
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/logs"

# Exécution
main "$@"