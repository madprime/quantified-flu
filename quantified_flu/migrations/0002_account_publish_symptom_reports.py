# Generated by Django 2.2.11 on 2020-04-08 05:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("quantified_flu", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="account",
            name="publish_symptom_reports",
            field=models.BooleanField(default=False),
        )
    ]