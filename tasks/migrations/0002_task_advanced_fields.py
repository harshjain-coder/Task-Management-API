from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='priority',
            field=models.CharField(
                choices=[
                    ('Low', 'Low'),
                    ('Medium', 'Medium'),
                    ('High', 'High'),
                    ('Urgent', 'Urgent'),
                ],
                default='Medium',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='category',
            field=models.CharField(default='General', max_length=50),
        ),
        migrations.AddField(
            model_name='task',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='task',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
