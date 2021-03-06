# Generated by Django 2.1.4 on 2019-01-10 10:14

from pathlib import PurePath

from django.db import migrations, models
import django.db.models.deletion

from datahub.core.migration_utils import load_yaml_data_in_migration
import uuid


def load_project_manager_request_status_data(apps, schema_editor):
    load_yaml_data_in_migration(
        apps,
        PurePath(__file__).parent / '0055_project_manager_request_status.yaml',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0054_investmentproject_likelihood_to_land'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectManagerRequestStatus',
            fields=[
                ('disabled_on', models.DateTimeField(blank=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.TextField(blank=True)),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='project_manager_requested_on',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentproject',
            name='project_manager_request_status',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='investment.ProjectManagerRequestStatus'),
        ),
        migrations.RunPython(load_project_manager_request_status_data, migrations.RunPython.noop),
    ]
