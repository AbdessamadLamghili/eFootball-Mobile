import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove old mission_type field
        migrations.RemoveField(
            model_name='mission',
            name='mission_type',
        ),
        # Add mission_code
        migrations.AddField(
            model_name='mission',
            name='mission_code',
            field=models.CharField(
                choices=[
                    ('instagram_follow', 'Suivre Instagram officiel'),
                    ('complete_profile', 'Compléter le profil'),
                    ('consecutive_3_days', 'Visiter 3 jours consécutifs'),
                    ('consecutive_7_days', 'Visiter 7 jours consécutifs'),
                    ('invite_friends', 'Inviter des amis'),
                    ('all_missions', 'Toutes les missions terminées'),
                    ('custom', 'Mission personnalisée'),
                ],
                default='custom',
                max_length=30,
                verbose_name='Code de mission',
            ),
        ),
        # Add validation_type
        migrations.AddField(
            model_name='mission',
            name='validation_type',
            field=models.CharField(
                choices=[
                    ('automatic', 'Automatique'),
                    ('manual', 'Manuelle'),
                ],
                default='automatic',
                max_length=20,
                verbose_name='Type de validation',
            ),
        ),
        # Add link
        migrations.AddField(
            model_name='mission',
            name='link',
            field=models.URLField(
                blank=True, null=True,
                verbose_name='Lien externe',
            ),
        ),
        # Add max_monthly_completions
        migrations.AddField(
            model_name='mission',
            name='max_monthly_completions',
            field=models.PositiveIntegerField(
                default=0,
                verbose_name='Max complétions/mois',
            ),
        ),
        # Create MissionRequest model
        migrations.CreateModel(
            name='MissionRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'En attente'),
                        ('approved', 'Approuvée'),
                        ('rejected', 'Refusée'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('rejection_reason', models.TextField(blank=True, verbose_name='Raison du refus')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mission_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('mission', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='requests',
                    to='missions.mission',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_mission_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Demande de mission',
                'verbose_name_plural': 'Demandes de missions',
                'ordering': ['-created_at'],
            },
        ),
        # Update Mission ordering
        migrations.AlterModelOptions(
            name='mission',
            options={
                'ordering': ['mission_code', '-reward_points'],
                'verbose_name': 'Mission',
                'verbose_name_plural': 'Missions',
            },
        ),
    ]
