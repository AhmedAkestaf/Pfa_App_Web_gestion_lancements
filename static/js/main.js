// ===== NAVBAR FUNCTIONALITY =====

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== ACTIVE LINK MANAGEMENT =====
    function setActiveNavLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }
    
    // ===== NOTIFICATION MANAGEMENT =====
    function updateNotificationCount() {
        const countElement = document.getElementById('notification-count');
        if (countElement) {
            // Simulate real-time updates (replace with actual API call)
            const count = Math.floor(Math.random() * 10);
            countElement.textContent = count;
            countElement.style.display = count > 0 ? 'block' : 'none';
        }
    }
    
    // ===== DROPDOWN ENHANCEMENTS =====
    function enhanceDropdowns() {
        const dropdowns = document.querySelectorAll('.dropdown-toggle');
        
        dropdowns.forEach(dropdown => {
            // Add keyboard navigation
            dropdown.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
            
            // Add hover effect for desktop
            if (window.innerWidth > 991) {
                const dropdownMenu = this.nextElementSibling;
                let hoverTimeout;
                
                dropdown.parentElement.addEventListener('mouseenter', function() {
                    clearTimeout(hoverTimeout);
                    const bsDropdown = new bootstrap.Dropdown(dropdown);
                    bsDropdown.show();
                });
                
                dropdown.parentElement.addEventListener('mouseleave', function() {
                    hoverTimeout = setTimeout(() => {
                        const bsDropdown = bootstrap.Dropdown.getInstance(dropdown);
                        if (bsDropdown) bsDropdown.hide();
                    }, 300);
                });
            }
        });
    }
    
    // ===== MOBILE MENU MANAGEMENT =====
    function manageMobileMenu() {
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');
        
        if (navbarToggler && navbarCollapse) {
            // Close mobile menu when clicking on a link
            const navLinks = navbarCollapse.querySelectorAll('.nav-link:not(.dropdown-toggle)');
            navLinks.forEach(link => {
                link.addEventListener('click', () => {
                    if (navbarCollapse.classList.contains('show')) {
                        navbarToggler.click();
                    }
                });
            });
        }
    }
    
    // ===== USER SESSION MANAGEMENT =====
    function updateUserSession() {
        const sessionElement = document.querySelector('.dropdown-item-text small');
        if (sessionElement && sessionElement.textContent.includes('Connecté depuis')) {
            // Update connection time every minute
            setInterval(() => {
                // This would typically fetch from server
                // For now, just update the display
                const now = new Date();
                const loginTime = new Date(now.getTime() - Math.random() * 3600000); // Random time within last hour
                const timeDiff = Math.floor((now - loginTime) / 60000); // minutes
                
                let timeText = '';
                if (timeDiff < 60) {
                    timeText = `${timeDiff} minute${timeDiff > 1 ? 's' : ''}`;
                } else {
                    const hours = Math.floor(timeDiff / 60);
                    timeText = `${hours} heure${hours > 1 ? 's' : ''}`;
                }
                
                sessionElement.innerHTML = `<i class="fas fa-clock me-1"></i>Connecté depuis ${timeText}`;
            }, 60000); // Update every minute
        }
    }
    
    // ===== NOTIFICATION INTERACTIONS =====
    function setupNotificationHandlers() {
        const notificationItems = document.querySelectorAll('#notificationsDropdown + ul .dropdown-item');
        
        notificationItems.forEach(item => {
            if (!item.classList.contains('text-center') && !item.querySelector('.dropdown-header')) {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    // Mark as read (add visual feedback)
                    this.style.opacity = '0.7';
                    this.style.backgroundColor = '#f8f9fa';
                    
                    // Update notification count
                    const countElement = document.getElementById('notification-count');
                    if (countElement) {
                        let count = parseInt(countElement.textContent) - 1;
                        countElement.textContent = Math.max(0, count);
                        if (count <= 0) {
                            countElement.style.display = 'none';
                        }
                    }
                    
                    // Here you would typically send an AJAX request to mark as read
                    console.log('Notification marked as read');
                });
            }
        });
    }
    
    // ===== RESPONSIVE ADJUSTMENTS =====
    function handleResize() {
        window.addEventListener('resize', function() {
            // Reinitialize dropdown behaviors based on screen size
            if (window.innerWidth <= 991) {
                // Mobile: disable hover effects
                document.querySelectorAll('.dropdown-toggle').forEach(dropdown => {
                    dropdown.parentElement.removeEventListener('mouseenter', () => {});
                    dropdown.parentElement.removeEventListener('mouseleave', () => {});
                });
            } else {
                // Desktop: enable hover effects
                enhanceDropdowns();
            }
        });
    }
    
    // ===== ACCESSIBILITY IMPROVEMENTS =====
    function improveAccessibility() {
        // Add ARIA labels where missing
        const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
        dropdownToggles.forEach(toggle => {
            if (!toggle.getAttribute('aria-label')) {
                const text = toggle.textContent.trim();
                toggle.setAttribute('aria-label', `Ouvrir le menu ${text}`);
            }
        });
        
        // Improve focus management
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                // Close all open dropdowns
                const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
                openDropdowns.forEach(menu => {
                    const toggle = menu.previousElementSibling;
                    const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
                    if (bsDropdown) bsDropdown.hide();
                });
            }
        });
    }
    
    // ===== INITIALIZE ALL FUNCTIONALITY =====
    function initNavbar() {
        setActiveNavLink();
        enhanceDropdowns();
        manageMobileMenu();
        updateUserSession();
        setupNotificationHandlers();
        handleResize();
        improveAccessibility();
        initFooter();
        initDashboard(); 
        initBaseTemplate();
        // Update notifications periodically
        updateNotificationCount();
        setInterval(updateNotificationCount, 30000); // Every 30 seconds
        
        console.log('Navbar initialized successfully');
    }
    
    // Start everything
    initNavbar();
});

