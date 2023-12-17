# Generated by Django 5.0 on 2023-12-17 11:26

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_ticket'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ticket',
            options={},
        ),
        migrations.AddField(
            model_name='ticket',
            name='active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ticket',
            name='create_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
