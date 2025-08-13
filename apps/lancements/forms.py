from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import Lancement
from apps.ateliers.models import Atelier, Categorie
from apps.core.models import Affaire
from apps.collaborateurs.models import Collaborateur


class LancementForm(forms.ModelForm):
    """
    Formulaire pour créer et modifier un lancement avec gestion d'erreurs détaillée
    """
    
    class Meta:
        model = Lancement
        fields = [
            'num_lanc', 'affaire', 'sous_livrable', 'date_reception', 
            'date_lancement', 'atelier', 'categorie', 'collaborateur',
            'poids_debitage', 'poids_assemblage', 'observations', 'statut'
        ]
        
        widgets = {
            'num_lanc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'LC-YYYY-XXX',
                'maxlength': 50
            }),
            'affaire': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'sous_livrable': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Décrivez précisément le sous-livrable à réaliser...'
            }),
            'date_reception': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'date_lancement': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'atelier': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'categorie': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'collaborateur': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'poids_debitage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'poids_assemblage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observations, remarques particulières, instructions spéciales...'
            }),
            'statut': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        
        labels = {
            'num_lanc': 'Numéro de lancement',
            'affaire': 'Affaire',
            'sous_livrable': 'Description du sous-livrable',
            'date_reception': 'Date de réception',
            'date_lancement': 'Date de lancement',
            'atelier': 'Atelier',
            'categorie': 'Catégorie',
            'collaborateur': 'Collaborateur responsable',
            'poids_debitage': 'Poids débitage (kg)',
            'poids_assemblage': 'Poids assemblage (kg)',
            'observations': 'Observations',
            'statut': 'Statut'
        }
        
        help_texts = {
            'num_lanc': 'Format recommandé: LC-YYYY-XXX (ex: LC-2024-001)',
            'date_reception': 'Date à laquelle la demande a été reçue',
            'date_lancement': 'Date prévue pour le début de la production',
            'poids_debitage': 'Poids en kilogrammes pour la phase de débitage',
            'poids_assemblage': 'Poids en kilogrammes pour la phase d\'assemblage',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # CORRECTION PRINCIPALE : Si on est en mode modification (instance existe)
        if self.instance.pk:
            # Rendre le champ num_lanc non requis et en lecture seule
            self.fields['num_lanc'].required = False
            self.fields['num_lanc'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control',
                'style': 'background-color: #e9ecef;'
            })
            # Ajouter un message d'aide spécifique pour la modification
            self.fields['num_lanc'].help_text = 'Le numéro de lancement ne peut pas être modifié'
        
        # Filtrer les affaires actives pour les nouveaux lancements
        if not self.instance.pk:
            self.fields['affaire'].queryset = Affaire.objects.filter(
                statut__in=['en_cours', 'planifie']
            ).order_by('code_affaire')
        else:
            # Pour la modification, inclure l'affaire actuelle même si elle n'est plus active
            self.fields['affaire'].queryset = Affaire.objects.all().order_by('code_affaire')
        
        # Filtrer les ateliers actifs
        self.fields['atelier'].queryset = Atelier.objects.all().order_by('nom_atelier')
        
        # Filtrer les catégories
        self.fields['categorie'].queryset = Categorie.objects.all().order_by('nom_categorie')
        
        # Filtrer les collaborateurs actifs
        self.fields['collaborateur'].queryset = Collaborateur.objects.filter(
            is_active=True
        ).order_by('nom_collaborateur', 'prenom_collaborateur')
        
        # Ajouter des placeholders vides pour les selects
        self.fields['affaire'].empty_label = "Sélectionnez une affaire"
        self.fields['atelier'].empty_label = "Sélectionnez un atelier"
        self.fields['categorie'].empty_label = "Sélectionnez une catégorie"
        self.fields['collaborateur'].empty_label = "Sélectionnez un collaborateur"

    def add_error_with_context(self, field, message, context=""):
        """
        Ajoute une erreur avec contexte pour identifier la source du problème
        """
        if context:
            full_message = f"[{context}] {message}"
        else:
            full_message = message
        
        if field:
            self.add_error(field, full_message)
        else:
            self.add_error(None, full_message)

    def clean_num_lanc(self):
        """
        Validation spéciale pour le numéro de lancement
        """
        num_lanc = self.cleaned_data.get('num_lanc')
        
        # Si on est en mode modification et que le numéro n'a pas changé, c'est OK
        if self.instance.pk and self.instance.num_lanc == num_lanc:
            return num_lanc
        
        # Si on est en mode création et que le numéro est vide, on génère automatiquement
        if not self.instance.pk and not num_lanc:
            return self.generate_lancement_number()
        
        # Vérifier l'unicité du numéro
        if num_lanc:
            existing = Lancement.objects.filter(num_lanc=num_lanc)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError("Ce numéro de lancement existe déjà.")
        
        return num_lanc

    def clean_date_lancement(self):
        """
        Validation de la date de lancement
        """
        try:
            date_lancement = self.cleaned_data.get('date_lancement')
            date_reception = self.cleaned_data.get('date_reception')
            
            if not date_lancement:
                raise ValidationError("La date de lancement est obligatoire.")
            
            # La date de lancement ne peut pas être antérieure à la date de réception
            if date_reception and date_lancement < date_reception:
                raise ValidationError(
                    "La date de lancement ne peut pas être antérieure à la date de réception."
                )
            
            return date_lancement
            
        except Exception as e:
            raise ValidationError(f"[DATES] Erreur dans la validation de la date de lancement: {str(e)}")

    def clean_date_reception(self):
        """
        Validation de la date de réception
        """
        try:
            date_reception = self.cleaned_data.get('date_reception')
            
            if not date_reception:
                raise ValidationError("La date de réception est obligatoire.")
            
            # La date de réception ne peut pas être dans le futur (avec une marge d'un jour)
            tomorrow = timezone.now().date() + timezone.timedelta(days=1)
            if date_reception > tomorrow:
                raise ValidationError(
                    "La date de réception ne peut pas être dans le futur."
                )
            
            return date_reception
            
        except Exception as e:
            raise ValidationError(f"[DATES] Erreur dans la validation de la date de réception: {str(e)}")

    def clean_poids_debitage(self):
        """
        Validation du poids de débitage
        """
        try:
            poids_debitage = self.cleaned_data.get('poids_debitage')
            
            if poids_debitage is not None:
                # Conversion en Decimal pour éviter les erreurs de type
                poids_debitage = Decimal(str(poids_debitage))
                
                if poids_debitage < 0:
                    raise ValidationError("Le poids de débitage ne peut pas être négatif.")
                
                if poids_debitage > Decimal('1000000'):
                    raise ValidationError("Le poids de débitage semble anormalement élevé (> 1000 tonnes).")
            
            return poids_debitage
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"[POIDS] Format de poids de débitage invalide: {str(e)}")
        except Exception as e:
            raise ValidationError(f"[POIDS] Erreur dans la validation du poids de débitage: {str(e)}")

    def clean_poids_assemblage(self):
        """
        Validation du poids d'assemblage
        """
        try:
            poids_assemblage = self.cleaned_data.get('poids_assemblage')
            
            if poids_assemblage is not None:
                # Conversion en Decimal pour éviter les erreurs de type
                poids_assemblage = Decimal(str(poids_assemblage))
                
                if poids_assemblage < 0:
                    raise ValidationError("Le poids d'assemblage ne peut pas être négatif.")
                
                if poids_assemblage > Decimal('1000000'):
                    raise ValidationError("Le poids d'assemblage semble anormalement élevé (> 1000 tonnes).")
            
            return poids_assemblage
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"[POIDS] Format de poids d'assemblage invalide: {str(e)}")
        except Exception as e:
            raise ValidationError(f"[POIDS] Erreur dans la validation du poids d'assemblage: {str(e)}")

    def clean(self):
        """
        Validation globale du formulaire
        """
        cleaned_data = super().clean()
        
        try:
            atelier = cleaned_data.get('atelier')
            categorie = cleaned_data.get('categorie')
            poids_debitage = cleaned_data.get('poids_debitage', Decimal('0'))
            poids_assemblage = cleaned_data.get('poids_assemblage', Decimal('0'))
            
            # Conversion en Decimal pour éviter les erreurs de type
            if poids_debitage is not None:
                poids_debitage = Decimal(str(poids_debitage))
            else:
                poids_debitage = Decimal('0')
                
            if poids_assemblage is not None:
                poids_assemblage = Decimal(str(poids_assemblage))
            else:
                poids_assemblage = Decimal('0')
            
            # Vérifier que l'atelier peut traiter cette catégorie
            if atelier and categorie:
                try:
                    from apps.ateliers.models import AtelierCategorie
                    if not AtelierCategorie.objects.filter(atelier=atelier, categorie=categorie).exists():
                        self.add_error_with_context(
                            'categorie',
                            f"L'atelier '{atelier.nom_atelier}' ne peut pas traiter "
                            f"la catégorie '{categorie.nom_categorie}'.",
                            "ATELIER-CATEGORIE"
                        )
                except Exception as e:
                    self.add_error_with_context(
                        'atelier',
                        f"Erreur lors de la vérification atelier-catégorie: {str(e)}",
                        "ATELIER-CATEGORIE"
                    )
            
            # Vérifier que les poids ne sont pas tous les deux à zéro
            if poids_debitage == Decimal('0') and poids_assemblage == Decimal('0'):
                self.add_error_with_context(
                    'poids_debitage',
                    "Au moins un des poids (débitage ou assemblage) doit être supérieur à zéro.",
                    "POIDS-VALIDATION"
                )
            
            # Vérifier la cohérence des poids (assemblage généralement <= débitage)
            if poids_debitage > Decimal('0') and poids_assemblage > poids_debitage * Decimal('1.5'):
                self.add_error_with_context(
                    None,
                    "Attention: Le poids d'assemblage semble très élevé par rapport "
                    "au poids de débitage. Veuillez vérifier.",
                    "POIDS-COHERENCE"
                )
            
        except Exception as e:
            self.add_error_with_context(
                None,
                f"Erreur générale lors de la validation: {str(e)}",
                "VALIDATION-GENERALE"
            )
        
        return cleaned_data

    def save(self, commit=True):
        """
        Sauvegarde personnalisée du lancement
        """
        try:
            lancement = super().save(commit=False)
            
            # Générer un numéro automatique si pas fourni (pour création uniquement)
            if not lancement.pk and not lancement.num_lanc:
                lancement.num_lanc = self.generate_lancement_number()
            
            if commit:
                lancement.save()
            
            return lancement
            
        except Exception as e:
            raise ValidationError(f"[SAUVEGARDE] Erreur lors de la sauvegarde: {str(e)}")

    def generate_lancement_number(self):
        """
        Génère automatiquement un numéro de lancement unique
        """
        try:
            from datetime import datetime
            
            year = datetime.now().year
            month = datetime.now().month
            
            # Compter le nombre de lancements ce mois-ci
            count = Lancement.objects.filter(
                created_at__year=year,
                created_at__month=month
            ).count() + 1
            
            # Générer le numéro avec un format: LC-YYYYMM-XXX
            base_number = f"LC-{year}{month:02d}-{count:03d}"
            
            # Vérifier l'unicité et incrémenter si nécessaire
            counter = 0
            while Lancement.objects.filter(num_lanc=base_number).exists():
                counter += 1
                base_number = f"LC-{year}{month:02d}-{count + counter:03d}"
            
            return base_number
            
        except Exception as e:
            # En cas d'erreur, générer un numéro basique
            import uuid
            return f"LC-{uuid.uuid4().hex[:8].upper()}"


