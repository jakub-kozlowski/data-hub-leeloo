# Generated by Django 2.0.4 on 2018-05-16 23:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('investment', '0042_correct_spi_stage_log_created_on_and_ordering'),
    ]

    operations = [
        migrations.CreateModel(
            name='Proposition',
            fields=[
                ('created_on', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_on', models.DateTimeField(auto_now=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('deadline', models.DateField()),
                ('status', models.CharField(choices=[('ongoing', 'Ongoing'), ('abandoned', 'Abandoned'), ('completed', 'Completed')], default='ongoing', max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('scope', models.TextField()),
                ('details', models.TextField()),
                ('adviser', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('investment_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proposition', to='investment.InvestmentProject')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('read_all_proposition', 'Can read all proposition'), ('read_associated_investmentproject_proposition', 'Can read proposition for associated investment projects'), ('add_associated_investmentproject_proposition', 'Can add proposition for associated investment projects'), ('change_associated_investmentproject_proposition', 'Can change proposition for associated investment projects')),
                'default_permissions': ('add_all', 'change_all', 'delete'),
            },
        ),
    ]
