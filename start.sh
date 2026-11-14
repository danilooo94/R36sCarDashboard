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

# 6. Execução do aplicativo unificado (MultiPageApp)
echo "[CarDataReader] Iniciando main.py..."
exec python3 main.py

