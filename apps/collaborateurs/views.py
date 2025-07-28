from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Collaborateur

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenue {user}!')
                
                # Redirection selon le rôle
                next_url = request.GET.get('next', '/dashboard/')
                return redirect(next_url)
            else:
                messages.error(request, 'Email ou mot de passe incorrect.')
        else:
            messages.error(request, 'Veuillez renseigner tous les champs.')
    
    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')

@login_required
def profile_view(request):
    """Vue pour afficher le profil de l'utilisateur connecté"""
    return render(request, 'collaborateurs/profile.html', {
        'collaborateur': request.user,
        'permissions': request.user.get_all_permissions()
    })

@login_required
def check_permission_ajax(request):
    """Vue AJAX pour vérifier les permissions côté client"""
    module = request.GET.get('module')
    action = request.GET.get('action')
    
    if module and action:
        has_perm = request.user.has_permission(module, action)
        return JsonResponse({'has_permission': has_perm})
    
    return JsonResponse({'has_permission': False})