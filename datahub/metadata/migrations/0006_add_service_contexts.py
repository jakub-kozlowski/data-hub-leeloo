# Generated by Django 2.0.4 on 2018-04-04 08:43

import datahub.core.fields
import django.contrib.postgres.indexes
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0005_add_order_to_headquartertype'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='contexts',
            field=datahub.core.fields.MultipleChoiceField(choices=(('event', 'Event'), ('interaction', 'Interaction'), ('investment_project_interaction', 'Investment project interaction'), ('policy_feedback', 'Policy feedback'), ('service_delivery', 'Service delivery')), default=['event', 'interaction', 'investment_project_interaction', 'service_delivery'], max_length=255, blank=True),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name='service',
            index=django.contrib.postgres.indexes.GinIndex(fields=['contexts'], name='metadata_se_context_df7886_gin'),
        ),
    ]