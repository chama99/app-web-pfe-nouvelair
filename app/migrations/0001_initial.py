# Generated by Django 5.1.6 on 2025-05-07 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SegmentAvecCompte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member_id', models.CharField(max_length=30)),
                ('decimal_mois', models.IntegerField()),
                ('duree_moyenne_voyage', models.FloatField(blank=True, null=True)),
            ],
        ),
    ]
