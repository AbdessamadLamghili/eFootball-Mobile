from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_verification_settings_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accountverificationrequest',
            name='verification_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='accountverificationrequest',
            name='entered_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='accountverificationrequest',
            name='phone_snapshot',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(blank=True, max_length=30, verbose_name='Numéro de téléphone'),
        ),
    ]
