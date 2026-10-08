#!/bin/bash
# ==============================================================================
# CarDataReader - Script de Inicialização para Armbian / R36S
# ==============================================================================

# Entra no diretório onde o script está localizado
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[CarDataReader] Iniciando a partir de: $SCRIPT_DIR"

# 1. Ativa ambiente virtual Python (venv), caso exista
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo "[CarDataReader] Ativando virtualenv (venv)..."
    source "$SCRIPT_DIR/venv/bin/activate"
elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    echo "[CarDataReader] Ativando virtualenv (.venv)..."
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# 2. Configurações de exibição do Pygame
# Se houver servidor X11 rodando, usa x11; caso contrário, usa KMS/DRM direto no hardware
if [ -n "$DISPLAY" ]; then
    export SDL_VIDEODRIVER=x11
else
    export SDL_VIDEODRIVER=kmsdrm
    # Em consoles portáteis (R36S), pode ser necessário especificar a tty e card DRM
    export SDL_KMSDRM_DEVICE_INDEX=0
fi

# 3. Áudio (ALSA)
export SDL_AUDIODRIVER=alsa

# 4. Saída do Python sem buffer (logs em tempo real no journalctl)
export PYTHONUNBUFFERED=1

# 5. Permissões de porta serial (dialout)
if [ "$(id -u)" -ne 0 ]; then
    # Se não for root, assegura permissão de serial
    sudo usermod -a -G dialout,video,input "$USER" 2>/dev/null || true
fi

# 6. Suporte opcional a Bluetooth (se configurado com MAC e rfcomm no Linux)
if command -v rfcomm >/dev/null 2>&1; then
    # Se o config tiver um MAC e não existir /dev/rfcomm0, tenta vincular
    MAC=$(grep -E '^\s*OBD_MAC\s*=' config.py 2>/dev/null | cut -d'"' -f2 | cut -d"'" -f2)
    CONN=$(grep -E '^\s*OBD_CONNECTION\s*=' config.py 2>/dev/null | cut -d'"' -f2 | cut -d"'" -f2)
    if [ "$CONN" = "bluetooth" ] && [ -n "$MAC" ] && [ ! -e "/dev/rfcomm0" ]; then
        echo "[CarDataReader] Vinculando /dev/rfcomm0 ao MAC $MAC..."
        rfcomm bind 0 "$MAC" 2>/dev/null || true
    fi
fi

# 7. Execução do aplicativo unificado (MultiPageApp)
echo "[CarDataReader] Iniciando main.py..."
exec python3 main.py

