# apps/core/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Role, Permission
from .models import Affaire
from apps.collaborateurs.models import Collaborateur

class RoleForm(forms.ModelForm):
    """Formulaire pour créer/modifier un rôle"""
    
    class Meta:
        model = Role
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du rôle',
                'maxlength': 100
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Description du rôle',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': 'Nom du rôle',
            'description': 'Description',
            'is_active': 'Rôle actif'
        }
    
    def clean_name(self):
        """Validation du nom du rôle"""
        name = self.cleaned_data.get('name')
        
        if not name:
            raise ValidationError('Le nom du rôle est obligatoire.')
        
        # Vérifier l'unicité (en excluant l'instance actuelle si modification)
        queryset = Role.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError('Un rôle avec ce nom existe déjà.')
        
        return name
    
    def save(self, commit=True):
        """Sauvegarde personnalisée du rôle"""
        role = super().save(commit=False)
        
        # Les nouveaux rôles ne sont jamais des rôles système
        if not role.pk:
            role.is_system_role = False
        
        if commit:
            role.save()
        
        return role


class RolePermissionForm(forms.Form):
    """Formulaire pour gérer les permissions d'un rôle"""
    
    def __init__(self, *args, **kwargs):
        self.role = kwargs.pop('role', None)
        super().__init__(*args, **kwargs)
        
        # Créer les champs de permissions dynamiquement
        permissions = Permission.objects.all().order_by('module', 'action')
        
        # Grouper les permissions par module
        modules = {}
        for permission in permissions:
            if permission.module not in modules:
                modules[permission.module] = []
            modules[permission.module].append(permission)
        
        # Créer les champs pour chaque permission
        for module, module_permissions in modules.items():
            for permission in module_permissions:
                field_name = f'permission_{permission.id}'
                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label=f'{permission.get_module_display()} - {permission.get_action_display()}',
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input permission-checkbox',
                        'data-module': permission.module,
                        'data-action': permission.action,
                    })
                )
                
                # Pré-cocher si le rôle a déjà cette permission
                if self.role and self.role.permissions.filter(id=permission.id).exists():
                    self.fields[field_name].initial = True
    
    def save(self, role):
        """Sauvegarde les permissions pour le rôle"""
        if not role:
            return
        
        # Récupérer toutes les permissions sélectionnées
        selected_permissions = []
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('permission_') and value:
                permission_id = int(field_name.replace('permission_', ''))
                try:
                    permission = Permission.objects.get(id=permission_id)
                    selected_permissions.append(permission)
                except Permission.DoesNotExist:
                    pass
        
        # Assigner les permissions au rôle
        role.permissions.set(selected_permissions)
        return role


