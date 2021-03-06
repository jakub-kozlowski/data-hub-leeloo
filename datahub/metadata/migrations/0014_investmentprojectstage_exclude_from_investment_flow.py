# Generated by Django 2.1.2 on 2018-10-26 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0013_add_overseas_region'),
    ]

    operations = [
        migrations.AddField(
            model_name='investmentprojectstage',
            name='exclude_from_investment_flow',
            field=models.NullBooleanField(help_text='If set to True the stage will not be part of the linear flow and will be skipped.'),
        ),
    ]
