# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-08 10:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0014_adding_read_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='vat_number',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]