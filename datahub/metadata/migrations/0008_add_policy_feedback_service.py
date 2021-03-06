# Generated by Django 2.0.3 on 2018-03-27 12:23
from pathlib import PurePath

from django.db import migrations
from django.db.migrations import RunPython
from datahub.core.migration_utils import load_yaml_data_in_migration


def load_initial_services(apps, schema_editor):
    service_model = apps.get_model('metadata', 'Service')

    # Only load the fixtures if there aren't any already in the database
    # because we don't know if they have been changed via Django admin.
    if not service_model.objects.exists():
        load_yaml_data_in_migration(
            apps,
            PurePath(__file__).parent / '0008_initial_services.yaml'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0007_remove_role'),
    ]

    operations = [
        RunPython(load_initial_services, RunPython.noop),
    ]
