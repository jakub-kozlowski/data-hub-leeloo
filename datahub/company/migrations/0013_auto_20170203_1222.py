# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-03 12:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0012_auto_20170201_1458'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companieshousecompany',
            name='company_number',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]