# Autres formulaires (inchangés mais avec amélioration des messages d'erreur)

class LancementFilterForm(forms.Form):
    """
    Formulaire pour filtrer la liste des lancements
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher...'
        }),
        label='Recherche'
    )
    
    statut = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous les statuts')] + Lancement._meta.get_field('statut').choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Statut'
    )
    
    atelier = forms.ModelChoiceField(
        required=False,
        queryset=Atelier.objects.all(),
        empty_label="Tous les ateliers",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Atelier'
    )
    
    affaire = forms.ModelChoiceField(
        required=False,
        queryset=Affaire.objects.all(),
        empty_label="Toutes les affaires",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Affaire'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date de début'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date de fin'
    )


class LancementStatusUpdateForm(forms.Form):
    """
    Formulaire simple pour mettre à jour rapidement le statut d'un lancement
    """
    statut = forms.ChoiceField(
        choices=Lancement._meta.get_field('statut').choices,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm'
        }),
        label='Nouveau statut'
    )
    
    def __init__(self, *args, **kwargs):
        self.lancement = kwargs.pop('lancement', None)
        super().__init__(*args, **kwargs)
        
        if self.lancement:
            self.fields['statut'].initial = self.lancement.statut


class LancementQuickCreateForm(forms.ModelForm):
    """
    Formulaire simplifié pour création rapide de lancement (modal ou popup)
    """
    class Meta:
        model = Lancement
        fields = ['num_lanc', 'affaire', 'atelier', 'collaborateur', 'date_lancement', 'statut']
        
        widgets = {
            'num_lanc': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Auto-généré si vide'
            }),
            'affaire': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'required': True
            }),
            'atelier': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'required': True
            }),
            'collaborateur': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'required': True
            }),
            'date_lancement': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date',
                'required': True
            }),
            'statut': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les options pour la création rapide
        self.fields['affaire'].queryset = Affaire.objects.filter(
            statut__in=['en_cours', 'planifie']
        ).order_by('code_affaire')
        
        self.fields['collaborateur'].queryset = Collaborateur.objects.filter(
            is_active=True
        ).order_by('nom_collaborateur', 'prenom_collaborateur')
        
        # Valeurs par défaut
        self.fields['date_lancement'].initial = timezone.now().date()
        self.fields['statut'].initial = 'planifie'
        
        # Rendre le numéro optionnel pour auto-génération
        self.fields['num_lanc'].required = False


class LancementBulkActionForm(forms.Form):
    """
    Formulaire pour les actions en lot sur plusieurs lancements
    """
    ACTION_CHOICES = [
        ('', 'Choisir une action'),
        ('update_status', 'Changer le statut'),
        ('assign_atelier', 'Réaffecter à un atelier'),
        ('assign_collaborateur', 'Réaffecter à un collaborateur'),
        ('export', 'Exporter la sélection'),
        ('delete', 'Supprimer la sélection'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'bulk-action-select'
        }),
        label='Action à effectuer'
    )
    
    # Champs conditionnels selon l'action choisie
    new_statut = forms.ChoiceField(
        required=False,
        choices=Lancement._meta.get_field('statut').choices,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'style': 'display: none;'
        }),
        label='Nouveau statut'
    )
    
    new_atelier = forms.ModelChoiceField(
        required=False,
        queryset=Atelier.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'style': 'display: none;'
        }),
        label='Nouvel atelier'
    )
    
    new_collaborateur = forms.ModelChoiceField(
        required=False,
        queryset=Collaborateur.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'style': 'display: none;'
        }),
        label='Nouveau collaborateur'
    )
    
    selected_lancements = forms.CharField(
        widget=forms.HiddenInput(),
        label='Lancements sélectionnés'
    )
    
    def clean_selected_lancements(self):
        """
        Valide que des lancements ont été sélectionnés
        """
        selected = self.cleaned_data.get('selected_lancements')
        if not selected:
            raise ValidationError("Aucun lancement sélectionné.")
        
        try:
            ids = [int(id.strip()) for id in selected.split(',') if id.strip()]
            if not ids:
                raise ValidationError("Aucun lancement valide sélectionné.")
            return ids
        except ValueError:
            raise ValidationError("Format de sélection invalide.")

    def clean(self):
        """
        Validation selon l'action choisie
        """
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'update_status' and not cleaned_data.get('new_statut'):
            raise ValidationError("[ACTION] Veuillez choisir un nouveau statut.")
        
        if action == 'assign_atelier' and not cleaned_data.get('new_atelier'):
            raise ValidationError("[ACTION] Veuillez choisir un nouvel atelier.")
        
        if action == 'assign_collaborateur' and not cleaned_data.get('new_collaborateur'):
            raise ValidationError("[ACTION] Veuillez choisir un nouveau collaborateur.")
        
        return cleaned_data