# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-31 10:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('metadata', '0008_remove_legacy_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamrole',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='Permission groups associated with this team.', related_name='team_roles', related_query_name='team_roles', to='auth.Group', verbose_name='team role permission groups'),
        ),
    ]