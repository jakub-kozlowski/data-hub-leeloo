# Generated by Django 2.1.7 on 2019-04-05 13:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0061_auto_20190405_1135'),
    ]

    operations = [
        migrations.AlterField(
            model_name='investmentproject',
            name='gva_multiplier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='investment_projects', to='investment.GVAMultiplier'),
        ),
    ]
