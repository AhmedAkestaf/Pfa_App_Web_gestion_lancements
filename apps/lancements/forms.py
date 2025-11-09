# apps/lancements/forms.py - MODIFIÉ avec nouveaux champs de poids et toggle

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import Lancement
from apps.ateliers.models import Atelier, Categorie
from apps.core.models import Affaire
from apps.collaborateurs.models import Collaborateur
from apps.associations.models import AffaireCategorie

class FrenchDecimalWidget(forms.NumberInput):
    """
    Widget personnalisé pour les poids avec format français
    """
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control',
            'step': '0.001',
            'min': '0',
            'placeholder': '0,000',
            'pattern': r'^\d{1,3}(?:\s\d{3})*(?:,\d{3})?$'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def format_value(self, value):
        """
        Formate la valeur pour l'affichage dans le champ
        """
        if value is None or value == '':
            return ''
        
        try:
            decimal_value = Decimal(str(value))
            if decimal_value == 0:
                return '0,000'
            
            # Format avec 3 décimales
            formatted = f"{decimal_value:.3f}"
            
            # Remplacer le point par une virgule
            formatted = formatted.replace('.', ',')
            
            # Ajouter les espaces pour les milliers
            if ',' in formatted:
                integer_part, decimal_part = formatted.split(',')
            else:
                integer_part = formatted
                decimal_part = "000"
            
            # Formater la partie entière avec espaces
            integer_formatted = ""
            for i, digit in enumerate(reversed(integer_part)):
                if i > 0 and i % 3 == 0:
                    integer_formatted = " " + integer_formatted
                integer_formatted = digit + integer_formatted
            
            return f"{integer_formatted},{decimal_part}"
            
        except (InvalidOperation, ValueError, TypeError):
            return '0,000'

class FrenchDecimalField(forms.DecimalField):
    """
    Champ décimal personnalisé pour gérer le format français
    """
    widget = FrenchDecimalWidget

    def to_python(self, value):
        """
        Convertit la valeur du format français vers un Decimal Python
        """
        if value in self.empty_values:
            return None

        if isinstance(value, str):
            # Nettoyer la valeur : supprimer espaces et remplacer virgule par point
            cleaned_value = value.replace(' ', '').replace(',', '.')
            try:
                return Decimal(cleaned_value)
            except InvalidOperation:
                raise ValidationError(
                    'Format invalide. Utilisez le format : 1 234,567',
                    code='invalid'
                )
        
        return super().to_python(value)


