# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-29 05:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0003_auto_20161125_0332'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contact',
            name='role',
        ),
        migrations.AddField(
            model_name='contact',
            name='job_title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]