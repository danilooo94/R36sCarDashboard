"""Traduções em Português Brasileiro (pt-BR)."""

STRINGS = {
    # Geral / Janela
    "app.window_title": "Painel Diário — OBD2",
    "app.header_title": "PAINEL DIÁRIO",

    # Tela de Inicialização / Conexão
    "conn.mode_usb":         "USB SERIAL",
    "conn.mode_mock":        "SIMULAÇÃO",
    "conn.obd_badge":        "OBD-II",
    "conn.title":            "Conectando à interface OBD-II",
    "conn.subtitle":         "Conecte o adaptador USB ELM327 e ligue a ignição",
    "conn.pill_port":        "PORTA USB",
    "conn.port_auto":        "AUTO",
    "conn.pill_baud":        "VELOCIDADE",
    "conn.pill_status":      "STATUS",
    "conn.status_searching": "BUSCANDO",
    "conn.status_connected": "CONECTADO",

    # Dashboard Principal (Daily Cockpit)
    "hud.trip":          "VIAGEM  {time}",
    "hud.iat_value":     "ADM {temp}°C",
    "hud.iat_empty":     "ADM --°C",
    "hud.rpm_unit":      "RPM x1000",
    "hud.speed_unit":    "KM/H",
    "hud.gear_neutral":  "N",
    "hud.gear_engaged":  "D{gear}",
    "hud.economy_title": "CONSUMO INSTANT.",
    "hud.economy_unit":  "km / litro",
    "hud.zero100_run":   "0-100: {time}s",
    "hud.zero100_best":  "MELHOR 0-100: {time}s",
    "hud.zero100_ready": "0-100: PRONTO",
    "hud.zero100_idle":  "0-100: --.-s",
    "hud.pill_water":    "ÁGUA",
    "hud.pill_oil":      "ÓLEO",
    "hud.pill_battery":  "BATERIA",
    "hud.pill_tps_boost": "ACEL / BOOST",

    # Mensagens de Log
    "log.session_start":        "=== sessão iniciada — log de erros: {path} ===",
    "log.recording_csv":        "Gravando dados em: {path}",
    "log.unhandled_loop_error": "Erro não tratado no loop principal",
    "log.session_end":          "=== sessão encerrada ===",
}
