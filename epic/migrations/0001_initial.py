# Generated by Django 3.1.3 on 2020-11-20 04:59
import secrets

from django.db import migrations, models
import django.db.models.deletion

def generate_join_codes(apps, schema_editor):
    JoinCode = apps.get_model("epic", "JoinCode")
    JoinCode.objects.bulk_create([
        JoinCode(code=secrets.token_hex(32)) for i in range(10000)
    ])

def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='JoinCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=256)),
                ('claimed', models.BooleanField(default=False)),
            ],
        ),
        migrations.RunPython(generate_join_codes, noop)
    ]
