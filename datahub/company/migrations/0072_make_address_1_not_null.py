# Generated by Django 2.2 on 2019-04-16 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0071_make_registered_address_postcode_not_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='address_1',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
    ]
