import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0002_league_two_legs'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='matchresult',
            name='screenshot',
            field=models.ImageField(blank=True, null=True, upload_to='leagues/screenshots/'),
        ),
        migrations.AddField(
            model_name='matchresult',
            name='challenger_home_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='matchresult',
            name='challenger_away_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='matchresult',
            name='challenger_submitted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='challenger_match_results',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='matchresult',
            name='challenger_screenshot',
            field=models.ImageField(blank=True, null=True, upload_to='leagues/screenshots/'),
        ),
    ]
