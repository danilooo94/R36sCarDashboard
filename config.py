SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
FPS = 60
FULLSCREEN = False   # True para sempre abrir em tela cheia (útil no R36S)
EXIT_KEY   = 97    # pygame.K_a — botão A no R36S / tecla 'a' no PC

MOCK_MODE = True    # True para testar sem adaptador OBD

OBD_CONNECTION    = "wifi"  # "serial", "bluetooth" (MAC) ou "wifi"

# --- Configurações para SERIAL ou BLUETOOTH PAREADO (COMx / rfcomm) ---
OBD_PORT          = "auto"    # "auto" detecta a porta, ou força ex: "COM3", "/dev/rfcomm0"
OBD_BAUD          = 38400     # 38400 (padrão ELM327), 115200, ou 9600

# --- Configurações para BLUETOOTH DIRETO (MAC Address) ---
# (Requer PyBluez instalado se não estiver usando rfcomm)
OBD_MAC           = "44:DC:C3:0D:67:A3"

# --- Configurações para WIFI ---
OBD_HOST          = "192.168.0.10"
OBD_WIFI_PORT     = 35000

OBD_POLL_INTERVAL = 0.01      # segundos entre ciclos de leitura (prioridade rápida a ~15-20 Hz)
ESP32_BAUD = 115200

# Navegação entre páginas
import pygame
PAGE_NEXT_KEY = pygame.K_RIGHT    # D-pad direita no R36S / seta direita no PC
PAGE_PREV_KEY = pygame.K_LEFT     # D-pad esquerda no R36S / seta esquerda no PC
START_PAGE    = 0                 # Página inicial (0 = HUD, 1 = Extras)

COLORS = {
    "bg":      (5,   5,   10),
    "primary": (0,   255, 200),
    "danger":  (255, 60,  50),
    "warning": (255, 190, 0),
    "text":    (240, 245, 255),
    "muted":   (80,  105, 115),
    "panel":   (18,  22,  28),
    "arc_bg":  (22,  32,  42),
    "divider": (35,  55,  65),
}

ALARM_SOUND  = False  # False para silenciar os beeps de alarme

LOG_ENABLED  = True
LOG_DIR      = "logs"
LOG_INTERVAL = 1.0   # segundos entre cada linha gravada no CSV

RPM_MAX      = 7000
RPM_REDLINE  = 5500
TEMP_MIN     = 40
TEMP_MAX     = 120
TEMP_HISTORY = 120  # amostras no gráfico

# --- Configurações da HUD Retrô (Expressões do Doomguy) ---
RETRO_TEMP_THRESHOLD = 100   # °C a partir do qual entra em chamas (burning)
RETRO_TEMP_ALERT     = 89    # °C a partir do qual o nicho pisca em vermelho transparente
RETRO_SPEED_HAPPY    = 80    # km/h mínimo para expressão feliz
RETRO_SPEED_SCARY    = 100   # km/h a partir do qual mostra expressão assustada

# --- Limiares de Cores para Indicadores (Temperatura e Tensão) ---
TEMP_COLOR_WARN        = 95.0    # °C a partir do qual a temperatura fica amarela
TEMP_COLOR_DANGER      = 105.0   # °C a partir do qual a temperatura fica vermelha
VOLT_COLOR_LOW_DANGER  = 11.8    # V abaixo do qual fica vermelho (bateria crítica)
VOLT_COLOR_LOW_WARN    = 13.0    # V abaixo do qual fica amarelo (bateria em repouso)
VOLT_COLOR_HIGH_WARN   = 14.8    # V acima do qual fica vermelho (sobretensão)
