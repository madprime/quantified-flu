# Generated by Django 2.2.11 on 2020-04-08 04:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("retrospective", "0005_auto_20200331_1916")]

    operations = [
        migrations.AddField(
            model_name="retrospectiveevent",
            name="published",
            field=models.BooleanField(default=False),
        )
    ]