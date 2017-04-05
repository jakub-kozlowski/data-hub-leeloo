# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-05 14:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('interaction', '0004_auto_20170302_1421'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicedelivery',
            name='country_of_interest',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='metadata.Country'),
        ),
        migrations.AlterField(
            model_name='servicedelivery',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='metadata.Event'),
        ),
        migrations.AlterField(
            model_name='servicedelivery',
            name='feedback',
            field=models.TextField(max_length=4000, null=True),
        ),
        migrations.AlterField(
            model_name='servicedelivery',
            name='sector',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='metadata.Sector'),
        ),
        migrations.AlterField(
            model_name='servicedelivery',
            name='service_offer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='interaction.ServiceOffer'),
        ),
        migrations.AlterField(
            model_name='servicedelivery',
            name='uk_region',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='metadata.UKRegion'),
        ),
    ]
