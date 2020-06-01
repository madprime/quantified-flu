# Generated by Django 2.2.12 on 2020-05-29 18:03
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
    Symptom = apps.get_model("reports", "Symptom")
    ReportSetup = apps.get_model("reports", "ReportSetup")
    ReportSetupCategoryItem = apps.get_model("reports", "ReportSetupCategoryItem")
    ReportSetupSymptomItem = apps.get_model("reports", "ReportSetupSymptomItem")

    # Use CATEGORIZED_SYMPTOM_CHOICES (previously hard-coded) to set up
    # the default symptom report setup.
    default_setup = ReportSetup.objects.create(id=1, title="Viral Symptom Report")
    for cat_name in CATEGORIZED_SYMPTOM_CHOICES:
        cat = ReportSetupCategoryItem.objects.create(
            report_setup=default_setup, name=cat_name
        )
        for symptom_data in CATEGORIZED_SYMPTOM_CHOICES[cat_name]:
            symptom = Symptom.objects.get(label=symptom_data[0])
            symptom.verbose = symptom_data[1]
            symptom.save()
            symptom_item = ReportSetupSymptomItem.objects.create(
                report_setup=default_setup, category=cat, symptom=symptom
            )

    # Store obsolete symptom report setup.
    obsolete_setup = ReportSetup.objects.create(id=2, title="Symptom Report")
    for cat_name in OBSOLETE_REPORT:
        cat = ReportSetupCategoryItem.objects.create(
            report_setup=obsolete_setup, name=cat_name
        )
        for symptom_data in OBSOLETE_REPORT[cat_name]:
            symptom = Symptom.objects.get(label=symptom_data[0])
            if not symptom.verbose or symptom.verbose == symptom.label:
                symptom.verbose = symptom_data[1]
                symptom.save()
            symptom_item = ReportSetupSymptomItem.objects.create(
                report_setup=obsolete_setup, category=cat, symptom=symptom
            )


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


def update_reports(apps, schema_editor):
    # Symptom = apps.get_model("reports", "Symptom")
    ReportSetup = apps.get_model("reports", "ReportSetup")
    # ReportSetupCategoryItem = apps.get_model("reports", "ReportSetupCategoryItem")
    # ReportSetupSymptomItem = apps.get_model("reports", "ReportSetupSymptomItem")
    SymptomReport = apps.get_model("reports", "SymptomReport")
    SymptomReportCategoryItem = apps.get_model("reports", "SymptomReportCategoryItem")

    default_setup = ReportSetup.objects.get(id=1)
    default_setup_symptoms = {
        si.symptom.label: si for si in default_setup.reportsetupsymptomitem_set.all()
    }
    default_catitems = default_setup.reportsetupcategoryitem_set.all()
    old_setup = ReportSetup.objects.get(id=2)
    old_setup_symptoms = {
        si.symptom.label: si for si in old_setup.reportsetupsymptomitem_set.all()
    }
    old_catitems = old_setup.reportsetupcategoryitem_set.all()

    for report in SymptomReport.objects.all():

        # Determine which report setup was used.
        symptom_items = {
            si.symptom.label: si for si in report.symptomreportsymptomitem_set.all()
        }
        is_default_setup = True
        is_old_setup = True
        for label in symptom_items:
            if label not in default_setup_symptoms:
                is_default_setup = False
            if label not in old_setup_symptoms:
                is_old_setup = False
        assert is_default_setup != is_old_setup

        # report set up information
        setup = default_setup if is_default_setup else old_setup
        setup_catitems = default_catitems if is_default_setup else old_catitems
        setup_symptoms = (
            default_setup_symptoms if is_default_setup else old_setup_symptoms
        )

        # copy categories to report, and link to report symptom items
        for setup_cat in setup_catitems:
            report_cat = SymptomReportCategoryItem.objects.create(
                name=setup_cat.name, report=report
            )
            for label in setup_symptoms:
                if setup_symptoms[label].category == setup_cat:
                    si = symptom_items[label]
                    si.category = report_cat
                    si.save()


class Migration(migrations.Migration):

    dependencies = [("reports", "0005_symptomreportphysiology")]

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
            ],
            bases=(reports.models.ReportDisplayMixin, models.Model),
        ),
        migrations.CreateModel(
            name="ReportSetupCategoryItem",
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
                ("name", models.CharField(max_length=20)),
                (
                    "report_setup",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reports.ReportSetup",
                    ),
                ),
            ],
        ),
        migrations.RemoveField(model_name="symptom", name="available"),
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
            model_name="symptomreportsymptomitem",
            name="symptom",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="reports.Symptom"
            ),
        ),
        migrations.CreateModel(
            name="SymptomReportCategoryItem",
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
                ("name", models.CharField(max_length=20)),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reports.SymptomReport",
                    ),
                ),
            ],
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
                    "category",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="reports.ReportSetupCategoryItem",
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
            model_name="symptomreportsymptomitem",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="reports.SymptomReportCategoryItem",
            ),
        ),
        migrations.RunPython(
            create_reportsetups, reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(fix_empty_reports, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(update_reports, reverse_code=migrations.RunPython.noop),
    ]
