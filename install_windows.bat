@echo off
:: =============================================================================
:: Script d'installation automatique Windows - Système de Gestion des Lancements
:: AIC Métallurgie
:: =============================================================================

setlocal EnableDelayedExpansion

:: Configuration des couleurs
for /F %%a in ('"prompt $E$S & echo on & for %%b in (1) do rem"') do set ESC=%%a

set GREEN=%ESC%[92m
set YELLOW=%ESC%[93m
set RED=%ESC%[91m
set BLUE=%ESC%[94m
set NC=%ESC%[0m

:: Variables de configuration
set PROJECT_NAME=GESTION_LANCEMENTS
set INSTALL_DIR=C:\gestion-lancements
set VENV_NAME=venv_lancements
set DB_NAME=gestion_lancements_aic
set DB_USER=aic_user
set DB_PASSWORD=password123

echo %BLUE%========================================%NC%
echo %BLUE% INSTALLATION - SYSTÈME DE GESTION DES LANCEMENTS %NC%
echo %BLUE%========================================%NC%
echo %GREEN%AIC Métallurgie - Version 1.0.0%NC%
echo.

:: Vérifier les permissions administrateur
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% Ce script doit être exécuté en tant qu'administrateur!
    echo Faites un clic droit sur le fichier et sélectionnez "Exécuter en tant qu'administrateur"
    pause
    exit /b 1
)

echo %GREEN%[INFO]%NC% Permissions administrateur confirmées
echo.

:: Vérifier si Python est installé
echo %BLUE%=== ÉTAPE 1: VÉRIFICATION DE PYTHON ===%NC%
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% Python n'est pas installé ou pas dans le PATH!
    echo.
    echo %YELLOW%[SOLUTION]%NC% Veuillez installer Python 3.8+ depuis https://python.org
    echo N'oubliez pas de cocher "Add Python to PATH" lors de l'installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo %GREEN%[INFO]%NC% Python version: %PYTHON_VERSION%

:: Vérifier si pip est disponible
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% pip n'est pas disponible!
    echo Réinstallez Python avec pip inclus
    pause
    exit /b 1
)

:: Vérification intelligente de PostgreSQL
echo %BLUE%=== ÉTAPE 2: VÉRIFICATION DE POSTGRESQL ===%NC%
set "PSQL_FOUND=false"
set "PSQL_CMD="

:: Méthode 1: Vérifier dans le PATH
psql --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PSQL_FOUND=true"
    set "PSQL_CMD=psql"
    echo %GREEN%[INFO]%NC% PostgreSQL trouvé dans le PATH
    goto :postgresql_ok
)

:: Méthode 2: Chercher dans les emplacements standards
echo %BLUE%[INFO]%NC% Recherche de PostgreSQL dans les emplacements standards...
for %%v in (16 15 14 13 12 11) do (
    if exist "C:\Program Files\PostgreSQL\%%v\bin\psql.exe" (
        set "PSQL_FOUND=true"
        set "PSQL_CMD=C:\Program Files\PostgreSQL\%%v\bin\psql.exe"
        echo %GREEN%[INFO]%NC% PostgreSQL %%v trouvé dans C:\Program Files\PostgreSQL\%%v
        
        :: Ajouter temporairement au PATH pour cette session
        set "PATH=!PATH!;C:\Program Files\PostgreSQL\%%v\bin"
        goto :postgresql_ok
    )
)

:: Méthode 3: Chercher dans Program Files (x86)
for %%v in (16 15 14 13 12 11) do (
    if exist "C:\Program Files (x86)\PostgreSQL\%%v\bin\psql.exe" (
        set "PSQL_FOUND=true"
        set "PSQL_CMD=C:\Program Files (x86)\PostgreSQL\%%v\bin\psql.exe"
        echo %GREEN%[INFO]%NC% PostgreSQL %%v trouvé dans C:\Program Files (x86)\PostgreSQL\%%v
        
        :: Ajouter temporairement au PATH pour cette session
        set "PATH=!PATH!;C:\Program Files (x86)\PostgreSQL\%%v\bin"
        goto :postgresql_ok
    )
)

:: PostgreSQL non trouvé
echo %RED%[ERREUR]%NC% PostgreSQL n'est pas installé ou non détecté
echo.
echo %YELLOW%[SOLUTION MANUELLE]%NC%
echo 1. Téléchargez PostgreSQL depuis: https://www.postgresql.org/download/windows/
echo 2. Installez PostgreSQL avec les paramètres suivants:
echo    - Utilisateur: postgres
echo    - Mot de passe: %DB_PASSWORD%
echo    - Port: 5432
echo 3. Cochez "Add PostgreSQL to PATH" ou ajoutez manuellement le dossier bin au PATH
echo 4. Redémarrez ce script après l'installation
echo.
echo %BLUE%[INFO]%NC% Vous pouvez aussi ajouter manuellement PostgreSQL au PATH:
echo    Ajoutez le dossier: C:\Program Files\PostgreSQL\[version]\bin
echo.
pause
exit /b 1

:postgresql_ok
echo %GREEN%[INFO]%NC% PostgreSQL configuré avec: !PSQL_CMD!

:: Vérifier que le service PostgreSQL fonctionne
echo %BLUE%[INFO]%NC% Vérification du service PostgreSQL...
set "SERVICE_FOUND=false"
for %%s in (postgresql-x64-16 postgresql-x64-15 postgresql-x64-14 postgresql-15 postgresql-14 PostgreSQL) do (
    sc query "%%s" >nul 2>&1
    if !errorlevel! equ 0 (
        echo %GREEN%[INFO]%NC% Service PostgreSQL trouvé: %%s
        net start "%%s" >nul 2>&1
        set "SERVICE_FOUND=true"
        goto :service_checked
    )
)

:service_checked
if "!SERVICE_FOUND!"=="false" (
    echo %YELLOW%[ATTENTION]%NC% Service PostgreSQL non détecté automatiquement
    echo Assurez-vous que le service PostgreSQL est démarré manuellement
)

:: Créer le répertoire d'installation
echo %BLUE%=== ÉTAPE 3: CRÉATION DES RÉPERTOIRES ===%NC%
if exist "%INSTALL_DIR%" (
    echo %YELLOW%[ATTENTION]%NC% Le répertoire %INSTALL_DIR% existe déjà
    set /p continue="Continuer? Les fichiers existants seront remplacés (o/N): "
    if /i not "!continue!"=="o" (
        echo Installation annulée
        pause
        exit /b 1
    )
    rmdir /s /q "%INSTALL_DIR%" 2>nul
)

mkdir "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%\logs"
mkdir "%INSTALL_DIR%\media"
mkdir "%INSTALL_DIR%\staticfiles"
echo %GREEN%[INFO]%NC% Répertoires créés

:: Copier les fichiers du projet
echo %BLUE%=== ÉTAPE 4: COPIE DES FICHIERS DU PROJET ===%NC%
if exist "manage.py" (
    echo Copie depuis le répertoire actuel...
    xcopy /E /I /H /Y . "%INSTALL_DIR%" >nul
    echo %GREEN%[INFO]%NC% Fichiers du projet copiés
) else if exist "%PROJECT_NAME%" (
    echo Copie depuis le dossier %PROJECT_NAME%...
    xcopy /E /I /H /Y "%PROJECT_NAME%" "%INSTALL_DIR%" >nul
    echo %GREEN%[INFO]%NC% Fichiers du projet copiés depuis %PROJECT_NAME%
) else (
    echo %RED%[ERREUR]%NC% Fichiers du projet non trouvés!
    echo Assurez-vous d'exécuter le script depuis le répertoire contenant le projet Django
    echo Le script doit se trouver dans le même dossier que manage.py
    pause
    exit /b 1
)

cd /d "%INSTALL_DIR%"

:: Créer l'environnement virtuel
echo %BLUE%=== ÉTAPE 5: CRÉATION DE L'ENVIRONNEMENT VIRTUEL ===%NC%
if exist "%VENV_NAME%" (
    rmdir /s /q "%VENV_NAME%" 2>nul
)
python -m venv %VENV_NAME%
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% Échec de la création de l'environnement virtuel
    echo Vérifiez que Python est correctement installé
    pause
    exit /b 1
)
echo %GREEN%[INFO]%NC% Environnement virtuel créé

:: Activer l'environnement virtuel et installer les dépendances
echo %BLUE%=== ÉTAPE 6: INSTALLATION DES DÉPENDANCES ===%NC%
call %VENV_NAME%\Scripts\activate.bat

:: Vérifier que l'activation a fonctionné
where python | findstr "%INSTALL_DIR%" >nul
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% L'environnement virtuel n'a pas pu être activé
    pause
    exit /b 1
)

