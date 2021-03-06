# Generated by Django 2.1.3 on 2018-11-16 11:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0017_countries_with_iso_data'),
        ('investment', '0051_switch_to_booleanfield_with_null_kwarg'),
    ]

    operations = [
        migrations.AddField(
            model_name='investmentproject',
            name='country_investment_originates_from',
            field=models.ForeignKey(blank=True, help_text='The country from which the investment originates', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='metadata.Country'),
        ),
    ]
