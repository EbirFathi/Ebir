from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['expediteur', 'transfer_id', 'montant', 'statut_verification', 'date_reception_serveur', 'lu']
    list_filter = ['statut_verification', 'lu']
    search_fields = ['expediteur', 'contenu', 'transfer_id', 'numero_envoyeur']
    readonly_fields = ['date_reception_serveur', 'source_ip']
    ordering = ['-date_reception_serveur']
