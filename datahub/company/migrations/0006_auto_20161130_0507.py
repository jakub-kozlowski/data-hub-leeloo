# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-30 05:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0005_auto_20161129_0950'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advisor',
            name='date_joined',
            field=models.DateTimeField(auto_now_add=True, verbose_name='date joined'),
        ),
    ]