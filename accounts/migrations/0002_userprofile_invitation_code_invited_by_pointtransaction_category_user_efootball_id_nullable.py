import random
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def generate_unique_codes(apps, schema_editor):
    """Generate unique invitation codes for all existing profiles."""
    UserProfile = apps.get_model('accounts', 'UserProfile')
    used = set()
    for profile in UserProfile.objects.all():
        while True:
            code = f"EFOOT-{random.randint(1000, 9999)}"
            if code not in used:
                used.add(code)
                break
        profile.invitation_code = code
        profile.save(update_fields=['invitation_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # Make efootball_id nullable
        migrations.AlterField(
            model_name='user',
            name='efootball_id',
            field=models.CharField(
                blank=True, max_length=50, null=True, unique=True,
                verbose_name='eFootball ID'
            ),
        ),
        # Add invitation_code WITHOUT unique constraint first
        migrations.AddField(
            model_name='userprofile',
            name='invitation_code',
            field=models.CharField(blank=True, max_length=20, default=''),
        ),
        # Populate codes for existing rows
        migrations.RunPython(generate_unique_codes, migrations.RunPython.noop),
        # Now add the unique constraint
        migrations.AlterField(
            model_name='userprofile',
            name='invitation_code',
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
        # Add invited_by
        migrations.AddField(
            model_name='userprofile',
            name='invited_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invited_users',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Add category to PointTransaction
        migrations.AddField(
            model_name='pointtransaction',
            name='category',
            field=models.CharField(
                choices=[
                    ('daily_login', 'Connexion quotidienne'),
                    ('mission', 'Mission complétée'),
                    ('invitation', 'Invitation'),
                    ('bonus', 'Bonus'),
                    ('exchange', 'Échange'),
                    ('refund', 'Remboursement'),
                    ('correction', 'Correction administrateur'),
                ],
                default='bonus',
                max_length=20,
            ),
        ),
    ]
