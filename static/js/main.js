/**
 * Scripts JavaScript principaux pour AIC Métallurgie
 * Gestion des interactions utilisateur et fonctionnalités communes
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 AIC Métallurgie - Système initialisé');
    
    // Initialisation des composants
    initializeComponents();
    initializeAlerts();
    initializeTooltips();
    initializeSearch();
    initializeNavigation();
    
    // Gestion des notifications
    initializeNotifications();
    
    // Animation au scroll
    initializeScrollAnimations();
});

/**
 * Initialise tous les composants Bootstrap
 */
function initializeComponents() {
    // Initialisation des tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialisation des popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Gestion des alertes automatiques
 */
function initializeAlerts() {
    // Auto-hide des alertes après 5 secondes
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        // Ajouter une barre de progression
        const progressBar = document.createElement('div');
        progressBar.className = 'alert-progress';
        progressBar.style.cssText = `
            position: absolute;
            bottom: 0;
            left: 0;
            height: 3px;
            background-color: rgba(0,0,0,0.2);
            width: 100%;
            animation: alertProgress 5s linear forwards;
        `;
        
        alert.style.position = 'relative';
        alert.style.overflow = 'hidden';
        alert.appendChild(progressBar);
        
        // Auto-fermeture après 5 secondes
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // CSS pour la barre de progression
    if (!document.getElementById('alert-progress-style')) {
        const style = document.createElement('style');
        style.id = 'alert-progress-style';
        style.textContent = `
            @keyframes alertProgress {
                from { width: 100%; }
                to { width: 0%; }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Initialise les tooltips avec contenu dynamique
 */
function initializeTooltips() {
    // Tooltips pour les boutons d'action
    const actionButtons = document.querySelectorAll('.btn[data-action]');
    actionButtons.forEach(function(btn) {
        const action = btn.dataset.action;
        let tooltipText = '';
        
        switch(action) {
            case 'edit':
                tooltipText = 'Modifier cet élément';
                break;
            case 'delete':
                tooltipText = 'Supprimer cet élément';
                break;
            case 'view':
                tooltipText = 'Voir les détails';
                break;
            case 'export':
                tooltipText = 'Exporter les données';
                break;
            default:
                tooltipText = 'Action disponible';
        }
        
        btn.setAttribute('data-bs-toggle', 'tooltip');
        btn.setAttribute('data-bs-placement', 'top');
        btn.setAttribute('title', tooltipText);
        
        new bootstrap.Tooltip(btn);
    });
}

/**
 * Gestion de la recherche globale
 */
function initializeSearch() {
    const searchForm = document.querySelector('form[action*="search"]');
    const searchInput = document.querySelector('input[name="q"]');
    
    if (searchInput) {
        // Auto-complétion basique
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            if (query.length >= 2) {
                // Ici vous pouvez ajouter un appel AJAX pour l'auto-complétion
                console.log('Recherche:', query);
            }
        });
        
        // Raccourci clavier Ctrl+K pour focus sur recherche
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        });
        
        // Placeholder dynamique
        const placeholders = [
            'Rechercher un lancement...',
            'Nom d\'un collaborateur...',
            'Code affaire...',
            'Nom d\'atelier...'
        ];
        
        let currentPlaceholder = 0;
        setInterval(function() {
            if (!searchInput.value && document.activeElement !== searchInput) {
                searchInput.placeholder = placeholders[currentPlaceholder];
                currentPlaceholder = (currentPlaceholder + 1) % placeholders.length;
            }
        }, 3000);
    }
}

/**
 * Améliorer la navigation
 */
function initializeNavigation() {
    // Marquer l'élément actif dans la navigation
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && currentPath.startsWith(href) && href !== '/') {
            link.classList.add('active');
            // Si c'est dans un dropdown, activer aussi le parent
            const dropdown = link.closest('.dropdown');
            if (dropdown) {
                dropdown.querySelector('.dropdown-toggle').classList.add('active');
            }
        }
    });
    
    // Effet de ripple sur les boutons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.height, rect.width);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.6);
                transform: scale(0);
                animation: ripple-effect 0.6s linear;
                left: ${x}px;
                top: ${y}px;
                width: ${size}px;
                height: ${size}px;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // CSS pour l'effet ripple
    if (!document.getElementById('ripple-style')) {
        const style = document.createElement('style');
        style.id = 'ripple-style';
        style.textContent = `
            @keyframes ripple-effect {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Système de notifications
 */
function initializeNotifications() {
    // Simuler des notifications (à remplacer par des vraies données)
    const notificationBadge = document.querySelector('.navbar .badge');
    const notificationDropdown = document.querySelector('.dropdown-menu');
    
    if (notificationBadge) {
        // Animation du badge quand il y a de nouvelles notifications
        function animateNotificationBadge() {
            notificationBadge.style.animation = 'none';
            notificationBadge.offsetHeight; // Force reflow
            notificationBadge.style.animation = 'bounce 0.5s ease';
        }
        
        // Exemple: nouvelle notification après 10 secondes
        setTimeout(() => {
            const currentCount = parseInt(notificationBadge.textContent);
            notificationBadge.textContent = currentCount + 1;
            animateNotificationBadge();
        }, 10000);
    }
    
    // CSS pour l'animation bounce
    if (!document.getElementById('notification-style')) {
        const style = document.createElement('style');
        style.id = 'notification-style';
        style.textContent = `
            @keyframes bounce {
                0%, 20%, 60%, 100% {
                    transform: translateY(0);
                }
                40% {
                    transform: translateY(-10px);
                }
                80% {
                    transform: translateY(-5px);
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Animations au scroll
 */
function initializeScrollAnimations() {
    // Fonction pour vérifier si un élément est visible
    function isElementInViewport(el) {
        const rect = el.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
    
    // Animer les cartes quand elles deviennent visibles
    const cards = document.querySelectorAll('.card');
    function checkCardsVisibility() {
        cards.forEach(function(card, index) {
            if (isElementInViewport(card) && !card.classList.contains('animate-in')) {
                setTimeout(() => {
                    card.classList.add('animate-in');
                    card.style.animation = 'slideInUp 0.5s ease forwards';
                }, index * 100); // Délai pour effet cascade
            }
        });
    }
    
    // Vérifier au chargement et au scroll
    checkCardsVisibility();
    window.addEventListener('scroll', checkCardsVisibility);
    
    // CSS pour l'animation slideInUp
    if (!document.getElementById('scroll-animation-style')) {
        const style = document.createElement('style');
        style.id = 'scroll-animation-style';
        style.textContent = `
            .card {
                opacity: 0;
                transform: translateY(20px);
            }
            
            @keyframes slideInUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .animate-in {
                opacity: 1 !important;
                transform: translateY(0) !important;
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Utilitaires globaux
 */
window.AIC = {
    // Afficher une notification toast
    showToast: function(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Container pour les toasts
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1055';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Supprimer après fermeture
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    },
    
    // Confirmer une action
    confirmAction: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },
    
    // Loading spinner pour boutons
    showButtonLoading: function(button) {
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span class="loading-spinner me-2"></span>Chargement...';
        
        return function() {
            button.disabled = false;
            button.innerHTML = originalText;
        };
    }
};

// Gestion des erreurs JavaScript
window.addEventListener('error', function(e) {
    console.error('Erreur JavaScript:', e.error);
    
    // En développement, afficher l'erreur
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        AIC.showToast(`Erreur: ${e.message}`, 'danger');
    }
});

console.log('✅ Scripts AIC Métallurgie chargés avec succès');
// JavaScript principal pour AIC Métallurgie
document.addEventListener('DOMContentLoaded', function() {
    
    // Gestion des dropdowns
    const dropdowns = document.querySelectorAll('[data-toggle="dropdown"]');
    dropdowns.forEach(function(dropdown) {
        dropdown.addEventListener('click', function(e) {
            e.preventDefault();
            const menu = this.nextElementSibling;
            if (menu) {
                menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            }
        });
    });

    // Fermer les dropdowns en cliquant ailleurs
    document.addEventListener('click', function(e) {
        if (!e.target.matches('[data-toggle="dropdown"]')) {
            const dropdownMenus = document.querySelectorAll('.dropdown-menu');
            dropdownMenus.forEach(function(menu) {
                menu.style.display = 'none';
            });
        }
    });

    // Gestion des alerts avec auto-fermeture
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        if (alert.classList.contains('alert-success')) {
            setTimeout(function() {
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.remove();
                }, 300);
            }, 3000);
        }
    });

    // Animation des compteurs sur le dashboard
    const counters = document.querySelectorAll('.small-box h3');
    counters.forEach(function(counter) {
        const target = parseInt(counter.innerText);
        const increment = target / 50;
        let current = 0;
        
        const timer = setInterval(function() {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.innerText = Math.floor(current);
        }, 30);
    });

    console.log('AIC Métallurgie - Système initialisé');
});