:: Mettre à jour pip
echo %BLUE%[INFO]%NC% Mise à jour de pip...
python -m pip install --upgrade pip >nul

:: Vérifier si requirements.txt existe
if not exist "requirements.txt" (
    echo %RED%[ERREUR]%NC% Le fichier requirements.txt est manquant!
    pause
    exit /b 1
)

:: Installer les dépendances
echo %BLUE%[INFO]%NC% Installation des dépendances Python...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% Échec de l'installation des dépendances
    echo Vérifiez le contenu du fichier requirements.txt
    pause
    exit /b 1
)

:: Installer waitress pour le serveur de production
pip install waitress >nul 2>&1
echo %GREEN%[INFO]%NC% Dépendances Python installées avec succès

:: Créer le fichier de configuration
echo %BLUE%=== ÉTAPE 7: CONFIGURATION DE L'ENVIRONNEMENT ===%NC%
(
echo # Configuration de production
echo DEBUG=False
echo SECRET_KEY=your-secret-key-change-this-in-production-!RANDOM!
echo ALLOWED_HOSTS=localhost,127.0.0.1,*
echo.
echo # Base de données PostgreSQL
echo DB_NAME=%DB_NAME%
echo DB_USER=%DB_USER%
echo DB_PASSWORD=%DB_PASSWORD%
echo DB_HOST=127.0.0.1
echo DB_PORT=5432
echo.
echo # Chemins de fichiers
echo STATIC_ROOT=%INSTALL_DIR%\staticfiles
echo MEDIA_ROOT=%INSTALL_DIR%\media
) > .env

