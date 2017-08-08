# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-03 09:22
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0004_team_roles_regions_countries'),
        ('investment', '0015_created_modified_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='investmentproject',
            name='country_lost_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='metadata.Country'),
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='date_abandoned',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='date_lost',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='reason_abandoned',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='reason_delayed',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='reason_lost',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='status',
            field=models.CharField(choices=[('ongoing', 'Ongoing'), ('delayed', 'Delayed'), ('lost', 'Lost'), ('abandoned', 'Abandoned')], default='ongoing', max_length=255),
        ),
    ]