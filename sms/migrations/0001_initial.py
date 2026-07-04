from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expediteur', models.CharField(max_length=50, verbose_name='Expéditeur')),
                ('contenu', models.TextField(verbose_name='Contenu du message')),
                ('date_reception_telephone', models.DateTimeField(blank=True, null=True)),
                ('date_reception_serveur', models.DateTimeField(auto_now_add=True)),
                ('lu', models.BooleanField(default=False)),
                ('source_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('transfer_id', models.CharField(blank=True, max_length=100, null=True, verbose_name='Transaction ID')),
                ('montant', models.CharField(blank=True, max_length=50, null=True, verbose_name='Montant ETB')),
                ('numero_envoyeur', models.CharField(blank=True, max_length=50, null=True, verbose_name='Numéro envoyeur')),
                ('nom_envoyeur', models.CharField(blank=True, max_length=100, null=True, verbose_name='Nom envoyeur')),
                ('statut_verification', models.CharField(
                    choices=[
                        ('non_verifie', '⏳ En attente'),
                        ('correspond', '✅ Confirmé'),
                        ('ne_correspond_pas', '❌ Ne correspond pas'),
                        ('non_trouve', '🔍 Non trouvé'),
                    ],
                    default='non_verifie',
                    max_length=30,
                    verbose_name='Statut'
                )),
                ('details_verification', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Message SMS',
                'verbose_name_plural': 'Messages SMS',
                'ordering': ['-date_reception_serveur'],
            },
        ),
    ]
