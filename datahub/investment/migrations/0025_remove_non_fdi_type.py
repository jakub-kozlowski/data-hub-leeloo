# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-09 15:47
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0024_adding_read_permissions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='investmentproject',
            name='non_fdi_type',
        ),
    ]