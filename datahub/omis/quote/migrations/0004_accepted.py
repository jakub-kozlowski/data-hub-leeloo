# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-16 10:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0010_auto_20170807_1124'),
        ('omis-quote', '0003_quote_expires_on'),
    ]

    operations = [
        migrations.AddField(
            model_name='quote',
            name='accepted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='company.Contact'),
        ),
        migrations.AddField(
            model_name='quote',
            name='accepted_on',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]