echo %GREEN%[INFO]%NC% Fichier de configuration .env créé

:: Configuration de la base de données PostgreSQL
echo %BLUE%=== ÉTAPE 8: CONFIGURATION DE LA BASE DE DONNÉES ===%NC%
echo %BLUE%[INFO]%NC% Création de la base de données %DB_NAME%...

:: Créer un script SQL temporaire
(
echo DROP DATABASE IF EXISTS %DB_NAME%;
echo CREATE DATABASE %DB_NAME%;
echo \q
) > temp_db_setup.sql

:: Configurer la variable d'environnement pour le mot de passe
set PGPASSWORD=%DB_PASSWORD%

:: Exécuter le script SQL
"!PSQL_CMD!" -U postgres -h localhost -p 5432 -f temp_db_setup.sql >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%[INFO]%NC% Base de données créée avec succès
) else (
    echo %YELLOW%[ATTENTION]%NC% Impossible de créer automatiquement la base de données
    echo.
    echo %BLUE%[INFO]%NC% Configuration manuelle requise:
    echo 1. Ouvrez pgAdmin ou connectez-vous à PostgreSQL
    echo 2. Créez une base de données nommée: %DB_NAME%
    echo 3. Assurez-vous que l'utilisateur 'postgres' peut y accéder
    echo.
    set /p continue="Base de données configurée manuellement? Continuer? (o/N): "
    if /i not "!continue!"=="o" (
        del temp_db_setup.sql 2>nul
        echo Installation annulée
        pause
        exit /b 1
    )
)

del temp_db_setup.sql 2>nul

:: Test de connexion à la base de données
echo %BLUE%[INFO]%NC% Test de connexion à la base de données...
"!PSQL_CMD!" -U postgres -h localhost -p 5432 -d %DB_NAME% -c "\q" >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%[INFO]%NC% Connexion à la base de données réussie
) else (
    echo %YELLOW%[ATTENTION]%NC% Impossible de se connecter à la base de données
    echo Vérifiez que PostgreSQL fonctionne et que la base de données existe
)

:: Initialisation de Django
echo %BLUE%=== ÉTAPE 9: INITIALISATION DE DJANGO ===%NC%

:: Vérifier que manage.py existe
if not exist "manage.py" (
    echo %RED%[ERREUR]%NC% Le fichier manage.py est manquant!
    pause
    exit /b 1
)

echo %BLUE%[INFO]%NC% Création des fichiers de migration...
python manage.py makemigrations >nul 2>&1

echo %BLUE%[INFO]%NC% Exécution des migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% Échec des migrations Django
    echo Vérifiez la configuration de la base de données
    pause
    exit /b 1
)

