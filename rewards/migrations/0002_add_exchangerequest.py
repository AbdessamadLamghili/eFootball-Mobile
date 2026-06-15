import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rewards', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExchangeRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_number', models.CharField(blank=True, max_length=20, unique=True)),
                ('points_used', models.PositiveIntegerField(verbose_name='Points utilisés')),
                ('coins_requested', models.PositiveIntegerField(verbose_name='Coins demandés')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'En attente'),
                        ('validated', 'Validé'),
                        ('rejected', 'Refusé'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('rejection_reason', models.TextField(blank=True, verbose_name='Raison du refus')),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='exchange_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('processed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='processed_exchanges',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': "Demande d'échange",
                'verbose_name_plural': "Demandes d'échange",
                'ordering': ['-created_at'],
            },
        ),
    ]
