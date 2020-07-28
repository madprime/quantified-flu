# Generated by Django 2.2.14 on 2020-07-27 22:18
from collections import OrderedDict
import re

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion

import reports.models

# List adapted from common surveys.
CATEGORIZED_SYMPTOM_CHOICES = OrderedDict(
    [
        (
            "Respiratory",
            [
                ("cough", "Cough"),
                ("wet_cough", "Cough with mucus (phlegm)"),
                ("anosmia", "Reduced sense of smell (anosmia)"),
                ("runny_nose", "Runny or stuffy nose"),
                ("sore_throat", "Sore throat"),
                ("short_breath", "Shortness of breath"),
            ],
        ),
        (
            "Gastrointestinal",
            [("diarrhea", "Diarrhea"), ("nausea", "Nausea or vomiting")],
        ),
        (
            "Systemic",
            [
                ("chills", "Chills and sweats"),
                ("fatigue", "Fatigue and malaise"),
                ("headache", "Headache"),
                ("body_ache", "Muscle pains and body aches"),
            ],
        ),
    ]
)

# Used prior to mid-April (see commit 5b909bf)
OBSOLETE_REPORT = OrderedDict(
    [
        (
            "Respiratory",
            [
                ("cough", "Cough"),
                ("anosmia", "Reduced sense of smell (anosmia)"),
                ("runny_nose", "Runny or stuffy nose"),
                ("sore_throat", "Sore throat"),
                ("short_breath", "Shortness of breath"),
            ],
        ),
        (
            "Gastrointestinal",
            [
                ("diarrhea", "Diarrhea"),
                ("nausea", "Nausea or vomiting"),
                ("stomach_ache", "Stomach ache"),
            ],
        ),
        (
            "Systemic",
            [
                ("chills", "Chills and sweats"),
                ("ear_ache", "Ear ache"),
                ("fatigue", "Fatigue and malaise"),
                ("headache", "Headache"),
                ("body_ache", "Muscle pains and body aches"),
            ],
        ),
    ]
)


def create_reportsetups(apps, schema_editor):
    SymptomCategory = apps.get_model("reports", "SymptomCategory")
    Symptom = apps.get_model("reports", "Symptom")
    ReportSetup = apps.get_model("reports", "ReportSetup")
    ReportSetupSymptomItem = apps.get_model("reports", "ReportSetupSymptomItem")

    # Use CATEGORIZED_SYMPTOM_CHOICES (previously hard-coded) to set up
    # the default symptom report setup.
    default_setup = ReportSetup.objects.create(id=1, title="Viral Symptom Report")
    cat_ordering = []
    for cat_name in CATEGORIZED_SYMPTOM_CHOICES:
        cat = SymptomCategory.objects.create(name=cat_name)
        cat_ordering.append(str(cat.id))
        for symptom_data in CATEGORIZED_SYMPTOM_CHOICES[cat_name]:
            symptom = Symptom.objects.get(label=symptom_data[0])
            symptom.verbose = symptom_data[1]
            symptom.category = cat
            symptom.save()
            symptom_item = ReportSetupSymptomItem.objects.create(
                report_setup=default_setup, symptom=symptom
            )
    default_setup.category_ordering = ",".join(cat_ordering)
    default_setup.public = True
    default_setup.description = "Default viral symptom report."
    default_setup.save()

    # Store obsolete symptom report setup.
    obsolete_setup = ReportSetup.objects.create(id=2, title="Symptom Report")
    cat_ordering = []
    for cat_name in OBSOLETE_REPORT:
        cat, _ = SymptomCategory.objects.get_or_create(name=cat_name)
        cat_ordering.append(str(cat.id))
        for symptom_data in OBSOLETE_REPORT[cat_name]:
            symptom = Symptom.objects.get(label=symptom_data[0])
            symptom.category = cat
            symptom.save()
            if not symptom.verbose or symptom.verbose == symptom.label:
                symptom.verbose = symptom_data[1]
                symptom.save()
            symptom_item = ReportSetupSymptomItem.objects.create(
                report_setup=obsolete_setup, symptom=symptom
            )
    obsolete_setup.category_ordering = ",".join(cat_ordering)
    obsolete_setup.public = True
    obsolete_setup.description = "Historic viral symptom report (Mar/Apr 2020)."
    obsolete_setup.save()


def fix_empty_reports(apps, schema_editor):
    Symptom = apps.get_model("reports", "Symptom")
    SymptomReport = apps.get_model("reports", "SymptomReport")
    ReportSetup = apps.get_model("reports", "ReportSetup")
    SymptomReportSymptomItem = apps.get_model("reports", "SymptomReportSymptomItem")

    default_setup = ReportSetup.objects.get(id=1)
    default_symptoms = default_setup.reportsetupsymptomitem_set.filter(
        report_setup=default_setup
    )
    empty_reports = SymptomReport.objects.filter(symptomreportsymptomitem=None)
    for report in empty_reports:
        for setup_symptom_item in default_symptoms:
            SymptomReportSymptomItem.objects.create(
                symptom=setup_symptom_item.symptom, report=report
            )


class Migration(migrations.Migration):

    dependencies = [
        ("quantified_flu", "0003_remove_account_public_data"),
        ("reports", "0005_symptomreportphysiology"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportSetup",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=30)),
                (
                    "category_ordering",
                    models.TextField(
                        blank=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                re.compile("^\\d+(?:\\,\\d+)*\\Z"),
                                code="invalid",
                                message="Enter only digits separated by commas.",
                            )
                        ],
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("public", models.BooleanField(default=False)),
                (
                    "owner",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="quantified_flu.Account",
                    ),
                ),
            ],
            bases=(reports.models.ReportDisplayMixin, models.Model),
        ),
        migrations.CreateModel(
            name="SymptomCategory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=20, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name="symptom",
            name="owner",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="quantified_flu.Account",
            ),
        ),
        migrations.AddField(
            model_name="symptom",
            name="verbose",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="symptomreport",
            name="category_ordering",
            field=models.TextField(
                blank=True,
                validators=[
                    django.core.validators.RegexValidator(
                        re.compile("^\\d+(?:\\,\\d+)*\\Z"),
                        code="invalid",
                        message="Enter only digits separated by commas.",
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="symptom",
            name="label",
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name="symptomreportsymptomitem",
            name="symptom",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="reports.Symptom"
            ),
        ),
        migrations.CreateModel(
            name="ReportSetupSymptomItem",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "report_setup",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reports.ReportSetup",
                    ),
                ),
                (
                    "symptom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="reports.Symptom",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="symptom",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="reports.SymptomCategory",
            ),
        ),
        migrations.RunPython(
            create_reportsetups, reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(fix_empty_reports, reverse_code=migrations.RunPython.noop),
    ]
