import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OAuthState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(db_index=True, max_length=64, unique=True)),
                ('next_url', models.CharField(default='/admin/', max_length=500)),
                ('is_popup', models.BooleanField(default=False)),
                ('poll_id', models.CharField(blank=True, max_length=64, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'oauth_states',
            },
        ),
        migrations.CreateModel(
            name='PendingAuthToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('poll_id', models.CharField(db_index=True, max_length=64, unique=True)),
                ('token', models.CharField(blank=True, db_index=True, max_length=64)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'pending_auth_tokens',
            },
        ),
        migrations.CreateModel(
            name='CayuOAuthProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cayu_user_id', models.CharField(max_length=50, unique=True)),
                ('cayu_email', models.EmailField(max_length=254)),
                ('cayu_organization_id', models.CharField(blank=True, max_length=50, null=True)),
                ('cayu_organization_role', models.CharField(blank=True, max_length=50, null=True)),
                ('cayu_is_super_admin', models.BooleanField(default=False)),
                ('last_login_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cayu_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Cayu OAuth Profile',
                'verbose_name_plural': 'Cayu OAuth Profiles',
                'db_table': 'cayu_oauth_profiles',
            },
        ),
    ]
