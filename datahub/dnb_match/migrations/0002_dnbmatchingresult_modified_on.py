# Generated by Django 2.1.7 on 2019-02-25 11:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dnb_match', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dnbmatchingresult',
            name='modified_on',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
