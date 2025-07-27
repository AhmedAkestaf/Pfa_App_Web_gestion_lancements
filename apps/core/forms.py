from django import forms
from django.core.exceptions import ValidationError
from .models import Role, Permission

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