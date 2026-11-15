"""English (en) translations."""

STRINGS = {
    # General / Window
    "app.window_title": "Daily Cockpit — OBD2",
    "app.header_title": "DAILY COCKPIT",

    # Startup / Connecting Screen
    "conn.mode_usb":         "USB SERIAL",
    "conn.mode_mock":        "SIMULATION",
    "conn.obd_badge":        "OBD-II",
    "conn.title":            "Connecting to OBD-II interface",
    "conn.subtitle":         "Plug in the USB ELM327 adapter and turn on ignition",
    "conn.pill_port":        "USB PORT",
    "conn.port_auto":        "AUTO",
    "conn.pill_baud":        "BAUD RATE",
    "conn.pill_status":      "STATUS",
    "conn.status_searching": "SEARCHING",
    "conn.status_connected": "CONNECTED",

    # Main Dashboard (Daily Cockpit)
    "hud.trip":          "TRIP  {time}",
    "hud.iat_value":     "IAT {temp}°C",
    "hud.iat_empty":     "IAT --°C",
    "hud.rpm_unit":      "RPM x1000",
    "hud.speed_unit":    "KM/H",
    "hud.gear_neutral":  "N",
    "hud.gear_engaged":  "D{gear}",
    "hud.economy_title": "INSTANT ECONOMY",
    "hud.economy_unit":  "km / liter",
    "hud.zero100_run":   "0-100: {time}s",
    "hud.zero100_best":  "BEST 0-100: {time}s",
    "hud.zero100_ready": "0-100: READY",
    "hud.zero100_idle":  "0-100: --.-s",
    "hud.pill_water":    "COOLANT",
    "hud.pill_oil":      "OIL TEMP",
    "hud.pill_battery":  "BATTERY",
    "hud.pill_tps_boost": "TPS / BOOST",

    # Log Messages
    "log.session_start":        "=== session started — error log: {path} ===",
    "log.recording_csv":        "Recording telemetry to: {path}",
    "log.unhandled_loop_error": "Unhandled error in main loop",
    "log.session_end":          "=== session ended ===",
}
