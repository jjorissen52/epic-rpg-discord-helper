# Generated by Django 3.1.3 on 2020-12-28 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("epic", "0014_marriage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gamble",
            name="created",
            field=models.DateTimeField(db_index=True),
        ),
    ]
