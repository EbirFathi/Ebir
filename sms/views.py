import json
import logging
import re
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Message

logger = logging.getLogger(__name__)


def extraire_infos_sms(contenu):
    """
    Extrait transfer_id, montant, numero_envoyeur, nom_envoyeur d'un SMS ETB.
    Supporte : Telebirr, CBE, HelloCash, et format Transfer-Id générique.
    """
    infos = {
        'transfer_id': None,
        'montant': None,
        'montant_num': None,
        'numero_envoyeur': None,
        'nom_envoyeur': None,
    }

    # ── Transfer-ID / Txn / Ref ───────────────────────────────────────────────
    for pattern in [
        r'Transfer[-\s]?Id[:\s#]*(\d+)',
        r'Txn\s*(?:No|ID|#)?[:\s]*([A-Z0-9]{6,20})',
        r'Transaction\s*(?:No|ID|#)?[:\s]*([A-Z0-9]{6,20})',
        r'Ref(?:erence)?\s*(?:No|#)?[:\s]*([A-Z0-9]{6,20})',
        r'TxnID[:\s]*([A-Z0-9]{6,20})',
    ]:
        m = re.search(pattern, contenu, re.IGNORECASE)
        if m:
            infos['transfer_id'] = m.group(1).strip()
            break

    # ── Montant ETB ──────────────────────────────────────────────────────────
    # Patterns: "ETB 1,000.00", "Birr 500", "1,000.00 ETB", "received ETB X from"
    for pattern in [
        r'(?:ETB|Birr)\s+([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*(?:ETB|Birr)',
        r'Received\s+([\w\s,]+?)\s+from',
    ]:
        m = re.search(pattern, contenu, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            # Supprimer les virgules des milliers, garder décimales
            num = re.sub(r'[,\s]', '', re.sub(r'[^\d,.]', '', raw))
            if num and re.search(r'\d', num):
                infos['montant'] = f"ETB {raw}"
                infos['montant_num'] = num
                break

    # ── Numéro expéditeur ─────────────────────────────────────────────────────
    # Formats éthiopiens : 09XXXXXXXX, 07XXXXXXXX, +251XXXXXXXXX, 251XXXXXXXXX
    for pattern in [
        r'from\s+[^(]*\((\+?(?:251)?0?[79]\d{8})\)',  # from Name(0911...)
        r'from\s+(\+?(?:251)?0[79]\d{8})\b',           # from 0911234567
        r'\b(\+?251[79]\d{8})\b',                       # international
        r'\b(0[79]\d{8})\b',                            # local 09/07
    ]:
        m = re.search(pattern, contenu, re.IGNORECASE)
        if m:
            phone = m.group(1).strip().lstrip('+')
            # Normaliser: garder les 9 derniers chiffres (sans indicatif pays)
            digits = re.sub(r'\D', '', phone)
            if digits.startswith('251') and len(digits) >= 12:
                digits = '0' + digits[3:]
            infos['numero_envoyeur'] = digits
            break

    # ── Nom expéditeur ───────────────────────────────────────────────────────
    for pattern in [
        r'from\s+([A-Za-z][A-Za-z\s]{2,40}?)\s*(?:\([\d+])',  # from Name(phone)
        r'from\s+([A-Za-z][A-Za-z\s]{2,40}?)\.',               # from Name.
    ]:
        m = re.search(pattern, contenu, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) >= 3 and not name.isdigit():
                infos['nom_envoyeur'] = name
                break

    return infos


@csrf_exempt
def webhook_recevoir_sms(request):
    """Point d'entrée webhook : reçoit les SMS depuis l'appli Android (SMS Forwarder)."""
    data = {}
    data.update(request.GET.dict())
    if request.method == 'POST':
        try:
            body_str = request.body.decode('utf-8').strip()
            if body_str:
                parsed = json.loads(body_str)
                if isinstance(parsed, dict):
                    data.update(parsed)
        except Exception:
            pass
        try:
            if request.POST:
                data.update(request.POST.dict())
        except Exception:
            pass

    logger.info(f"[WEBHOOK] données={json.dumps(data, ensure_ascii=False)[:500]}")

    expediteur = (data.get('from') or data.get('sender') or data.get('number') or 'Inconnu')
    if expediteur and expediteur.startswith('{'):
        expediteur = 'Inconnu'

    contenu = (data.get('message') or data.get('msg') or data.get('body') or
               data.get('text') or data.get('sms') or data.get('key') or '')
    if contenu and contenu.startswith('{'):
        contenu = ''
    if not contenu:
        contenu = f"[Données: {json.dumps(data, ensure_ascii=False)}]"

    infos = extraire_infos_sms(contenu)
    ip_source = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or
                 request.META.get('REMOTE_ADDR'))

    msg = Message.objects.create(
        expediteur=str(expediteur)[:50],
        contenu=contenu,
        source_ip=ip_source or None,
        transfer_id=infos.get('transfer_id'),
        montant=infos.get('montant'),
        numero_envoyeur=infos.get('numero_envoyeur'),
        nom_envoyeur=infos.get('nom_envoyeur'),
        statut_verification='non_verifie',
    )

    logger.info(
        f"[SMS #{msg.id}] Expéditeur:{expediteur} | "
        f"TxnID:{infos.get('transfer_id')} | "
        f"Montant:{infos.get('montant')} | "
        f"Phone:{infos.get('numero_envoyeur')}"
    )

    return JsonResponse({'status': 'ok', 'id': msg.id}, status=201)


@login_required
def dashboard(request):
    messages_qs = Message.objects.all()
    filtre_expediteur = request.GET.get('expediteur', '')
    if filtre_expediteur:
        messages_qs = messages_qs.filter(expediteur__icontains=filtre_expediteur)
    total = Message.objects.count()
    non_lus = Message.objects.filter(lu=False).count()
    Message.objects.filter(lu=False).update(lu=True)
    expediteurs = Message.objects.values_list('expediteur', flat=True).distinct()
    context = {
        'messages': messages_qs[:200],
        'total': total,
        'non_lus': non_lus,
        'expediteurs': expediteurs,
        'filtre_expediteur': filtre_expediteur,
        'webhook_url': request.build_absolute_uri('/webhook/sms/'),
    }
    return render(request, 'sms/dashboard.html', context)


@login_required
def detail_message(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.lu = True
    msg.save(update_fields=['lu'])
    return render(request, 'sms/detail.html', {'msg': msg})


@login_required
@require_http_methods(["POST"])
def supprimer_message(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.delete()
    return JsonResponse({'status': 'ok'})


def api_messages(request):
    """API lue par ebir-agent pour récupérer les nouveaux SMS."""
    depuis_id = request.GET.get('depuis_id', 0)
    msgs = Message.objects.filter(id__gt=depuis_id).values(
        'id', 'expediteur', 'contenu', 'transfer_id', 'montant',
        'numero_envoyeur', 'nom_envoyeur', 'statut_verification',
        'details_verification', 'date_reception_serveur', 'lu'
    )[:50]
    return JsonResponse({'messages': list(msgs)})


def ping(request):
    return JsonResponse({'status': 'ok', 'app': 'ebir-sms', 'total_sms': Message.objects.count()})