class RoleSearchForm(forms.Form):
    """Formulaire de recherche et filtrage des rôles"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher un rôle...',
            'id': 'search-input'
        }),
        label='Recherche'
    )
    
    STATUS_CHOICES = [
        ('', 'Tous les statuts'),
        ('active', 'Actifs seulement'),
        ('inactive', 'Inactifs seulement'),
        ('system', 'Rôles système'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Statut'
    )


class BulkRoleActionForm(forms.Form):
    """Formulaire pour les actions en lot sur les rôles"""
    
    ACTION_CHOICES = [
        ('activate', 'Activer'),
        ('deactivate', 'Désactiver'),
        ('delete', 'Supprimer'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Action'
    )
    
    role_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Je confirme cette action'
    )
    
    def clean_role_ids(self):
        """Validation des IDs de rôles"""
        role_ids = self.cleaned_data.get('role_ids', '')
        
        try:
            ids = [int(id) for id in role_ids.split(',') if id.strip()]
        except ValueError:
            raise ValidationError('IDs de rôles invalides.')
        
        if not ids:
            raise ValidationError('Aucun rôle sélectionné.')
        
        # Vérifier que tous les rôles existent
        existing_roles = Role.objects.filter(id__in=ids)
        if existing_roles.count() != len(ids):
            raise ValidationError('Certains rôles sélectionnés n\'existent pas.')
        
        return ids


class PermissionForm(forms.ModelForm):
    """Formulaire pour créer/modifier une permission"""
    
    class Meta:
        model = Permission
        fields = ['name', 'module', 'action', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la permission'
            }),
            'module': forms.Select(attrs={
                'class': 'form-select'
            }),
            'action': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Description de la permission',
                'rows': 3
            })
        }
        labels = {
            'name': 'Nom',
            'module': 'Module',
            'action': 'Action',
            'description': 'Description'
        }
    
    def clean(self):
        """Validation globale du formulaire"""
        cleaned_data = super().clean()
        module = cleaned_data.get('module')
        action = cleaned_data.get('action')
        
        if module and action:
            # Vérifier l'unicité de la combinaison module/action
            queryset = Permission.objects.filter(module=module, action=action)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('Une permission pour cette combinaison module/action existe déjà.')
        
        return cleaned_data

class AffaireForm(forms.ModelForm):
    """Formulaire pour créer/modifier une affaire"""
    
    class Meta:
        model = Affaire
        fields = ['code_affaire', 'client', 'livrable', 'responsable_affaire', 
                 'date_debut', 'date_fin_prevue', 'statut']
        widgets = {
            'code_affaire': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: AFF-2024-001',
                'maxlength': 50,
                'required': True  # Seul champ obligatoire
            }),
            'client': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du client (optionnel)',
                'maxlength': 100
            }),
            'livrable': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Description détaillée du livrable (optionnel)',
                'rows': 4
            }),
            'responsable_affaire': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_debut': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_fin_prevue': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'statut': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'code_affaire': 'Code de l\'affaire',
            'client': 'Client',
            'livrable': 'Description du livrable',
            'responsable_affaire': 'Responsable de l\'affaire',
            'date_debut': 'Date de début',
            'date_fin_prevue': 'Date de fin prévue',
            'statut': 'Statut'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les collaborateurs pour ne montrer que ceux qui sont actifs
        self.fields['responsable_affaire'].queryset = Collaborateur.objects.filter(
            is_active=True
        ).order_by('nom_collaborateur', 'prenom_collaborateur')
        
        # Ajouter un choix vide pour tous les champs optionnels
        self.fields['responsable_affaire'].empty_label = "Sélectionner un responsable (optionnel)"
        
        # Rendre SEUL le code_affaire obligatoire
        self.fields['code_affaire'].required = True
        self.fields['client'].required = False
        self.fields['livrable'].required = False
        self.fields['responsable_affaire'].required = False
        self.fields['date_debut'].required = False
        self.fields['date_fin_prevue'].required = False
        self.fields['statut'].required = False  # A une valeur par défaut
    
    def clean_code_affaire(self):
        """Validation du code affaire (SANS vérification d'unicité)"""
        code_affaire = self.cleaned_data.get('code_affaire')
        
        if not code_affaire:
            raise ValidationError('Le code affaire est obligatoire.')
        
        # SUPPRIMÉ: Plus de vérification d'unicité car les doublons sont maintenant autorisés
        return code_affaire
    
    def clean(self):
        """Validation globale du formulaire - seulement si les dates sont remplies"""
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin_prevue = cleaned_data.get('date_fin_prevue')
        
        # Validation des dates seulement si les deux sont renseignées
        if date_debut and date_fin_prevue:
            if date_fin_prevue <= date_debut:
                raise ValidationError('La date de fin prévue doit être postérieure à la date de début.')
        
        return cleaned_data


class AffaireQuickCreateForm(forms.ModelForm):
    """Formulaire rapide pour créer une affaire avec juste le code"""
    
    class Meta:
        model = Affaire
        fields = ['code_affaire']
        widgets = {
            'code_affaire': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: AFF-2024-001',
                'maxlength': 50,
                'required': True
            })
        }
        labels = {
            'code_affaire': 'Code de l\'affaire'
        }
    
    def clean_code_affaire(self):
        """Validation du code affaire (SANS vérification d'unicité)"""
        code_affaire = self.cleaned_data.get('code_affaire')
        
        if not code_affaire:
            raise ValidationError('Le code affaire est obligatoire.')
        
        # SUPPRIMÉ: Plus de vérification d'unicité car les doublons sont maintenant autorisés
        return code_affaire


class AffaireSearchForm(forms.Form):
    """Formulaire de recherche et filtrage des affaires"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par code, client ou livrable...',
            'id': 'search-input'
        }),
        label='Recherche'
    )
    
    statut = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Tous les statuts'),
            ('en_cours', 'En cours'),
            ('terminee', 'Terminée'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Statut'
    )
    
    completion = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Toutes les affaires'),
            ('complete', 'Affaires complètes'),
            ('incomplete', 'Affaires incomplètes'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='État de completion'
    )
    
    responsable = forms.ModelChoiceField(
        queryset=Collaborateur.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Responsable',
        empty_label="Tous les responsables"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Définir les choix de responsables
        self.fields['responsable'].queryset = Collaborateur.objects.filter(
            affaires_responsable__isnull=False
        ).distinct().order_by('nom_collaborateur', 'prenom_collaborateur')