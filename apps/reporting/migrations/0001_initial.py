# Generated by Django 5.2.4 on 2025-07-19 00:07

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RapportProduction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date_debut", models.DateField(verbose_name="Date de début")),
                ("date_fin", models.DateField(verbose_name="Date de fin")),
                (
                    "type_rapport",
                    models.CharField(
                        choices=[
                            ("journalier", "Journalier"),
                            ("hebdomadaire", "Hebdomadaire"),
                            ("mensuel", "Mensuel"),
                            ("annuel", "Annuel"),
                        ],
                        max_length=50,
                        verbose_name="Type de rapport",
                    ),
                ),
                (
                    "nb_lancements",
                    models.IntegerField(default=0, verbose_name="Nombre de lancements"),
                ),
                (
                    "poids_total",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Poids total traité",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Date de création"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Dernière mise à jour"
                    ),
                ),
            ],
            options={
                "verbose_name": "Rapport de Production",
                "verbose_name_plural": "Rapports de Production",
                "db_table": "rapport_production",
                "ordering": ["-date_debut"],
            },
        ),
    ]
