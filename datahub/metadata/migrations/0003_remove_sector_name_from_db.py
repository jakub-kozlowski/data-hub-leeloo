# Generated by Django 2.0.3 on 2018-03-21 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0002_add_sector_hierarchy'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='sector',
                    name='name',
                    field=models.TextField(blank=True, null=True),
                ),
            ],
        ),
        migrations.RemoveField('sector', 'name'),
    ]
