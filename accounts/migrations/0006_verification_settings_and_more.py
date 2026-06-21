import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_emailverificationcode_user_is_email_confirmed'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='Numéro de téléphone'),
        ),
        migrations.AddField(
            model_name='accountverificationrequest',
            name='method',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='accountverificationrequest',
            name='phone_snapshot',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='accountverificationrequest',
            name='code_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='VerificationSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(
                    choices=[
                        ('phone', 'Option 1 — Numéro de téléphone (vérification manuelle)'),
                        ('admin_code', "Option 2 — Code saisi par l'administrateur"),
                        ('send_code', "Option 3 — Envoi automatique du code à l'utilisateur"),
                    ],
                    default='admin_code',
                    max_length=20,
                    verbose_name='Méthode de vérification',
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='verification_settings_updates',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Configuration de vérification',
            },
        ),
    ]
