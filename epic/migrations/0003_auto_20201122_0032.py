# Generated by Django 3.1.3 on 2020-11-22 00:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("epic", "0002_cooldown_profile_server"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cooldown",
            name="type",
            field=models.CharField(
                choices=[
                    ("daily", "daily"),
                    ("weekly", "weekly"),
                    ("lootbox", "lootbox"),
                    ("vote", "vote"),
                    ("hunt", "hunt"),
                    ("adventure", "adventure"),
                    ("quest", "quest"),
                    ("training", "training"),
                    ("duel", "duel"),
                    ("work", "work"),
                    ("horse", "horse"),
                    ("arena", "arena"),
                    ("dungeon", "dungeon"),
                ],
                max_length=10,
            ),
        ),
    ]