:: Commandes supplémentaires si elles existent
if exist "*/management/commands/init_permissions.py" (
    echo %BLUE%[INFO]%NC% Initialisation des permissions...
    python manage.py init_permissions >nul 2>&1
)

if exist "*/management/commands/create_superuser_with_role.py" (
    echo %BLUE%[INFO]%NC% Création du super-utilisateur...
    python manage.py create_superuser_with_role >nul 2>&1
)

echo %BLUE%[INFO]%NC% Collecte des fichiers statiques...
python manage.py collectstatic --noinput >nul 2>&1

echo %GREEN%[INFO]%NC% Django initialisé avec succès

:: Créer les scripts de démarrage
echo %BLUE%=== ÉTAPE 10: CRÉATION DES SCRIPTS DE DÉMARRAGE ===%NC%

:: Script de démarrage principal
(
echo @echo off
echo title Gestion des Lancements - Serveur
echo cd /d "%INSTALL_DIR%"
echo call %VENV_NAME%\Scripts\activate.bat
echo echo.
echo echo ========================================
echo echo   SYSTÈME DE GESTION DES LANCEMENTS
echo echo   AIC Métallurgie
echo echo ========================================
echo echo.
echo echo Serveur démarré sur: http://localhost:8000
echo echo.
echo echo Appuyez sur Ctrl+C pour arrêter le serveur
echo echo.
echo waitress-serve --host=127.0.0.1 --port=8000 gestion_lancements.wsgi:application
) > start_server.bat

:: Script pour les commandes Django
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo call %VENV_NAME%\Scripts\activate.bat
echo python manage.py %%*
) > django_manage.bat

:: Script de vérification
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo call %VENV_NAME%\Scripts\activate.bat
echo echo Test de l'installation...
echo python -c "import django; print('Django OK -', django.get_version())"
echo python manage.py check
echo pause
) > test_installation.bat

echo %GREEN%[INFO]%NC% Scripts créés:
echo   - start_server.bat : Démarrer l'application
echo   - django_manage.bat : Commandes Django
echo   - test_installation.bat : Tester l'installation

:: Test final de l'installation
echo %BLUE%=== ÉTAPE 11: TEST FINAL ===%NC%
echo %BLUE%[INFO]%NC% Vérification de l'installation...

python -c "import django; print('Django version:', django.get_version())" 2>nul
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%NC% Problème avec l'installation Django
    pause
    exit /b 1
)

python manage.py check --deploy >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[ATTENTION]%NC% Avertissements de configuration détectés
    echo L'application devrait fonctionner mais vérifiez la configuration pour la production
) else (
    echo %GREEN%[INFO]%NC% Configuration validée
)

:: Installation terminée avec succès
echo.
echo %BLUE%========================================%NC%
echo %BLUE% INSTALLATION TERMINÉE AVEC SUCCÈS! %NC%
echo %BLUE%========================================%NC%
echo.
echo %GREEN%🎉 L'application Gestion des Lancements est installée!%NC%
echo.
echo %GREEN%📍 Informations d'installation:%NC%
echo   Répertoire: %INSTALL_DIR%
echo   Base de données: %DB_NAME%
echo   Python: %PYTHON_VERSION%
echo   PostgreSQL: !PSQL_CMD!
echo.
echo %GREEN%🚀 Pour démarrer l'application:%NC%
echo   Double-cliquez sur: %INSTALL_DIR%\start_server.bat
echo.
echo %GREEN%🌐 URL d'accès:%NC%
echo   http://localhost:8000
echo.
echo %GREEN%🔧 Scripts disponibles:%NC%
echo   • Démarrer: start_server.bat
echo   • Commandes Django: django_manage.bat [commande]
echo   • Test: test_installation.bat
echo.
echo %YELLOW%⚠️  Points importants:%NC%
echo   • Assurez-vous que le service PostgreSQL est démarré
echo   • Changez SECRET_KEY dans .env pour la production
echo   • Configurez ALLOWED_HOSTS selon votre environnement
echo   • Vérifiez les paramètres du pare-feu si nécessaire
echo.
echo %GREEN%✅ Installation réussie! Vous pouvez maintenant utiliser l'application.%NC%
echo.
echo Appuyez sur une touche pour fermer...
pause >nul