# Generated by Django 2.1.4 on 2019-02-22 13:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0056_investment_activity'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='investmentproject',
                    name='likelihood_of_landing',
                ),
            ],
        ),
    ]
