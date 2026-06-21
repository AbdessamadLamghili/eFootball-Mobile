from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='league',
            name='two_legs',
            field=models.BooleanField(default=False, verbose_name='Aller-retour (2 manches)'),
        ),
    ]
