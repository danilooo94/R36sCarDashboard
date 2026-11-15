"""Telemetry log parser, daily slicer, KPI calculator, and file exporter.

Uses only the Python standard library so it runs without extra dependencies on
both the R36S handheld (Linux ARM64) and desktop environments.
"""
import csv
import io
import json
import os
import re
import threading
import zipfile
from datetime import datetime

import config

_SESSION_RE = re.compile(r"^session_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.csv$", re.IGNORECASE)

EXPORT_COLUMNS = [
    "session_file",
    "timestamp",
    "rpm",
    "speed_kmh",
    "oil_temp_c",
    "water_temp_c",
    "voltage_v",
    "throttle_pct",
    "load_pct",
    "intake_temp_c",
    "map_kpa",
    "maf_gs",
    "fuel_pct",
    "consumption_kml",
]

_NUMERIC_COLS = EXPORT_COLUMNS[2:]

_CACHE_LOCK = threading.Lock()
_FILE_CACHE = {}  # filename -> {"sig": (mtime_ns, size), "parsed": dict}


def _safe_float(val, default=0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _log_dir() -> str:
    return getattr(config, "LOG_DIR", "logs")


def _parse_session_file(filepath: str, filename: str) -> dict:
    """Parse a single `session_*.csv` into normalized rows grouped by date."""
    m = _SESSION_RE.match(filename)
    fallback_date = m.group(1) if m else "unknown"

    afr = float(getattr(config, "FUEL_AFR", 14.7))
    density = float(getattr(config, "FUEL_DENSITY_G_L", 745.0))

    rows_by_date = {}
    total_rows = 0

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                if not raw:
                    continue
                ts = (raw.get("timestamp") or "").strip()
                date_key = ts[:10] if len(ts) >= 10 and ts[4:5] == "-" and ts[7:8] == "-" else fallback_date
                if date_key == "unknown":
                    continue

                dt_obj = _parse_iso(ts)
                epoch = dt_obj.timestamp() if dt_obj is not None else None

                rpm = _safe_float(raw.get("rpm"))
                speed = _safe_float(raw.get("speed_kmh"))
                oil_c = _safe_float(raw.get("oil_temp_c"))
                water_c = _safe_float(raw.get("water_temp_c"))
                volt = _safe_float(raw.get("voltage_v"))
                throttle = _safe_float(raw.get("throttle_pct"))
                load = _safe_float(raw.get("load_pct"))
                intake_c = _safe_float(raw.get("intake_temp_c"))
                map_kpa = _safe_float(raw.get("map_kpa"))
                maf_gs = _safe_float(raw.get("maf_gs"))
                fuel_pct = _safe_float(raw.get("fuel_pct"))
                cons_kml = _safe_float(raw.get("consumption_kml"))

                if cons_kml <= 0.0 and speed >= 3.0 and maf_gs > 0.0:
                    lph = maf_gs * 3600.0 / (afr * density)
                    if lph > 0:
                        cons_kml = round(speed / lph, 2)

                rec = {
                    "session_file":    filename,
                    "timestamp":       ts,
                    "time_hms":        ts[11:19] if len(ts) >= 19 else ts,
                    "epoch":           epoch,
                    "rpm":             round(rpm, 1),
                    "speed_kmh":       round(speed, 2),
                    "oil_temp_c":      round(oil_c, 2),
                    "water_temp_c":    round(water_c, 2),
                    "voltage_v":       round(volt, 2),
                    "throttle_pct":    round(throttle, 1),
                    "load_pct":        round(load, 1),
                    "intake_temp_c":   round(intake_c, 1),
                    "map_kpa":         round(map_kpa, 1),
                    "maf_gs":          round(maf_gs, 2),
                    "fuel_pct":        round(fuel_pct, 1),
                    "consumption_kml": round(cons_kml, 2),
                }
                rows_by_date.setdefault(date_key, []).append(rec)
                total_rows += 1
    except OSError:
        pass

    try:
        file_size = os.path.getsize(filepath)
    except OSError:
        file_size = 0

    return {
        "filename":     filename,
        "size_bytes":   file_size,
        "total_rows":   total_rows,
        "rows_by_date": rows_by_date,
    }


def _load_index() -> dict:
    """Return cached index of all `session_*.csv` files, refreshing changed files."""
    folder = _log_dir()
    if not os.path.isdir(folder):
        return {}

    current_files = {}
    for entry in os.scandir(folder):
        if not entry.is_file():
            continue
        if not _SESSION_RE.match(entry.name):
            continue
        try:
            st = entry.stat()
            current_files[entry.name] = (entry.path, (st.st_mtime_ns, st.st_size))
        except OSError:
            continue

    with _CACHE_LOCK:
        # Prune deleted files
        stale = [k for k in _FILE_CACHE if k not in current_files]
        for k in stale:
            del _FILE_CACHE[k]

        # Parse new or modified files
        for fname, (fpath, sig) in current_files.items():
            cached = _FILE_CACHE.get(fname)
            if cached is None or cached["sig"] != sig:
                parsed = _parse_session_file(fpath, fname)
                _FILE_CACHE[fname] = {"sig": sig, "parsed": parsed}

        return {k: v["parsed"] for k, v in _FILE_CACHE.items()}


def _compute_metrics(rows: list) -> dict:
    """Compute comprehensive driving KPIs across an ordered list of rows."""
    if not rows:
        return {
            "samples":               0,
            "duration_s":            0.0,
            "engine_on_s":           0.0,
            "distance_km":           0.0,
            "max_speed_kmh":         0.0,
            "avg_moving_speed_kmh":  0.0,
            "max_rpm":               0.0,
            "avg_rpm":               0.0,
            "redline_s":             0.0,
            "max_water_c":           0.0,
            "avg_water_c":           0.0,
            "warn_water_s":          0.0,
            "max_oil_c":             0.0,
            "avg_oil_c":             0.0,
            "max_intake_c":          0.0,
            "min_voltage_v":         0.0,
            "max_voltage_v":         0.0,
            "avg_voltage_v":         0.0,
            "max_throttle_pct":      0.0,
            "max_load_pct":          0.0,
            "avg_consumption_kml":   0.0,
            "start_time":            "--:--:--",
            "end_time":              "--:--:--",
        }

    engine_rpm_min = float(getattr(config, "TRIP_ENGINE_ON_RPM", 400))
    redline_rpm = float(getattr(config, "RPM_REDLINE", 5500))
    warn_temp_c = float(getattr(config, "TEMP_COLOR_WARN", 95.0))
    default_dt = float(getattr(config, "LOG_INTERVAL", 1.0))

    duration_s = 0.0
    engine_on_s = 0.0
    distance_km = 0.0
    redline_s = 0.0
    warn_water_s = 0.0

    max_speed = 0.0
    moving_speeds = []

    max_rpm = 0.0
    active_rpms = []

    waters = []
    oils = []
    intakes = []
    volts = []
    cons_list = []

    max_throttle = 0.0
    max_load = 0.0

    prev_row = None
    for r in rows:
        dt = default_dt
        if prev_row is not None:
            if prev_row["session_file"] == r["session_file"] and prev_row["epoch"] and r["epoch"]:
                diff = r["epoch"] - prev_row["epoch"]
                dt = diff if 0.0 < diff <= 15.0 else default_dt
            elif prev_row["session_file"] != r["session_file"]:
                dt = default_dt
        prev_row = r

        duration_s += dt
        rpm = r["rpm"]
        spd = r["speed_kmh"]
        wat = r["water_temp_c"]
        oil = r["oil_temp_c"]
        vlt = r["voltage_v"]
        thr = r["throttle_pct"]
        lod = r["load_pct"]
        iat = r["intake_temp_c"]
        kml = r["consumption_kml"]

        if rpm >= engine_rpm_min:
            engine_on_s += dt
            active_rpms.append(rpm)
        if rpm >= redline_rpm:
            redline_s += dt
        if rpm > max_rpm:
            max_rpm = rpm

        if spd > max_speed:
            max_speed = spd
        if spd >= 2.0:
            moving_speeds.append(spd)
        if spd > 0.0:
            distance_km += (spd / 3600.0) * dt

        if wat > 0.0:
            waters.append(wat)
            if wat >= warn_temp_c:
                warn_water_s += dt
        if oil > 0.0:
            oils.append(oil)
        if iat > 0.0:
            intakes.append(iat)
        if vlt > 5.0:
            volts.append(vlt)
        if kml > 0.0:
            cons_list.append(kml)

        if thr > max_throttle:
            max_throttle = thr
        if lod > max_load:
            max_load = lod

    return {
        "samples":               len(rows),
        "duration_s":            round(duration_s, 1),
        "engine_on_s":           round(engine_on_s, 1),
        "distance_km":           round(distance_km, 2),
        "max_speed_kmh":         round(max_speed, 1),
        "avg_moving_speed_kmh":  round(sum(moving_speeds) / len(moving_speeds), 1) if moving_speeds else 0.0,
        "max_rpm":               round(max_rpm, 0),
        "avg_rpm":               round(sum(active_rpms) / len(active_rpms), 0) if active_rpms else 0.0,
        "redline_s":             round(redline_s, 1),
        "max_water_c":           round(max(waters), 1) if waters else 0.0,
        "avg_water_c":           round(sum(waters) / len(waters), 1) if waters else 0.0,
        "warn_water_s":          round(warn_water_s, 1),
        "max_oil_c":             round(max(oils), 1) if oils else 0.0,
        "avg_oil_c":             round(sum(oils) / len(oils), 1) if oils else 0.0,
        "max_intake_c":          round(max(intakes), 1) if intakes else 0.0,
        "min_voltage_v":         round(min(volts), 2) if volts else 0.0,
        "max_voltage_v":         round(max(volts), 2) if volts else 0.0,
        "avg_voltage_v":         round(sum(volts) / len(volts), 2) if volts else 0.0,
        "max_throttle_pct":      round(max_throttle, 1),
        "max_load_pct":          round(max_load, 1),
        "avg_consumption_kml":   round(sum(cons_list) / len(cons_list), 2) if cons_list else 0.0,
        "start_time":            rows[0]["time_hms"],
        "end_time":              rows[-1]["time_hms"],
    }


def _downsample_rows(rows: list, max_points: int = 900) -> list:
    """Peak-preserving bucket downsampling so large daily logs render smoothly."""
    n = len(rows)
    if n <= max_points:
        return [
            {
                "t":   r["time_hms"],
                "s":   r["session_file"],
                "rpm": r["rpm"],
                "spd": r["speed_kmh"],
                "wat": r["water_temp_c"],
                "oil": r["oil_temp_c"],
                "vlt": r["voltage_v"],
                "thr": r["throttle_pct"],
                "lod": r["load_pct"],
                "iat": r["intake_temp_c"],
                "kml": r["consumption_kml"],
                "ful": r["fuel_pct"],
            }
            for r in rows
        ]

    # Each bucket emits up to 2 points (min speed/rpm and max speed/rpm in time order)
    buckets = max(1, max_points // 2)
    step = n / buckets
    sampled = []
    for b in range(buckets):
        i0 = int(b * step)
        i1 = min(n, int((b + 1) * step))
        chunk = rows[i0:i1]
        if not chunk:
            continue
        if len(chunk) == 1:
            picks = [chunk[0]]
        else:
            min_idx = min(range(len(chunk)), key=lambda i: (chunk[i]["speed_kmh"], chunk[i]["rpm"]))
            max_idx = max(range(len(chunk)), key=lambda i: (chunk[i]["speed_kmh"], chunk[i]["rpm"]))
            if min_idx == max_idx:
                picks = [chunk[0]]
            elif min_idx < max_idx:
                picks = [chunk[min_idx], chunk[max_idx]]
            else:
                picks = [chunk[max_idx], chunk[min_idx]]
        for r in picks:
            sampled.append({
                "t":   r["time_hms"],
                "s":   r["session_file"],
                "rpm": r["rpm"],
                "spd": r["speed_kmh"],
                "wat": r["water_temp_c"],
                "oil": r["oil_temp_c"],
                "vlt": r["voltage_v"],
                "thr": r["throttle_pct"],
                "lod": r["load_pct"],
                "iat": r["intake_temp_c"],
                "kml": r["consumption_kml"],
                "ful": r["fuel_pct"],
            })
    return sampled


def get_storage_overview() -> dict:
    """Fast overview used by the R36S WebServerPage UI and web header."""
    idx = _load_index()
    days = set()
    total_rows = 0
    total_bytes = 0
    for item in idx.values():
        total_rows += item["total_rows"]
        total_bytes += item["size_bytes"]
        for d, drows in item["rows_by_date"].items():
            if drows:
                days.add(d)

    best_0_100 = None
    best_path = getattr(config, "BEST_0_100_FILE", "logs/best_0_100.json")
    if os.path.isfile(best_path):
        try:
            with open(best_path, "r", encoding="utf-8") as fh:
                best_0_100 = json.load(fh).get("best")
        except Exception:
            best_0_100 = None

    return {
        "days_count":     len(days),
        "sessions_count": len(idx),
        "total_rows":     total_rows,
        "total_bytes":    total_bytes,
        "best_0_100":     round(float(best_0_100), 2) if best_0_100 else None,
    }


def list_daily_slices() -> list:
    """Return all recorded dates newest-first with quick daily summary stats."""
    idx = _load_index()
    by_day = {}
    for fname, item in idx.items():
        for d, drows in item["rows_by_date"].items():
            if not drows:
                continue
            bucket = by_day.setdefault(d, {"sessions": set(), "rows": []})
            bucket["sessions"].add(fname)
            bucket["rows"].extend(drows)

    result = []
    for d in sorted(by_day.keys(), reverse=True):
        rows = by_day[d]["rows"]
        rows.sort(key=lambda r: (r["timestamp"], r["session_file"]))
        metrics = _compute_metrics(rows)
        result.append({
            "date":           d,
            "sessions_count": len(by_day[d]["sessions"]),
            "samples":        metrics["samples"],
            "duration_s":     metrics["duration_s"],
            "distance_km":    metrics["distance_km"],
            "max_speed_kmh":  metrics["max_speed_kmh"],
            "max_rpm":        metrics["max_rpm"],
            "max_water_c":    metrics["max_water_c"],
        })
    return result


def get_daily_slice(date_str: str, session_filter: str = None) -> dict:
    """Return full KPIs, per-session breakdown, and chart series for `date_str`."""
    idx = _load_index()
    sessions_meta = []
    combined_rows = []

    for fname in sorted(idx.keys()):
        item = idx[fname]
        drows = item["rows_by_date"].get(date_str)
        if not drows:
            continue
        s_rows = sorted(drows, key=lambda r: r["timestamp"])
        s_metrics = _compute_metrics(s_rows)
        sessions_meta.append({
            "filename":      fname,
            "size_bytes":    item["size_bytes"],
            "samples":       s_metrics["samples"],
            "start_time":    s_metrics["start_time"],
            "end_time":      s_metrics["end_time"],
            "duration_s":    s_metrics["duration_s"],
            "distance_km":   s_metrics["distance_km"],
            "max_speed_kmh": s_metrics["max_speed_kmh"],
            "max_rpm":       s_metrics["max_rpm"],
            "max_water_c":   s_metrics["max_water_c"],
            "max_oil_c":     s_metrics["max_oil_c"],
            "min_voltage_v": s_metrics["min_voltage_v"],
        })
        if not session_filter or session_filter == fname:
            combined_rows.extend(s_rows)

    combined_rows.sort(key=lambda r: (r["timestamp"], r["session_file"]))
    metrics = _compute_metrics(combined_rows)
    series = _downsample_rows(combined_rows, max_points=960)

    return {
        "date":            date_str,
        "session_filter":  session_filter or "",
        "sessions_count":  len(sessions_meta),
        "metrics":         metrics,
        "sessions":        sessions_meta,
        "series":          series,
        "thresholds": {
            "temp_warn":  float(getattr(config, "TEMP_COLOR_WARN", 95.0)),
            "temp_danger": float(getattr(config, "TEMP_COLOR_DANGER", 105.0)),
            "rpm_redline": float(getattr(config, "RPM_REDLINE", 5500)),
            "volt_low":    float(getattr(config, "VOLT_COLOR_LOW_WARN", 13.0)),
        },
    }


def _collect_day_rows(date_str: str):
    idx = _load_index()
    rows = []
    files = []
    for fname in sorted(idx.keys()):
        drows = idx[fname]["rows_by_date"].get(date_str)
        if drows:
            files.append(fname)
            rows.extend(drows)
    rows.sort(key=lambda r: (r["timestamp"], r["session_file"]))
    return rows, files


def export_daily_csv(date_str: str) -> bytes:
    """Generate consolidated daily slice CSV (`daily_YYYY-MM-DD.csv`) in memory."""
    rows, _ = _collect_day_rows(date_str)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({col: r.get(col, "") for col in EXPORT_COLUMNS})
    return buf.getvalue().encode("utf-8")


def export_daily_json(date_str: str) -> bytes:
    """Generate analytical daily slice summary + series JSON."""
    payload = get_daily_slice(date_str)
    payload["generated_at"] = datetime.now().isoformat(timespec="seconds")
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def export_daily_zip(date_str: str) -> bytes:
    """Generate a ZIP package with consolidated daily CSV, JSON report, and raw CSVs."""
    rows, files = _collect_day_rows(date_str)
    mem = io.BytesIO()
    folder = _log_dir()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"daily_{date_str}.csv", export_daily_csv(date_str))
        zf.writestr(f"daily_report_{date_str}.json", export_daily_json(date_str))
        for fname in files:
            raw_path = os.path.join(folder, fname)
            if os.path.isfile(raw_path):
                zf.write(raw_path, arcname=f"raw_sessions/{fname}")
    return mem.getvalue()


def export_all_zip() -> bytes:
    """Generate a complete ZIP backup of all recorded CSV sessions and records."""
    mem = io.BytesIO()
    folder = _log_dir()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if os.path.isdir(folder):
            for entry in sorted(os.listdir(folder)):
                if _SESSION_RE.match(entry) or entry == "best_0_100.json":
                    fpath = os.path.join(folder, entry)
                    if os.path.isfile(fpath):
                        zf.write(fpath, arcname=entry)
    return mem.getvalue()


def get_raw_session_path(filename: str):
    """Safely resolve a raw `session_*.csv` file path, preventing path traversal."""
    if not filename or "/" in filename or "\\" in filename:
        return None
    if not _SESSION_RE.match(filename):
        return None
    base_dir = os.path.abspath(_log_dir())
    target = os.path.abspath(os.path.join(base_dir, filename))
    if os.path.commonpath([base_dir, target]) != base_dir:
        return None
    return target if os.path.isfile(target) else None
