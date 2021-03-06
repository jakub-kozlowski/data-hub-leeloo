# Generated by Django 2.0.6 on 2018-06-13 15:53

from pathlib import PurePath
from django.db import migrations, models

from datahub.core.migration_utils import load_yaml_data_in_migration


def load_initial_classifications(apps, schema_editor):
    load_yaml_data_in_migration(
        apps,
        PurePath(__file__).parent / '0010_company_classifications.yaml'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0009_investment_spi_services'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='companyclassification',
            options={'ordering': ('order',)},
        ),
        migrations.AddField(
            model_name='companyclassification',
            name='order',
            field=models.FloatField(default=0.0),
        ),
        migrations.RunPython(load_initial_classifications, migrations.RunPython.noop)
    ]
