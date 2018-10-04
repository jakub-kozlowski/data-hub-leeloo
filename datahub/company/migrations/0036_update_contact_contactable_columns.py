# Generated by Django 2.1 on 2018-09-27 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0035_remove_account_manager_column'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='contactable_by_dit',
            field=models.NullBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='contact',
            name='contactable_by_email',
            field=models.NullBooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='contactable_by_overseas_dit_partners',
            field=models.NullBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='contact',
            name='contactable_by_phone',
            field=models.NullBooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='contactable_by_uk_dit_partners',
            field=models.NullBooleanField(default=False),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='contact',
                    name='contactable_by_dit',
                ),
                migrations.RemoveField(
                    model_name='contact',
                    name='contactable_by_email',
                ),
                migrations.RemoveField(
                    model_name='contact',
                    name='contactable_by_overseas_dit_partners',
                ),
                migrations.RemoveField(
                    model_name='contact',
                    name='contactable_by_phone',
                ),
                migrations.RemoveField(
                    model_name='contact',
                    name='contactable_by_uk_dit_partners',
                ),
            ],
        ),
    ]
