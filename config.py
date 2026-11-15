SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
FPS = 60
FULLSCREEN = False   # True para sempre abrir em tela cheia (útil no R36S)
EXIT_KEY   = 97    # pygame.K_a — botão A no R36S / tecla 'a' no PC
SHOW_CONSOLE_BATTERY = True  # Exibe ícone + % da bateria do R36S no topo da tela
LANGUAGE   = "en"         # Idioma: "pt-BR" (Português Brasileiro) ou "en" (English)
LANGUAGE   = "pt-BR"         # Idioma: "pt-BR" (Português Brasileiro) ou "en" (English)

MOCK_MODE = False    # True para testar sem adaptador OBD

# --- Configurações de Conexão USB Serial (ELM327 / OBD-II) ---
OBD_PORT          = "auto"    # "auto" detecta a porta USB, ou força ex: "COM3", "/dev/ttyUSB0"
OBD_BAUD          = 38400     # 38400 (padrão ELM327), 115200, ou 9600
OBD_POLL_INTERVAL = 0.01      # segundos entre ciclos de leitura (prioridade rápida a ~15-20 Hz)

# Navegação entre páginas e atalho de idioma
import pygame
PAGE_NEXT_KEY = pygame.K_RIGHT    # D-pad direita no R36S / seta direita no PC
PAGE_PREV_KEY = pygame.K_LEFT     # D-pad esquerda no R36S / seta esquerda no PC
LANG_KEY      = pygame.K_l        # Tecla 'l' no PC para alternar idioma (pt-BR <-> en)
LANG_BUTTON   = 3                 # Botão Y no R36S / gamepad para alternar idioma ao vivo
START_PAGE    = 0                 # Página inicial (0 = Daily Cockpit)

COLORS = {
    "bg":      (11,  16,  23),
    "primary": (56,  189, 248),
    "danger":  (239, 68,  68),
    "warning": (245, 158, 11),
    "text":    (248, 250, 252),
    "muted":   (148, 163, 184),
    "panel":   (17,  24,  36),
    "arc_bg":  (30,  41,  59),
    "divider": (30,  41,  59),
}

ALARM_SOUND  = False  # False para silenciar os beeps de alarme

# --- Configurações de Logs (Telemetria CSV + Diagnóstico de Erros) ---
LOG_ENABLED  = False  # False desabilita todos os logs (CSV e errors_*.txt); True habilita
LOG_DIR      = "logs"
LOG_INTERVAL = 1.0    # segundos entre cada linha gravada no CSV

RPM_MAX      = 7000
RPM_REDLINE  = 5500
TEMP_MIN     = 40
TEMP_MAX     = 120
TEMP_HISTORY = 120  # amostras no gráfico

# --- Limiares de Cores para Indicadores (Temperatura e Tensão) ---
TEMP_COLOR_WARN        = 95.0    # °C a partir do qual a temperatura fica amarela
TEMP_COLOR_DANGER      = 105.0   # °C a partir do qual a temperatura fica vermelha
VOLT_COLOR_LOW_DANGER  = 11.8    # V abaixo do qual fica vermelho (bateria crítica)
VOLT_COLOR_LOW_WARN    = 13.0    # V abaixo do qual fica amarelo (bateria em repouso)
VOLT_COLOR_HIGH_WARN   = 14.8    # V acima do qual fica vermelho (sobretensão)

# --- HUD Telemetria & Indicadores Avancados ---
SPEED_MAX                = 200     # km/h fundo de escala do velocimetro
SHIFT_RPM                = 5300    # RPM em que acende o shift light
BOOST_MAX_BAR            = 2.0     # bar fundo de escala da barra de turbo
BAROMETRIC_KPA           = 101.3   # Pressao atmosferica de referencia (kPa)
FUEL_AFR                 = 14.7    # Relacao estequiometrica ar/combustivel (gasolina)
FUEL_DENSITY_G_L         = 745.0   # Densidade da gasolina (g/L)
GEAR_RPM_PER_KMH         = {1: 118, 2: 70, 3: 49, 4: 37, 5: 30} # Relacao RPM/(km/h) por marcha
ZERO_TO_HUNDRED_TARGET   = 100.0   # Velocidade alvo do teste de aceleracao (km/h)
BEST_0_100_FILE          = 'logs/best_0_100.json'
TRIP_ENGINE_ON_RPM       = 400     # RPM minimo considerado como motor ligado para o Trip
