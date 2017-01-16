# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-01-13 10:06
from __future__ import unicode_literals

import datahub.company.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0010_auto_20170113_0610'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='website',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[datahub.company.validators.RelaxedURLValidator]),
        ),
    ]