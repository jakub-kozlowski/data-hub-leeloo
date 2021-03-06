# Generated by Django 2.0.2 on 2018-03-05 14:17

from pathlib import PurePath

import django.db.models.deletion
import mptt
import mptt.fields
import mptt.managers
from django.db import migrations, models
from datahub.core.migration_utils import load_yaml_data_in_migration


def load_sectors(apps, schema_editor):
    load_yaml_data_in_migration(
        apps,
        PurePath(__file__).parent / '0002_add_sector_hierarchy.yaml'
    )


def rebuild_tree(apps, schema_editor):
    Sector = apps.get_model('metadata', 'Sector')
    manager = mptt.managers.TreeManager()
    manager.model = Sector
    mptt.register(Sector, order_insertion_by=['segment'])
    manager.contribute_to_class(Sector, 'objects')
    manager.rebuild()


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0001_squashed_0011_add_default_id_for_metadata'),
    ]

    # We're temporarily leaving the name column in the database to avoid downtime and allow the
    # migration to be reversed.
    #
    # Once these changes have been released, the column can be removed from the database using
    # another migration.
    state_operations = [
        migrations.RemoveField(
            model_name='sector',
            name='name',
        ),
    ]

    database_operations = [
        migrations.AlterField(
            model_name='sector',
            name='name',
            field=models.TextField(blank=True, null=True),
        ),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sector',
            options={'ordering': ('lft',)},
        ),
        migrations.AddField(
            model_name='sector',
            name='segment',
            field=models.CharField(max_length=255, default='(name not set)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sector',
            name='level',
            field=models.PositiveIntegerField(db_index=True, default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sector',
            name='lft',
            field=models.PositiveIntegerField(db_index=True, default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sector',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='metadata.Sector'),
        ),
        migrations.AddField(
            model_name='sector',
            name='rght',
            field=models.PositiveIntegerField(db_index=True, default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sector',
            name='tree_id',
            field=models.PositiveIntegerField(db_index=True, default=0, editable=False),
            preserve_default=False,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations, database_operations=database_operations,
        ),
        migrations.RunPython(load_sectors, migrations.RunPython.noop),
        migrations.RunPython(rebuild_tree, migrations.RunPython.noop),
    ]
