from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('exchange', '0003_demo_institution_admins')]

    operations = [
        migrations.AddField(
            model_name='credential', name='training_score',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='credential', name='training_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='TrainingAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('training_title', models.CharField(max_length=150)),
                ('answers', models.JSONField(default=list)),
                ('score', models.PositiveSmallIntegerField()),
                ('passed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('membership', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='training_attempts', to='exchange.membership')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='training_attempts', to='exchange.resource')),
            ],
            options={
                'ordering': ['-completed_at'],
                'indexes': [models.Index(fields=['membership', 'training_title', 'completed_at'], name='training_attempt_member_idx')],
            },
        ),
    ]
