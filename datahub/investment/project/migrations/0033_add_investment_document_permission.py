# Generated by Django 2.0.1 on 2018-01-09 16:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0032_investmentproject_comments'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='investmentproject',
            options={'default_permissions': ('add', 'change_all', 'delete'), 'permissions': (('read_all_investmentproject', 'Can read all investment project'), ('read_associated_investmentproject', 'Can read associated investment project'), ('change_associated_investmentproject', 'Can change associated investment project'), ('read_investmentproject_document', 'Can read investment project document'))},
        ),
    ]
