# Generated by Django 5.2.2 on 2025-06-22 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesmanPanel', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_approved',
            field=models.BooleanField(default=False),
        ),
    ]
