from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_affaire_options_alter_affaire_client_and_more'),  # Bonne dépendance
        ('collaborateurs', '0001_initial'),
    ]

    operations = [
        # Solution complète en une seule migration
        migrations.RunSQL(
            sql="""
            -- Supprimer toutes les contraintes uniques possibles
            DROP INDEX IF EXISTS affaire_code_affaire_3c4b9f25_uniq CASCADE;
            DROP INDEX IF EXISTS core_affaire_code_affaire_3c4b9f25_uniq CASCADE;
            DROP INDEX IF EXISTS affaire_code_affaire_key CASCADE;
            
            -- Autoriser NULL sur les champs optionnels
            ALTER TABLE affaire ALTER COLUMN client DROP NOT NULL;
            ALTER TABLE affaire ALTER COLUMN livrable DROP NOT NULL;
            ALTER TABLE affaire ALTER COLUMN responsable_affaire_id DROP NOT NULL;
            ALTER TABLE affaire ALTER COLUMN date_debut DROP NOT NULL;
            ALTER TABLE affaire ALTER COLUMN date_fin_prevue DROP NOT NULL;
            
            -- Créer un index non-unique pour performance
            CREATE INDEX IF NOT EXISTS affaire_code_affaire_idx ON affaire (code_affaire);
            """,
            reverse_sql="-- Pas de reverse pour éviter les conflits"
        ),
        
        # Redéfinir les champs pour Django
        migrations.AlterField(
            model_name='affaire',
            name='code_affaire',
            field=models.CharField(max_length=50, unique=False, verbose_name="Code affaire"),
        ),
        migrations.AlterField(
            model_name='affaire',
            name='client',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name="Nom du client"),
        ),
        migrations.AlterField(
            model_name='affaire',
            name='livrable',
            field=models.TextField(blank=True, null=True, verbose_name="Description du livrable"),
        ),
        migrations.AlterField(
            model_name='affaire',
            name='responsable_affaire',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='affaires_responsable', to='collaborateurs.collaborateur', verbose_name="Responsable de l'affaire"),
        ),
        migrations.AlterField(
            model_name='affaire',
            name='date_debut',
            field=models.DateField(blank=True, null=True, verbose_name="Date de début"),
        ),
        migrations.AlterField(
            model_name='affaire',
            name='date_fin_prevue',
            field=models.DateField(blank=True, null=True, verbose_name="Date de fin prévue"),
        ),
    ]