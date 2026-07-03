#!/bin/bash
# Монтирование RED OS 8.0 ISO через Redfish VirtualMedia
# Запуск: bash mount-iso-deploy.sh

set -e

ISO_URL="http://10.129.100.235:8888/redos8.iso"

BMC=("10.129.40.50" "10.129.40.51")
AUTH="techvirt:fhtfdh2!RF78"

echo "============================================"
echo "   Aither Platform — развёртывание RED OS 8.0"
echo "============================================"

for bmc in "${BMC[@]}"; do
    echo ""
    echo ">>> BMC: $bmc"
    
    # 1. Mount ISO как виртуальный CD-ROM
    echo "   Mount ISO..."
    RESP=$(curl -sk -u "$AUTH" -X POST \
        "https://$bmc/redfish/v1/Managers/bmc/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia" \
        -H "Content-Type: application/json" \
        -d "{\"Image\": \"$ISO_URL\", \"Inserted\": true, \"WriteProtected\": true}" \
        -w "\n%{http_code}" 2>/dev/null)
    
    HTTP_CODE=$(echo "$RESP" | tail -1)
    echo "   HTTP $HTTP_CODE"
    
    # 2. Установить загрузку с CD однократно
    echo "   Set BootOverride → Cd (Once)..."
    RESP=$(curl -sk -u "$AUTH" -X POST \
        "https://$bmc/redfish/v1/Systems/system/Actions/ComputerSystem.Reset" \
        -H "Content-Type: application/json" \
        -d '{"ResetType": "ForceOff"}' \
        -w "\n%{http_code}" 2>/dev/null)
    echo "   PowerOff: HTTP $(echo "$RESP" | tail -1)"
    
    sleep 5  # ждём выключения
    
    # Установить BootSourceOverride
    RESP=$(curl -sk -u "$AUTH" -X PATCH \
        "https://$bmc/redfish/v1/Systems/system" \
        -H "Content-Type: application/json" \
        -d '{"Boot": {"BootSourceOverrideEnabled": "Once", "BootSourceOverrideTarget": "Cd", "BootSourceOverrideMode": "UEFI"}}' \
        -w "\n%{http_code}" 2>/dev/null)
    echo "   BootOverride: HTTP $(echo "$RESP" | tail -1)"
    
    sleep 2
    
    # 3. Включить сервер
    echo "   PowerOn..."
    RESP=$(curl -sk -u "$AUTH" -X POST \
        "https://$bmc/redfish/v1/Systems/system/Actions/ComputerSystem.Reset" \
        -H "Content-Type: application/json" \
        -d '{"ResetType": "On"}' \
        -w "\n%{http_code}" 2>/dev/null)
    echo "   PowerOn: HTTP $(echo "$RESP" | tail -1)"
    
    echo "   >>> Сервер загружается с RED OS 8.0 ISO <<<"
done

echo ""
echo "============================================"
echo "Оба сервера загружаются с ISO."
echo "Подключитесь к Serial-over-LAN консоли BMC"
echo "для интерактивной установки."
echo "============================================"