class LancementForm(forms.ModelForm):
    """
    Formulaire pour créer et modifier un lancement avec formatage français des poids
    """
    
    # NOUVEAU : Champ pour le type de production
    type_production = forms.ChoiceField(
        choices=Lancement.TYPE_PRODUCTION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
            'id': 'id_type_production'
        }),
        label='Type de production',
        help_text='Sélectionnez le type de production pour afficher les champs de poids correspondants'
    )
    
    # Redéfinir les champs de poids avec le format français
    poids_assemblage = FrenchDecimalField(
        max_digits=12,
        decimal_places=3,
        required=False,
        help_text='Poids en kilogrammes (3 chiffres après la virgule)',
        widget=FrenchDecimalWidget(attrs={
            'placeholder': '0,000',
            'id': 'id_poids_assemblage'
        }),
        label='Poids assemblage (kg)'
    )
    
    poids_debitage_1 = FrenchDecimalField(
        max_digits=12,
        decimal_places=3,
        required=False,
        help_text='Poids débitage 1 en kilogrammes (3 chiffres après la virgule)',
        widget=FrenchDecimalWidget(attrs={
            'placeholder': '0,000',
            'id': 'id_poids_debitage_1'
        }),
        label='Poids débitage 1 (kg)'
    )
    
    poids_debitage_2 = FrenchDecimalField(
        max_digits=12,
        decimal_places=3,
        required=False,
        help_text='Poids débitage 2 en kilogrammes (3 chiffres après la virgule)',
        widget=FrenchDecimalWidget(attrs={
            'placeholder': '0,000',
            'id': 'id_poids_debitage_2'
        }),
        label='Poids débitage 2 (kg)'
    )
    
    class Meta:
        model = Lancement
        fields = [
            'num_lanc', 'affaire', 'sous_livrable', 'date_reception', 
            'date_lancement', 'atelier', 'categorie', 'collaborateur',
            'type_production', 'poids_assemblage', 'poids_debitage_1', 
            'poids_debitage_2', 'observations', 'statut'
        ]
        
        widgets = {
            'num_lanc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'LC-YYYY-XXX',
                'maxlength': 50
            }),
            'affaire': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_affaire',
                'data-url-categories': '/lancements/ajax/categories-by-affaire/'
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
                'required': False
            }),
            'atelier': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'categorie': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_categorie'
            }),
            'collaborateur': forms.Select(attrs={
                'class': 'form-select',
                'required': True
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
            'type_production': 'Type de production',
            'poids_assemblage': 'Poids assemblage (kg)',
            'poids_debitage_1': 'Poids débitage 1 (kg)',
            'poids_debitage_2': 'Poids débitage 2 (kg)',
            'observations': 'Observations',
            'statut': 'Statut'
        }
        
        help_texts = {
            'num_lanc': 'Format recommandé: LC-YYYY-XXX (ex: LC-2024-001). Peut être dupliqué.',
            'affaire': 'Sélectionnez d\'abord l\'affaire pour filtrer les catégories disponibles',
            'categorie': 'Les catégories affichées dépendent de l\'affaire sélectionnée',
            'date_reception': 'Date à laquelle la demande a été reçue',
            'date_lancement': 'Date prévue pour le début de la production',
            'type_production': 'Sélectionnez assemblage ou débitage selon le type de production',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configuration pour la modification
        if self.instance.pk:
            self.fields['num_lanc'].required = False
            self.fields['num_lanc'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control',
                'style': 'background-color: #e9ecef;'
            })
            self.fields['num_lanc'].help_text = 'Le numéro de lancement ne peut pas être modifié'
        
        # Filtrer les affaires actives
        if not self.instance.pk:
            self.fields['affaire'].queryset = Affaire.objects.filter(
                statut__in=['en_cours', 'planifie']
            ).order_by('code_affaire')
        else:
            self.fields['affaire'].queryset = Affaire.objects.all().order_by('code_affaire')
        
        # Filtrer les ateliers
        self.fields['atelier'].queryset = Atelier.objects.all().order_by('nom_atelier')
        
        # Configuration initiale des catégories
        if self.instance.pk and self.instance.affaire_id:
            # Mode modification : filtrer selon l'affaire existante
            self._setup_categories_for_affaire(self.instance.affaire_id)
        else:
            # Mode création : toutes les catégories au début
            self.fields['categorie'].queryset = Categorie.objects.all().order_by('nom_categorie')
        
        # Filtrer les collaborateurs actifs
        self.fields['collaborateur'].queryset = Collaborateur.objects.filter(
            is_active=True
        ).order_by('nom_collaborateur', 'prenom_collaborateur')
        
        # Placeholders pour les selects
        self.fields['affaire'].empty_label = "Sélectionnez une affaire"
        self.fields['atelier'].empty_label = "Sélectionnez un atelier"
        self.fields['categorie'].empty_label = "Sélectionnez d'abord une affaire"
        self.fields['collaborateur'].empty_label = "Sélectionnez un collaborateur"

    def _setup_categories_for_affaire(self, affaire_id):
        """
        Configure les catégories disponibles selon l'affaire sélectionnée
        """
        try:
            # Récupérer les catégories associées à cette affaire
            categories_ids = AffaireCategorie.objects.filter(
                affaire_id=affaire_id
            ).values_list('categorie_id', flat=True)
            
            if categories_ids:
                # Filtrer les catégories
                self.fields['categorie'].queryset = Categorie.objects.filter(
                    id__in=categories_ids
                ).order_by('nom_categorie')
                self.fields['categorie'].empty_label = "Sélectionnez une catégorie"
            else:
                # Aucune catégorie associée : afficher toutes les catégories
                self.fields['categorie'].queryset = Categorie.objects.all().order_by('nom_categorie')
                self.fields['categorie'].empty_label = "Sélectionnez une catégorie (aucune restriction)"
                
        except Exception as e:
            # En cas d'erreur, afficher toutes les catégories
            self.fields['categorie'].queryset = Categorie.objects.all().order_by('nom_categorie')
            self.fields['categorie'].empty_label = "Sélectionnez une catégorie"

    def clean_num_lanc(self):
        """Validation pour le numéro de lancement (unicité supprimée)"""
        num_lanc = self.cleaned_data.get('num_lanc')
        
        if self.instance.pk and self.instance.num_lanc == num_lanc:
            return num_lanc
        
        if not self.instance.pk and not num_lanc:
            return self.generate_lancement_number()
        
        # UNICITÉ SUPPRIMÉE : on accepte les doublons
        return num_lanc

    def clean_date_lancement(self):
        """Validation de la date de lancement"""
        try:
            date_lancement = self.cleaned_data.get('date_lancement')
            date_reception = self.cleaned_data.get('date_reception')
            
            if not date_lancement:
                return None
            
            if date_reception and date_lancement < date_reception:
                raise ValidationError(
                    "La date de lancement ne peut pas être antérieure à la date de réception."
                )
            
            return date_lancement
            
        except Exception as e:
            raise ValidationError(f"[DATES] Erreur dans la validation de la date de lancement: {str(e)}")

    def clean_date_reception(self):
        """Validation de la date de réception"""
        try:
            date_reception = self.cleaned_data.get('date_reception')
            
            if not date_reception:
                raise ValidationError("La date de réception est obligatoire.")
            
            tomorrow = timezone.now().date() + timezone.timedelta(days=1)
            if date_reception > tomorrow:
                raise ValidationError(
                    "La date de réception ne peut pas être dans le futur."
                )
            
            return date_reception
            
        except Exception as e:
            raise ValidationError(f"[DATES] Erreur dans la validation de la date de réception: {str(e)}")

    def clean_poids_assemblage(self):
        """Validation du poids d'assemblage avec format français"""
        try:
            poids_assemblage = self.cleaned_data.get('poids_assemblage')
            
            if poids_assemblage is not None:
                if poids_assemblage < 0:
                    raise ValidationError("Le poids d'assemblage ne peut pas être négatif.")
                
                if poids_assemblage > Decimal('999999999.999'):
                    raise ValidationError("Le poids d'assemblage semble anormalement élevé.")
                    
                # Vérifier que les décimales n'excèdent pas 3 chiffres
                if poids_assemblage.as_tuple().exponent < -3:
                    raise ValidationError("Maximum 3 chiffres après la virgule.")

            return poids_assemblage
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Format de poids d'assemblage invalide. Utilisez le format : 1 234,567")
        except Exception as e:
            raise ValidationError(f"Erreur dans la validation du poids d'assemblage: {str(e)}")

    def clean_poids_debitage_1(self):
        """Validation du poids débitage 1 avec format français"""
        try:
            poids_debitage_1 = self.cleaned_data.get('poids_debitage_1')
            
            if poids_debitage_1 is not None:
                if poids_debitage_1 < 0:
                    raise ValidationError("Le poids débitage 1 ne peut pas être négatif.")
                
                if poids_debitage_1 > Decimal('999999999.999'):
                    raise ValidationError("Le poids débitage 1 semble anormalement élevé.")
                    
                # Vérifier que les décimales n'excèdent pas 3 chiffres
                if poids_debitage_1.as_tuple().exponent < -3:
                    raise ValidationError("Maximum 3 chiffres après la virgule.")
            
            return poids_debitage_1
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Format de poids débitage 1 invalide. Utilisez le format : 1 234,567")
        except Exception as e:
            raise ValidationError(f"Erreur dans la validation du poids débitage 1: {str(e)}")

    def clean_poids_debitage_2(self):
        """Validation du poids débitage 2 avec format français"""
        try:
            poids_debitage_2 = self.cleaned_data.get('poids_debitage_2')
            
            if poids_debitage_2 is not None:
                if poids_debitage_2 < 0:
                    raise ValidationError("Le poids débitage 2 ne peut pas être négatif.")
                
                if poids_debitage_2 > Decimal('999999999.999'):
                    raise ValidationError("Le poids débitage 2 semble anormalement élevé.")
                    
                # Vérifier que les décimales n'excèdent pas 3 chiffres
                if poids_debitage_2.as_tuple().exponent < -3:
                    raise ValidationError("Maximum 3 chiffres après la virgule.")
            
            return poids_debitage_2
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Format de poids débitage 2 invalide. Utilisez le format : 1 234,567")
        except Exception as e:
            raise ValidationError(f"Erreur dans la validation du poids débitage 2: {str(e)}")

    def clean(self):
        """Validation globale du formulaire"""
        cleaned_data = super().clean()
        
        try:
            type_production = cleaned_data.get('type_production')
            poids_assemblage = cleaned_data.get('poids_assemblage')
            poids_debitage_1 = cleaned_data.get('poids_debitage_1')
            poids_debitage_2 = cleaned_data.get('poids_debitage_2')
            
            # Validation selon le type de production
            if type_production == 'assemblage':
                if not poids_assemblage or poids_assemblage == Decimal('0'):
                    self.add_error(
                        'poids_assemblage',
                        "Le poids d'assemblage est obligatoire pour ce type de production."
                    )
            elif type_production == 'debitage':
                if (not poids_debitage_1 or poids_debitage_1 == Decimal('0')) and (not poids_debitage_2 or poids_debitage_2 == Decimal('0')):
                    self.add_error(
                        'poids_debitage_1',
                        "Au moins un des poids de débitage doit être supérieur à zéro."
                    )
            
            # Vérification de cohérence affaire-catégorie
            affaire = cleaned_data.get('affaire')
            categorie = cleaned_data.get('categorie')
            
            if affaire and categorie:
                # Vérifier si cette catégorie est associée à l'affaire
                association_exists = AffaireCategorie.objects.filter(
                    affaire=affaire,
                    categorie=categorie
                ).exists()
                
                # Si aucune association existe pour cette affaire, c'est OK (pas de restriction)
                affaire_has_categories = AffaireCategorie.objects.filter(affaire=affaire).exists()
                
                if affaire_has_categories and not association_exists:
                    self.add_error(
                        'categorie',
                        f"La catégorie '{categorie.nom_categorie}' n'est pas associée à l'affaire '{affaire.code_affaire}'. "
                        "Veuillez sélectionner une catégorie associée à cette affaire."
                    )
            
        except Exception as e:
            self.add_error(
                None,
                f"Erreur générale lors de la validation: {str(e)}"
            )
        
        return cleaned_data

    def save(self, commit=True):
        """Sauvegarde personnalisée du lancement"""
        try:
            lancement = super().save(commit=False)
            
            # Générer un numéro automatique si nécessaire
            if not lancement.pk and not lancement.num_lanc:
                lancement.num_lanc = self.generate_lancement_number()
            
            if commit:
                lancement.save()
            
            return lancement
            
        except Exception as e:
            raise ValidationError(f"[SAUVEGARDE] Erreur lors de la sauvegarde: {str(e)}")

    def generate_lancement_number(self):
        """Génère automatiquement un numéro de lancement unique"""
        try:
            from datetime import datetime
            
            year = datetime.now().year
            month = datetime.now().month
            
            count = Lancement.objects.filter(
                created_at__year=year,
                created_at__month=month
            ).count() + 1
            
            base_number = f"LC-{year}{month:02d}-{count:03d}"
            
            # UNICITÉ SUPPRIMÉE : on ne vérifie plus l'existence
            return base_number
            
        except Exception as e:
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