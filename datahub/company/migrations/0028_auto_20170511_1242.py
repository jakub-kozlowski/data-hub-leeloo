# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-11 12:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0027_merge_20170509_1053'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companieshousecompany',
            name='registered_address_country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='companieshousecompanys', to='metadata.Country'),
        ),
        migrations.AlterField(
            model_name='company',
            name='business_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='metadata.BusinessType'),
        ),
        migrations.AlterField(
            model_name='company',
            name='registered_address_country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='companys', to='metadata.Country'),
        ),
        migrations.AlterField(
            model_name='company',
            name='sector',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='metadata.Sector'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='company.Company'),
        ),
    ]