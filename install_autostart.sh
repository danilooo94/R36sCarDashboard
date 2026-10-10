#!/bin/bash
# ==============================================================================
# Script de Instalação do Serviço de Autostart (Systemd) no Armbian
# ==============================================================================

set -e

# Garante que está rodando no diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================================"
echo " Instalando inicialização automática do CarDataReader "
echo " Diretório do projeto: $PROJECT_DIR"
echo "======================================================"

# Torna o script de inicialização executável
chmod +x "$PROJECT_DIR/start.sh"

SERVICE_FILE="/etc/systemd/system/cardatareader.service"
CURRENT_USER="${SUDO_USER:-$USER}"

# Se estiver rodando como root mas houver SUDO_USER, ou padrão root
if [ -z "$CURRENT_USER" ] || [ "$CURRENT_USER" = "root" ]; then
    RUN_USER="root"
else
    RUN_USER="$CURRENT_USER"
fi

echo "Configurando serviço para executar como usuário: $RUN_USER"

# Criação do arquivo de unidade systemd
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=CarDataReader OBD HUD Dashboard
After=network.target bluetooth.target systemd-user-sessions.service
Wants=bluetooth.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/bin/bash $PROJECT_DIR/start.sh
Restart=always
RestartSec=3

# Acesso direto ao TTY/DRM para saída de vídeo em console (sem desktop)
StandardInput=tty
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
EOF"

echo "Arquivo de serviço criado em: $SERVICE_FILE"

# Recarrega configurações do systemd e habilita o serviço no boot
sudo systemctl daemon-reload
sudo systemctl enable cardatareader.service

echo ""
echo "======================================================"
echo " Instalação concluída com sucesso!"
echo " O CarDataReader iniciará automaticamente com o Armbian."
echo ""
echo " Comandos úteis:"
echo "   Iniciar agora:    sudo systemctl start cardatareader"
echo "   Parar serviço:    sudo systemctl stop cardatareader"
echo "   Ver status:       sudo systemctl status cardatareader"
echo "   Ver logs ao vivo: sudo journalctl -u cardatareader -f"
echo "   Desativar boot:   sudo systemctl disable cardatareader"
echo "======================================================"

