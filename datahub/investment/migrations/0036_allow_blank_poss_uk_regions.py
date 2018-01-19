# Generated by Django 2.0.1 on 2018-01-17 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0035_nullable_est_land_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='investmentproject',
            name='allow_blank_possible_uk_regions',
            field=models.BooleanField(default=False, help_text='Controls whether possible UK regions is a required field (after the prospect stage). Intended for projects migrated from CDMS in the verify win and won stages where legacy data for possible UK regions does not exist.'),
        ),
    ]