// ===== UTILITY FUNCTIONS =====

// Function to manually trigger notification update (can be called from other scripts)
window.updateNavbarNotifications = function(count) {
    const countElement = document.getElementById('notification-count');
    if (countElement) {
        countElement.textContent = count;
        countElement.style.display = count > 0 ? 'block' : 'none';
    }
};

// Function to add new notification (can be called from other scripts)
window.addNavbarNotification = function(notification) {
    const notificationsList = document.querySelector('#notificationsDropdown + ul');
    if (notificationsList) {
        const header = notificationsList.querySelector('.dropdown-header');
        const newItem = document.createElement('li');
        newItem.innerHTML = `
            <a class="dropdown-item" href="#">
                <small class="text-muted">À l'instant</small><br>
                <strong>${notification.title}</strong><br>
                <small>${notification.message}</small>
            </a>
        `;
        
        // Insert after header
        header.parentElement.insertBefore(newItem, header.nextElementSibling);
        
        // Update count
        const countElement = document.getElementById('notification-count');
        if (countElement) {
            const currentCount = parseInt(countElement.textContent) || 0;
            window.updateNavbarNotifications(currentCount + 1);
        }
    }
};

// ===== FOOTER FUNCTIONALITY ====
    
    function initFooter() {
        // ===== REAL-TIME CLOCK UPDATE =====
        function updateFooterTime() {
            const timeElements = document.querySelectorAll('footer small:contains(":")');
            if (timeElements.length > 0) {
                const now = new Date();
                const timeString = now.toLocaleString('fr-FR', {
                    day: '2-digit',
                    month: '2-digit', 
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                // Update footer timestamp
                const footerInfo = document.querySelector('footer small');
                if (footerInfo && footerInfo.textContent.includes('|')) {
                    const parts = footerInfo.textContent.split('|');
                    parts[parts.length - 1] = ` ${timeString}`;
                    footerInfo.textContent = parts.join(' |');
                }
            }
        }
        
        // ===== SMOOTH SCROLL FOR FOOTER LINKS =====
        const footerLinks = document.querySelectorAll('footer a[href^="#"]');
        footerLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
        
        // ===== EASTER EGG FOR PYTHON ICON =====
        const pythonIcon = document.querySelector('footer .fa-python');
        if (pythonIcon) {
            let clickCount = 0;
            pythonIcon.addEventListener('click', function() {
                clickCount++;
                if (clickCount === 5) {
                    this.style.animation = 'bounce 0.5s infinite';
                    setTimeout(() => {
                        this.style.animation = 'bounce 2s infinite';
                        clickCount = 0;
                    }, 2000);
                }
            });
        }
        
        // Update time every minute
        updateFooterTime();
        setInterval(updateFooterTime, 60000);
        
        console.log('Footer initialized successfully');
    }
    
    // Add this call in your existing initNavbar() function:
    // initFooter();

    // ===== BASE TEMPLATE FUNCTIONALITY =====     
    function initBaseTemplate() {
        // ===== AUTO-DISMISS ALERTS =====
        function setupAlertDismissal() {
            const alerts = document.querySelectorAll('.alert:not(.alert-important)');
            alerts.forEach(alert => {
                // Auto-dismiss after 5 seconds (except errors)
                if (!alert.classList.contains('alert-danger') && !alert.classList.contains('alert-error')) {
                    setTimeout(() => {
                        const bsAlert = new bootstrap.Alert(alert);
                        bsAlert.close();
                    }, 5000);
                }
                
                // Add smooth fade out animation
                alert.addEventListener('closed.bs.alert', function() {
                    this.style.opacity = '0';
                    this.style.transform = 'translateX(100%)';
                });
            });
        }
        
        // ===== BREADCRUMB ENHANCEMENTS =====
        function enhanceBreadcrumb() {
            const breadcrumbLinks = document.querySelectorAll('.breadcrumb-item a');
            breadcrumbLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    // Add loading state to clicked breadcrumb
                    this.innerHTML += ' <i class="fas fa-spinner fa-spin ms-1"></i>';
                });
            });
        }
        
        // ===== FORM ENHANCEMENTS =====
        function enhanceForms() {
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.addEventListener('submit', function(e) {
                    const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                    if (submitBtn) {
                        // Prevent double submission
                        submitBtn.disabled = true;
                        const originalText = submitBtn.textContent;
                        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Traitement...';
                        
                        // Re-enable after 3 seconds (fallback)
                        setTimeout(() => {
                            submitBtn.disabled = false;
                            submitBtn.textContent = originalText;
                        }, 3000);
                    }
                    
                    // Add loading class to main content
                    document.querySelector('.main-content')?.classList.add('loading');
                });
            });
        }
        
        // ===== SMOOTH PAGE TRANSITIONS =====
        function setupPageTransitions() {
            const links = document.querySelectorAll('a[href^="/"], a[href^="{% url"]');
            links.forEach(link => {
                if (!link.getAttribute('target') && !link.classList.contains('dropdown-item')) {
                    link.addEventListener('click', function(e) {
                        // Add fade out effect
                        document.querySelector('.main-content')?.classList.add('loading');
                    });
                }
            });
        }
        
        // ===== KEYBOARD SHORTCUTS =====
        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', function(e) {
                // Ctrl+H = Go to home/dashboard
                if (e.ctrlKey && e.key === 'h') {
                    e.preventDefault();
                    const homeLink = document.querySelector('a[href*="dashboard"]');
                    if (homeLink) homeLink.click();
                }
                
                // Escape = Close all modals and alerts
                if (e.key === 'Escape') {
                    // Close alerts
                    document.querySelectorAll('.alert .btn-close').forEach(btn => btn.click());
                    
                    // Close modals
                    document.querySelectorAll('.modal.show').forEach(modal => {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    });
                }
            });
        }
        
        // ===== TOOLTIP AND POPOVER INITIALIZATION =====
        function initBootstrapComponents() {
            // Initialize tooltips
            const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltips.forEach(tooltip => {
                new bootstrap.Tooltip(tooltip);
            });
            
            // Initialize popovers
            const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
            popovers.forEach(popover => {
                new bootstrap.Popover(popover);
            });
        }
        
        // ===== ERROR HANDLING =====
        function setupErrorHandling() {
            window.addEventListener('error', function(e) {
                console.error('JavaScript error:', e.error);
                
                // Remove loading states on error
                document.querySelectorAll('.loading').forEach(el => {
                    el.classList.remove('loading');
                });
                
                // Re-enable disabled buttons
                document.querySelectorAll('button:disabled').forEach(btn => {
                    btn.disabled = false;
                });
            });
        }
        
        // ===== INITIALIZE ALL BASE FUNCTIONALITY =====
        setupAlertDismissal();
        enhanceBreadcrumb();
        enhanceForms();
        setupPageTransitions();
        setupKeyboardShortcuts();
        initBootstrapComponents();
        setupErrorHandling();
        
        console.log('Base template initialized successfully');
    }
    
    // Add this call in your existing initNavbar() function:
    // initBaseTemplate();

    // ===== DASHBOARD FUNCTIONALITY ===== 
    
    function initDashboard() {
        // ===== REAL-TIME STATS UPDATE =====
        function updateDashboardStats() {
            const statCards = document.querySelectorAll('.small-box .inner h3');
            
            // Simulate real-time updates (replace with actual API calls)
            statCards.forEach(statElement => {
                const currentValue = parseInt(statElement.textContent);
                
                // Add subtle animation for value changes
                statElement.style.transition = 'all 0.5s ease';
                
                // Example: Random small changes (replace with real data)
                if (Math.random() > 0.8) { // 20% chance of update
                    const change = Math.floor(Math.random() * 3) - 1; // -1, 0, or 1
                    const newValue = Math.max(0, currentValue + change);
                    
                    if (newValue !== currentValue) {
                        statElement.style.transform = 'scale(1.1)';
                        setTimeout(() => {
                            statElement.textContent = newValue;
                            statElement.style.transform = 'scale(1)';
                        }, 250);
                    }
                }
            });
        }
        
        // ===== INTERACTIVE STAT CARDS =====
        function enhanceStatCards() {
            const statCards = document.querySelectorAll('.small-box');
            
            statCards.forEach(card => {
                // Add click feedback
                card.addEventListener('click', function(e) {
                    if (!e.target.classList.contains('small-box-footer')) {
                        this.style.transform = 'scale(0.98)';
                        setTimeout(() => {
                            this.style.transform = '';
                        }, 150);
                    }
                });
                
                // Add loading state when clicking footer links
                const footerLink = card.querySelector('.small-box-footer');
                if (footerLink) {
                    footerLink.addEventListener('click', function(e) {
                        e.preventDefault();
                        card.classList.add('dashboard-loading');
                        
                        // Remove loading after 2 seconds (replace with actual navigation)
                        setTimeout(() => {
                            card.classList.remove('dashboard-loading');
                            // Here you would typically navigate to the actual page
                            console.log('Navigating to:', this.getAttribute('href'));
                        }, 2000);
                    });
                }
            });
        }
        
        // ===== ACTION BUTTONS ENHANCEMENT =====
        function enhanceActionButtons() {
            const actionButtons = document.querySelectorAll('.btn-lg.w-100');
            
            actionButtons.forEach(button => {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    // Add ripple effect
                    const ripple = document.createElement('span');
                    ripple.style.cssText = `
                        position: absolute;
                        border-radius: 50%;
                        background: rgba(255,255,255,0.6);
                        transform: scale(0);
                        animation: ripple 0.6s linear;
                        pointer-events: none;
                    `;
                    
                    const rect = this.getBoundingClientRect();
                    const size = Math.max(rect.width, rect.height);
                    ripple.style.width = ripple.style.height = size + 'px';
                    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
                    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
                    
                    this.style.position = 'relative';
                    this.style.overflow = 'hidden';
                    this.appendChild(ripple);
                    
                    setTimeout(() => ripple.remove(), 600);
                    
                    // Simulate action (replace with actual functionality)
                    console.log('Action triggered:', this.querySelector('div').textContent);
                });
            });
        }
        
        // ===== TIMELINE ANIMATION =====
        function animateTimeline() {
            const timelineItems = document.querySelectorAll('.timeline-item');
            
            // Intersection Observer for scroll-triggered animations
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateX(0)';
                    }
                });
            }, { threshold: 0.5 });
            
            timelineItems.forEach((item, index) => {
                item.style.opacity = '0';
                item.style.transform = 'translateX(-30px)';
                item.style.transition = `all 0.6s ease ${index * 0.1}s`;
                observer.observe(item);
            });
        }
        
        // ===== USER CARD ENHANCEMENTS =====
        function enhanceUserCard() {
            const avatarCircle = document.querySelector('.avatar-circle');
            const profileLink = document.querySelector('a[href*="profile"]');
            
            if (avatarCircle) {
                // Add hover effect to avatar
                avatarCircle.addEventListener('mouseenter', function() {
                    this.style.transform = 'scale(1.1) rotate(5deg)';
                });
                
                avatarCircle.addEventListener('mouseleave', function() {
                    this.style.transform = 'scale(1) rotate(0deg)';
                });
            }
            
            if (profileLink) {
                profileLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    // Add loading effect
                    this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Chargement...';
                    
                    setTimeout(() => {
                        // Navigate to profile (replace with actual navigation)
                        console.log('Navigating to profile');
                        this.innerHTML = '<i class="fas fa-eye me-1"></i>Voir mon profil';
                    }, 1500);
                });
            }
        }
        
        // ===== HELP LINKS TRACKING =====
        function trackHelpLinks() {
            const helpLinks = document.querySelectorAll('.list-group-item-action');
            
            helpLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    const linkText = this.textContent.trim();
                    console.log('Help link clicked:', linkText);
                    
                    // Add visual feedback
                    const icon = this.querySelector('i');
                    if (icon) {
                        const originalClass = icon.className;
                        icon.className = 'fas fa-spinner fa-spin me-2 text-secondary';
                        
                        setTimeout(() => {
                            icon.className = originalClass;
                        }, 1000);
                    }
                });
            });
        }
        
        // ===== DASHBOARD REFRESH =====
        function setupDashboardRefresh() {
            // Add refresh button to dashboard
            const dashboardCard = document.querySelector('.dashboard-main-card');
            if (dashboardCard) {
                const refreshBtn = document.createElement('button');
                refreshBtn.className = 'btn btn-sm btn-outline-light position-absolute';
                refreshBtn.style.cssText = 'top: 1rem; right: 1rem; z-index: 3;';
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
                refreshBtn.title = 'Actualiser les données';
                
                refreshBtn.addEventListener('click', function() {
                    this.querySelector('i').style.animation = 'spin 1s linear';
                    
                    // Refresh dashboard data
                    updateDashboardStats();
                    
                    setTimeout(() => {
                        this.querySelector('i').style.animation = '';
                    }, 1000);
                });
                
                dashboardCard.appendChild(refreshBtn);
            }
        }
        
        // ===== WELCOME MESSAGE PERSONALIZATION =====
        function personalizeWelcome() {
            const welcomeAlert = document.querySelector('.dashboard-welcome-alert');
            if (welcomeAlert) {
                // Add close functionality
                const closeBtn = document.createElement('button');
                closeBtn.className = 'btn-close float-end';
                closeBtn.addEventListener('click', function() {
                    welcomeAlert.style.animation = 'fadeOut 0.5s ease';
                    setTimeout(() => welcomeAlert.remove(), 500);
                });
                
                welcomeAlert.querySelector('h5').appendChild(closeBtn);
                
                // Add different messages based on time of day
                const hour = new Date().getHours();
                const greetings = {
                    morning: 'Bon matin',
                    afternoon: 'Bon après-midi', 
                    evening: 'Bonne soirée'
                };
                
                let greeting = 'Bonjour';
                if (hour < 12) greeting = greetings.morning;
                else if (hour < 18) greeting = greetings.afternoon;
                else greeting = greetings.evening;
                
                // Update welcome message if it exists
                const welcomeTitle = document.querySelector('.dashboard-main-card h3');
                if (welcomeTitle && welcomeTitle.textContent.includes('Bienvenue')) {
                    welcomeTitle.innerHTML = welcomeTitle.innerHTML.replace('Bienvenue', greeting);
                }
            }
        }
        
        // ===== INITIALIZE ALL DASHBOARD FUNCTIONALITY =====
        enhanceStatCards();
        enhanceActionButtons();
        animateTimeline();
        enhanceUserCard();
        trackHelpLinks();
        setupDashboardRefresh();
        personalizeWelcome();
        
        // Update stats periodically
        updateDashboardStats();
        setInterval(updateDashboardStats, 30000); // Every 30 seconds
        
        console.log('Dashboard initialized successfully');
    }
    
    // Add CSS for ripple animation
    const rippleStyle = document.createElement('style');
    rippleStyle.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        @keyframes fadeOut {
            to {
                opacity: 0;
                transform: translateY(-20px);
            }
        }
    `;
    document.head.appendChild(rippleStyle);
    
    // Add this call in your existing initNavbar() function:
    // if (document.querySelector('.dashboard-main-card')) initDashboard(); 