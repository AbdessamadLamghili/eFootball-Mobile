import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def set_email_confirmed_for_existing_users(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.all().update(is_email_confirmed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_passwordresetcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_email_confirmed',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='EmailVerificationCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=6)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('is_used', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_verify_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Code vérification email',
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(
            set_email_confirmed_for_existing_users,
            migrations.RunPython.noop,
        ),
    ]
