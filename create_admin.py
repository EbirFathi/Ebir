import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
U = get_user_model()

u, created = U.objects.get_or_create(username='ebir')
u.is_superuser = True
u.is_staff = True
u.set_password('EbirAdmin2026!')
u.save()
print(f"Admin 'ebir' {'créé' if created else 'mis à jour'} avec succès")

deleted, _ = U.objects.filter(username='admin').delete()
if deleted:
    print("Ancien compte 'admin' supprimé")
