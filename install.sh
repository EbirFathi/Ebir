#!/bin/bash
# Installation Ebir-SMS sur VPS Ubuntu
set -e

echo "=== Installation Ebir-SMS ==="

apt-get update -qq
apt-get install -y python3 python3-pip python3-venv

cd /root/ebir-sms
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

# Migrations & superutilisateur
python manage.py migrate
python manage.py collectstatic --noinput

echo ""
echo "=== Créer le superutilisateur admin ==="
python manage.py createsuperuser

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Démarrer avec gunicorn :"
echo "  screen -S ebir-sms -dm bash -c 'cd /root/ebir-sms && source venv/bin/activate && gunicorn config.wsgi -b 0.0.0.0:8001 --workers 2 --log-file -'"
echo ""
echo "URL webhook pour SMS Forwarder :"
echo "  http://VPS_IP:8001/webhook/sms/"
echo ""
echo "Dashboard (login admin) :"
echo "  http://VPS_IP:8001/"
