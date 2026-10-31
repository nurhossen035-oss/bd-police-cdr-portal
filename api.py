"""BD Police CDR Intelligence Platform — FastAPI application."""

import io
import os
import re
import secrets
import urllib.parse
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Cookie, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

app = FastAPI(title="BD Police CDR Intelligence Platform")

# Set these as Render Environment Variables before production deployment.
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "police123")
CONTACT_NUMBER = os.getenv("CONTACT_NUMBER", "01828941367")
SESSION_SECRET = os.getenv("SESSION_SECRET", "CHANGE-ME-before-production-" + secrets.token_urlsafe(24))
SESSION_COOKIE = "cdr_session"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
SESSION_SERIALIZER = URLSafeTimedSerializer(SESSION_SECRET, salt="cdr-session-v1")
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

app.state.session_secret_configured = bool(os.getenv("SESSION_SECRET"))


def valid_session(token: Optional[str]) -> bool:
    if not token:
        return False
    try:
        payload = SESSION_SERIALIZER.loads(token, max_age=8 * 60 * 60)
        return payload.get("authenticated") is True
    except (BadSignature, SignatureExpired, AttributeError):
        return False


def normalize_col(value):
    return re.sub(r"[^a-z0-9]", "", str(value).replace("\ufeff", "").strip().lower())


def find_col(columns, candidates):
    normalized = {normalize_col(c): c for c in columns}
    for candidate in candidates:
        key = normalize_col(candidate)
        if key in normalized:
            return normalized[key]
    # Cautious fallback: avoid matching generic words such as "time" too early.
    for candidate in candidates:
        key = normalize_col(candidate)
        if len(key) >= 5:
            for norm, original in normalized.items():
                if key in norm:
                    return original
    return None


def header_score(columns):
    names = {normalize_col(c) for c in columns}
    groups = [
        {"start", "startdttime", "startdatetime", "starttime", "datetime", "calldatetime", "timestamp"},
        {"calldate", "date", "startdate", "eventdate"},
        {"calltime", "time", "timeonly", "eventtime"},
        {"bparty", "bpartya", "callednumber", "calledparty", "dialednumber", "otherparty"},
        {"duration", "durationsec", "callduration", "dur", "talktime"},
        {"lac", "lacstarta", "cellid", "ci", "cgi", "imei", "imsi"}
    ]
    score = sum(1 for group in groups if names.intersection(group))
    return score


def read_uploaded_data(contents: bytes, ext: str) -> pd.DataFrame:
    candidates = []
    errors = []
    for skiprows in range(0, 6):
        try:
            if ext == ".csv":
                frame = None
                for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
                    try:
                        frame = pd.read_csv(io.BytesIO(contents), encoding=encoding,
                                            sep=None, engine="python",
                                            skiprows=skiprows)
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
                        errors.append(str(exc))
                if frame is None:
                    continue
            elif ext in {".xlsx", ".xls"}:
                frame = pd.read_excel(io.BytesIO(contents), sheet_name=0, skiprows=skiprows)
            else:
                raise ValueError("শুধু CSV, XLSX অথবা XLS ফাইল গ্রহণযোগ্য।")
            if frame is not None and not frame.empty:
                frame.columns = [str(c).replace("\ufeff", "").strip() for c in frame.columns]
                score = header_score(frame.columns)
                candidates.append((score, -skiprows, frame))
        except ImportError as exc:
            if ext == ".xls":
                raise ValueError("পুরোনো .xls ফাইল পড়তে xlrd প্যাকেজ প্রয়োজন। requirements.txt আপডেট করে পুনরায় Deploy করুন।") from exc
            raise
        except Exception as exc:
            errors.append(str(exc))
    if not candidates:
        raise ValueError("ফাইলের হেডার বা ডেটা পড়া যায়নি। " + (errors[-1] if errors else ""))
    # Prefer the strongest header match; ties prefer the first row as header.
    score, _, selected = max(candidates, key=lambda item: (item[0], item[1]))
    if score < 1:
        raise ValueError("CDR-এর প্রয়োজনীয় কলাম শনাক্ত করা যায়নি। ফাইলের প্রথম ৬টি সারিতে হেডার আছে কি না পরীক্ষা করুন।")
    return selected


def parse_dt(value):
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, datetime)):
        dt = pd.to_datetime(value, errors="coerce")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if number <= 0:
            return pd.NaT
        digits = str(int(number)) if number.is_integer() else ""
        if len(digits) == 14:
            dt = pd.to_datetime(digits, format="%Y%m%d%H%M%S", errors="coerce")
        elif number.is_integer() and 20000 <= number <= 80000:
            dt = pd.to_datetime(number, unit="D", origin="1899-12-30", errors="coerce")
        else:
            return pd.NaT
    else:
        raw = str(value).strip()
        if not raw or raw.lower() in {"nan", "nat", "none", "null", "0", "0.0"}:
            return pd.NaT
        raw = re.sub(r"\.0$", "", raw)
        if re.fullmatch(r"\d{14}", raw):
            dt = pd.to_datetime(raw, format="%Y%m%d%H%M%S", errors="coerce")
        elif re.fullmatch(r"\d{8}", raw):
            dt = pd.to_datetime(raw, format="%Y%m%d", errors="coerce")
        elif re.fullmatch(r"\d{4,6}(?:\.\d+)?", raw):
            try:
                serial = float(raw)
                dt = (pd.to_datetime(serial, unit="D", origin="1899-12-30", errors="coerce")
                      if 20000 <= serial <= 80000 else pd.NaT)
            except (ValueError, OverflowError):
                dt = pd.NaT
        else:
            try:
                dt = pd.to_datetime(raw, errors="coerce", dayfirst=True, format="mixed")
            except (TypeError, ValueError):
                dt = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return pd.NaT
    dt = pd.Timestamp(dt)
    return dt if 2000 <= dt.year <= 2100 else pd.NaT


def parse_date_time(date_value, time_value=None):
    date_dt = parse_dt(date_value)
    if pd.isna(date_dt) or time_value is None or pd.isna(time_value):
        return date_dt
    # Do not append a time if the date cell already contains a non-midnight time.
    if date_dt.hour or date_dt.minute or date_dt.second:
        return date_dt
    raw_time = str(time_value).strip()
    if not raw_time or raw_time.lower() in {"nan", "none", "null", "nat"}:
        return date_dt
    try:
        fraction = float(raw_time)
        if 0 <= fraction < 1 and re.fullmatch(r"\d+(?:\.\d+)?", raw_time):
            seconds = round(fraction * 86400)
            hh, rem = divmod(seconds, 3600)
            mm, ss = divmod(rem, 60)
            raw_time = f"{hh % 24:02d}:{mm:02d}:{ss:02d}"
    except ValueError:
        pass
    combined = pd.to_datetime(f"{date_dt.strftime('%Y-%m-%d')} {raw_time}",
                              errors="coerce")
    return combined if not pd.isna(combined) else date_dt


def clean_number(value):
    if pd.isna(value):
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none", "null"}:
        return None
    if re.fullmatch(r"\d+\.0", raw):
        raw = raw[:-2]
    if re.fullmatch(r"\d+(?:\.\d+)?[eE][+-]?\d+", raw):
        try:
            raw = format(int(float(raw)), "d")
        except (ValueError, OverflowError):
            return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("8801") and len(digits) == 13:
        digits = "0" + digits[3:]
    elif digits.startswith("880") and len(digits) == 13:
        digits = digits[3:]
    if len(digits) == 11 and digits.startswith("01"):
        return digits
    return digits if len(digits) >= 5 else None


def duration_seconds(value):
    if pd.isna(value):
        return 0
    raw = str(value).strip()
    if not raw:
        return 0
    if ":" in raw:
        parts = raw.split(":")
        try:
            nums = [int(float(x)) for x in parts]
            if len(nums) == 3:
                return max(0, nums[0] * 3600 + nums[1] * 60 + nums[2])
            if len(nums) == 2:
                return max(0, nums[0] * 60 + nums[1])
        except ValueError:
            return 0
    try:
        return max(0, int(float(raw)))
    except (ValueError, OverflowError):
        return 0


def fmt_duration(seconds):
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds} সে."
    if seconds < 3600:
        return f"{seconds // 60} মি. {seconds % 60} সে."
    return f"{seconds // 3600} ঘ. {(seconds % 3600) // 60} মি."


def safe_scalar(value):
    if pd.isna(value):
        return ""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def process_cdr(contents: bytes, filename: str) -> dict:
    ext = os.path.splitext(filename.lower())[1]
    df = read_uploaded_data(contents, ext)
    if df is None or df.empty:
        raise ValueError("ফাইলে কোনো ডেটা পাওয়া যায়নি।")
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    source_row_count = int(len(df))

    dt_col = find_col(df.columns, [
        "START_DTTIME", "START_DATETIME", "START_DATE_TIME", "CALL_DATETIME",
        "CALL_START_TIME", "DATETIME", "DATE_TIME", "EVENT_TIMESTAMP", "TIMESTAMP",
        "START_TIME", "STARTTIME", "START"
    ])
    date_col = find_col(df.columns, [
        "CALL_DATE", "DATE", "START_DATE", "EVENT_DATE", "TRANSACTION_DATE", "CALLING_DATE"
    ])
    time_col = find_col(df.columns, [
        "CALL_TIME", "TIME_ONLY", "START_CLOCK", "EVENT_CLOCK", "CALLING_TIME", "START_TIME", "STARTTIME", "TIME"
    ])
    # A START_TIME column that only contains clock time must be combined with date.
    full_dates = pd.Series([pd.NaT] * len(df), index=df.index, dtype="datetime64[ns]")
    if dt_col:
        parsed = df[dt_col].map(parse_dt)
        if parsed.notna().any():
            full_dates = pd.to_datetime(parsed, errors="coerce")
    if full_dates.isna().all() and date_col:
        full_dates = pd.to_datetime([
            parse_date_time(d, df[time_col].iloc[i] if time_col else None)
            for i, d in enumerate(df[date_col].tolist())
        ], errors="coerce")
    if full_dates.isna().all():
        sample_cols = ", ".join(map(str, df.columns[:30]))
        raise ValueError("তারিখ/সময় কলাম শনাক্ত করা যায়নি। পাওয়া কলাম: " + sample_cols)

    b_col = find_col(df.columns, [
        "B_PARTY", "BPARTY", "CALLED_NUMBER", "CALLED_PARTY", "DIALED_NUMBER",
        "OTHER_PARTY", "DESTINATION_NUMBER", "MSISDN_B", "CALLED", "TO"
    ])
    # Explicitly avoid treating generic "number" as B-party when A-party is also present.
    if b_col is None:
        b_col = find_col(df.columns, ["DESTINATION", "DIALED", "OTHER_PARTY_NUMBER"])
    a_col = find_col(df.columns, ["A_PARTY", "APARTY", "CALLING_NUMBER", "ORIGINATING_NUMBER"])
    dur_col = find_col(df.columns, ["DURATION_SEC", "CALL_DURATION", "DURATION", "DUR", "TALK_TIME", "HOLDING_TIME"])
    type_col = find_col(df.columns, ["CALL_TYPE", "USAGE_TYPE", "SERVICE_TYPE", "EVENT_TYPE", "TYPE"])
    imsi_col = find_col(df.columns, ["IMSI", "CALLING_IMSI"])
    imei_col = find_col(df.columns, ["IMEI", "CALLING_IMEI"])
    address_col = find_col(df.columns, [
        "SITE_ADDRESS", "TOWER_ADDRESS", "ADDRESS", "SITE_NAME", "CELL_NAME",
        "LOCATION_DESCRIPTION", "ADDRESS_TEXT"
    ])
    lac_col = find_col(df.columns, ["LAC_START_A", "LAC", "FIRST_LAC", "LAST_LAC", "LOCATION_AREA_CODE"])
    ci_col = find_col(df.columns, ["CI_START_A", "CELL_ID", "CELLID", "CI", "CGI", "CELL_IDENTITY"])

    df["Full_DateTime"] = full_dates
    df["Call_Date"] = df["Full_DateTime"].dt.strftime("%Y-%m-%d").fillna("N/A")
    df["Call_Time"] = df["Full_DateTime"].dt.strftime("%H:%M:%S").fillna("N/A")
    df["B_Party"] = df[b_col].map(clean_number) if b_col else None
    df["Duration_Sec"] = df[dur_col].map(duration_seconds) if dur_col else 0
    df["Duration_Formatted"] = df["Duration_Sec"].map(fmt_duration)

    # An address is displayed only when the source CDR explicitly contains an address.
    # LAC/Cell identifiers are not geographic coordinates and must never be presented as a location.
    def valid_text(value):
        if pd.isna(value):
            return ""
        text = str(value).strip()
        return "" if text.lower() in {"", "nan", "none", "null", "nat", "0", "n/a", "-"} else text

    df["Location"] = df[address_col].map(valid_text) if address_col else ""
    def cell_ref(row):
        lac = valid_text(row[lac_col]) if lac_col else ""
        ci = valid_text(row[ci_col]) if ci_col else ""
        parts = []
        if lac:
            parts.append("LAC: " + lac)
        if ci:
            parts.append("Cell ID: " + ci)
        return " | ".join(parts)
    df["Cell_Reference"] = df.apply(cell_ref, axis=1)

    def map_url(address):
        address = valid_text(address)
        if len(address) < 4:
            return ""
        query = address if "bangladesh" in address.lower() else address + ", Bangladesh"
        return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query, safe="")
    df["Map_URL"] = df["Location"].map(map_url)

    if type_col:
        type_text = df[type_col].astype(str).str.upper()
        voice_mask = ~type_text.str.contains(r"SMS|TEXT|MMS|PROMO", regex=True, na=False)
        if voice_mask.any():
            df = df.loc[voice_mask].copy()

    valid_df = df[df["B_Party"].notna() & (df["B_Party"] != "")].copy()
    night_df = df[df["Full_DateTime"].notna() &
                  (df["Full_DateTime"].dt.hour >= 0) &
                  (df["Full_DateTime"].dt.hour < 6)].copy()

    top_count = [
        {"number": str(number), "count": int(count)}
        for number, count in valid_df["B_Party"].value_counts().head(5).items()
    ]
    top_duration = [
        {"number": str(number), "duration": fmt_duration(total)}
        for number, total in valid_df.groupby("B_Party")["Duration_Sec"].sum()
            .sort_values(ascending=False).head(5).items()
    ]
    loc_df = df[df["Location"].astype(str).str.len() > 0]
    top_locations = []
    if not loc_df.empty:
        for loc, count in loc_df["Location"].value_counts().head(5).items():
            url = loc_df.loc[loc_df["Location"] == loc, "Map_URL"].iloc[0]
            top_locations.append({"location": str(loc), "count": int(count), "map_url": str(url)})

    def records(frame):
        result = []
        cols = ["B_Party", "Call_Date", "Call_Time", "Duration_Formatted",
                "Duration_Sec", "Location", "Cell_Reference", "Map_URL"]
        for _, row in frame.iterrows():
            result.append({col: safe_scalar(row.get(col, "")) for col in cols})
        return result

    primary_imsi = valid_text(df[imsi_col].dropna().iloc[0]) if imsi_col and not df[imsi_col].dropna().empty else ""
    primary_imei = valid_text(df[imei_col].dropna().iloc[0]) if imei_col and not df[imei_col].dropna().empty else ""
    total_seconds = int(valid_df["Duration_Sec"].sum()) if not valid_df.empty else 0

    return {
        "total_calls": int(len(valid_df)),
        "total_duration_formatted": fmt_duration(total_seconds),
        "primary_imsi": primary_imsi,
        "primary_imei": primary_imei,
        "night_calls_count": int(len(night_df)),
        "top_by_count": top_count,
        "top_by_duration": top_duration,
        "top_locations": top_locations,
        "all_calls_details": records(valid_df),
        "night_calls_details": records(night_df),
        "total_rows": source_row_count,
        "valid_datetime_rows": int(df["Full_DateTime"].notna().sum()),
        "invalid_datetime_rows": int(df["Full_DateTime"].isna().sum())
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "CDR Intelligence API"}


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - CDR Investigation Portal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700;800&display=swap');
        body { background:linear-gradient(135deg,#dbeafe 0%,#f0fdfa 48%,#ede9fe 100%) !important; font-family:'Noto Sans Bengali','Hind Siliguri',sans-serif !important; height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-card { background:rgba(255,255,255,.97) !important; color:#172554 !important; border:1px solid #dbeafe !important; box-shadow:0 24px 70px rgba(37,99,235,.18) !important; padding: 40px; border-radius: 20px; width: 100%; max-width: 400px; }
        .login-card h3 { color:#172554 !important; }
        .login-card .text-muted,.login-card .text-secondary { color:#52627a !important; }
        .login-card .form-control { background:#fff !important; color:#172554 !important; border:1px solid #cbd5e1 !important; }
        .login-card .form-control::placeholder { color:#94a3b8 !important; }
        .login-card button { background:linear-gradient(110deg,#2563eb,#7c3aed) !important; box-shadow:0 8px 20px rgba(79,70,229,.22); border: none; }
    </style>
</head>
<body>
    <div class="login-card text-center">
        <div class="mb-3 text-indigo">
            <i class="fa-solid fa-shield-halved fa-3x text-primary"></i>
        </div>
        <h3 class="fw-bold text-dark mb-1">CDR সিকিউর পোর্টাল</h3>
        <p class="text-muted mb-4">লগইন করতে আপনার ইউজারনেম ও পাসওয়ার্ড দিন</p>
        
        <form action="/login" method="POST">
            <div class="mb-3 text-start">
                <label class="form-label fw-bold text-secondary">ইউজারনেম</label>
                <input type="text" name="username" class="form-control rounded-pill px-3 py-2" required placeholder="ইউজারনেম দিন">
            </div>
            
            <div class="mb-4 text-start">
                <label class="form-label fw-bold text-secondary">পাসওয়ার্ড</label>
                <div class="position-relative">
                    <input type="password" name="password" id="passwordField" class="form-control rounded-pill px-3 py-2 pe-5" required placeholder="আপনার পাসওয়ার্ড দিন">
                    <span class="position-absolute top-50 end-0 translate-middle-y me-3 text-secondary" id="togglePassword" style="cursor: pointer;">
                        <i class="fa-solid fa-eye" id="eyeIcon"></i>
                    </span>
                </div>
            </div>

            <button type="submit" class="btn btn-primary w-100 py-2 rounded-pill fw-bold shadow-sm">
                <i class="fa-solid fa-right-to-bracket me-1"></i> লগইন করুন
            </button>
        </form>
    </div>

    <script>
        const togglePassword = document.getElementById('togglePassword');
        const passwordField = document.getElementById('passwordField');
        const eyeIcon = document.getElementById('eyeIcon');

        togglePassword.addEventListener('click', function () {
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            
            if (type === 'text') {
                eyeIcon.classList.remove('fa-eye');
                eyeIcon.classList.add('fa-eye-slash');
            } else {
                eyeIcon.classList.remove('fa-eye-slash');
                eyeIcon.classList.add('fa-eye');
            }
        });
    </script>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDR Investigation Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700;800&display=swap');
        :root { color-scheme:light !important; }
        body { background:linear-gradient(135deg,#f0f7ff 0%,#f8fafc 48%,#f5f3ff 100%) !important; color:#172554 !important; font-family:'Noto Sans Bengali','Hind Siliguri','Segoe UI',sans-serif !important; }
        .hero-header { background:linear-gradient(105deg,#123b82 0%,#075985 48%,#4338ca 100%) !important; border-bottom:3px solid #22d3ee !important; box-shadow:0 10px 28px rgba(30,64,175,.20) !important; padding:22px 0; }
        .header-inner,.brand-area,.header-actions,.profile-pill,.workspace-welcome { display:flex; align-items:center; }
        .header-inner { justify-content:space-between; gap:24px; }
        .brand-area { gap:15px; }
        .brand-mark { width:54px; height:54px; display:grid; place-items:center; position:relative; border-radius:17px; background:linear-gradient(145deg,#2563eb,#06b6d4) !important; color:#fff !important; border:1px solid rgba(255,255,255,.35) !important; font-size:24px; }
        .brand-spark { position:absolute; width:7px; height:7px; border-radius:50%; background:#67e8f9; right:8px; top:8px; box-shadow:0 0 12px #67e8f9; }
        .brand-copy .eyebrow,.section-kicker { color:#dbeafe !important; font-size:.68rem; font-weight:800; letter-spacing:.16em; }
        .status-dot,.chip-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#34d399; box-shadow:0 0 10px rgba(52,211,153,.65); margin-right:7px; }
        .brand-copy h2 { margin:3px 0 1px; font-size:clamp(1.45rem,2.2vw,1.95rem) !important; font-weight:800; color:#fff !important; }
        .brand-copy h2 span { background:linear-gradient(90deg,#fff,#a5f3fc) !important; -webkit-background-clip:text; background-clip:text; color:transparent; }
        .brand-copy p { margin:0; color:#dbeafe !important; font-size:1rem !important; }
        .header-actions { gap:14px; }
        .profile-pill { gap:10px; padding:8px 13px 8px 8px; border:1px solid rgba(255,255,255,.22) !important; border-radius:15px; background:rgba(255,255,255,.12) !important; }
        .profile-avatar { width:39px; height:39px; display:grid; place-items:center; border-radius:12px; background:linear-gradient(145deg,#7464e8,#3e8dbd); font-size:.82rem; font-weight:800; color:white; }
        .profile-copy strong { font-size:.85rem; color:#fff !important; display:block; }
        .profile-copy span { margin-top:2px; font-size:.7rem; color:#dbeafe !important; display:block; }
        .logout-btn { color:#fff !important; text-decoration:none; font-size:.82rem; font-weight:700; padding:11px 14px; border:1px solid #ff8794; border-radius:12px; background:#ef233c !important; box-shadow:0 6px 16px rgba(239,35,60,.28); transition:.2s; }
        .logout-btn:hover { background:#c1122f !important; color:#fff !important; transform:translateY(-1px); }
        .workspace-container { max-width:1500px; padding-top:28px; padding-bottom:30px; }
        .workspace-welcome { justify-content:space-between; gap:20px; margin-bottom:22px; }
        .workspace-welcome h1 { font-size:1.9rem !important; font-weight:800; color:#172554 !important; margin:6px 0 4px; }
        .workspace-welcome p { margin:0; color:#52627a !important; font-size:1rem !important; }
        .workspace-chip { display:flex; align-items:center; padding:10px 14px; border:1px solid #bfdbfe; border-radius:99px; background:#fff !important; color:#1d4ed8 !important; font-size:.75rem; font-weight:700; }
        .card,.chat-box-container { border:1px solid #dbeafe !important; border-radius:18px !important; background:#fff !important; box-shadow:0 10px 28px rgba(37,99,235,.08) !important; }
        .card:hover { transform:translateY(-2px); border-color:#93c5fd !important; }
        .upload-box { padding:35px 20px; background:linear-gradient(135deg,#eff6ff 0%,#f5f3ff 52%,#ecfeff 100%) !important; border:2px dashed #60a5fa !important; border-radius:17px; cursor:pointer; text-align:center; }
        .upload-box:hover { background:linear-gradient(135deg,#dbeafe,#ede9fe,#cffafe) !important; border-color:#4f46e5 !important; }
        .upload-box h5 { color:#172554 !important; font-size:1.15rem !important; }
        .upload-box p { color:#52627a !important; font-size:.98rem !important; }
        .stat-card-blue { background:linear-gradient(135deg,#dbeafe,#eff6ff) !important; border:1px solid #93c5fd !important; border-left:5px solid #2563eb !important; padding:19px !important; border-radius:17px !important; }
        .stat-card-green { background:linear-gradient(135deg,#d1fae5,#ecfdf5) !important; border:1px solid #6ee7b7 !important; border-left:5px solid #059669 !important; padding:19px !important; border-radius:17px !important; }
        .stat-card-yellow { background:linear-gradient(135deg,#fef3c7,#fffbeb) !important; border:1px solid #fcd34d !important; border-left:5px solid #d97706 !important; padding:19px !important; border-radius:17px !important; }
        .stat-card-red { background:linear-gradient(135deg,#ffe4e6,#fff1f2) !important; border:1px solid #fda4af !important; border-left:5px solid #e11d48 !important; padding:19px !important; border-radius:17px !important; }
        .stat-card-blue h3 { color:#1d4ed8 !important; font-size:1.55rem; }
        .stat-card-green h3 { color:#047857 !important; font-size:1.55rem; }
        .stat-card-yellow h3 { color:#b45309 !important; font-size:1.55rem; }
        .stat-card-red h3 { color:#be123c !important; font-size:1.55rem; }
        .chat-box-container { padding:23px !important; }
        .chat-messages { min-height:220px; height:280px; background:linear-gradient(180deg,#f8fafc,#eff6ff) !important; border:1px solid #dbeafe !important; border-radius:15px !important; padding:18px; overflow-y:auto; }
        .chat-bubble { padding:13px 16px; border-radius:15px; line-height:1.65; max-width:84%; margin-bottom:12px; }
        .chat-ai { background:#e0f2fe !important; color:#164e63 !important; border:1px solid #bae6fd !important; }
        .chat-user { background:linear-gradient(120deg,#4f46e5,#7c3aed) !important; color:#fff !important; margin-left:auto; text-align:right; }
        .table-custom th { background:linear-gradient(90deg,#1d4ed8,#4338ca) !important; color:#fff !important; border-color:#c7d2fe !important; padding: 12px; font-size: 0.85rem; }
        .table-custom td { color:#24334f !important; border-color:#e2e8f0 !important; padding: 12px; font-size: 0.95rem; }
        .table-custom tr:hover td { background:#eff6ff !important; }
        .form-control,.form-select { background:#fff !important; color:#172554 !important; border:1px solid #cbd5e1 !important; min-height:48px !important; border-radius:10px !important; font-size:1rem !important; }
        .form-label { color:#24334f !important; font-weight:700 !important; }
        .btn-primary { background:linear-gradient(110deg,#2563eb,#7c3aed) !important; border:0 !important; color:#fff !important; }
        .btn-outline-secondary { background:#fff !important; color:#334155 !important; border-color:#cbd5e1 !important; }
        .app-footer { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-top:12px; padding:19px 4px 8px; border-top:1px solid #dbeafe; color:#64748b; font-size:.76rem; }
        .app-footer strong { color:#1d4ed8; font-weight:700; }
        .location-text { color:#334155 !important; font-size: 0.88rem; }
        @media (max-width:768px) { .header-inner,.workspace-welcome { align-items:flex-start; flex-direction:column; } .header-actions { width:100%; justify-content:space-between; } }
    </style>
</head>
<body>
    <header class="hero-header">
        <div class="container header-inner">
            <div class="brand-area">
                <div class="brand-mark"><i class="fa-solid fa-brain"></i><span class="brand-spark"></span></div>
                <div class="brand-copy">
                    <div class="eyebrow"><span class="status-dot"></span> PRIVATE ANALYSIS WORKSPACE</div>
                    <h2>CDR <span>Intelligence</span></h2>
                    <p>Call detail record analysis · Investigation workspace</p>
                </div>
            </div>
            <div class="header-actions">
                <div class="profile-pill">
                    <div class="profile-avatar">NH</div>
                    <div class="profile-copy"><strong>নুর হোসেন</strong><span>বাংলাদেশ পুলিশ সদস্য</span></div>
                </div>
                <a href="/logout" class="logout-btn"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i>লগআউট</a>
            </div>
        </div>
    </header>

    <div class="container workspace-container">
        <div class="workspace-welcome">
            <div><span class="section-kicker">WORKSPACE OVERVIEW</span><h1>বিশ্লেষণ ড্যাশবোর্ড</h1><p>CDR ফাইল আপলোড করুন, রেকর্ড বিশ্লেষণ করুন এবং প্রাসঙ্গিক তথ্য খুঁজুন।</p></div>
            <div class="workspace-chip"><i class="fa-solid fa-lock me-2"></i>লোকাল সেশন <span class="chip-dot"></span></div>
        </div>

        <!-- Upload Box -->
        <div class="card p-4 mb-4 shadow-sm">
            <div class="upload-box" onclick="document.getElementById('fileInput').click()">
                <div class="mb-2">
                    <i class="fa-solid fa-cloud-arrow-up fa-3x" style="color: #4f46e5;"></i>
                </div>
                <h5 class="fw-bold text-dark mb-1">CDR এক্সেল / সিএসভি ফাইল আপলোড করুন</h5>
                <p class="text-muted small mb-3">ক্লিক করে আপনার ফরেনসিক CDR ফাইল (.xlsx / .xls / .csv) নির্বাচন করুন</p>
                <input type="file" id="fileInput" accept=".xlsx, .xls, .csv" style="display:none;" onchange="uploadFile()">
                <button class="btn btn-primary px-4 rounded-pill fw-bold shadow-sm"><i class="fa-solid fa-upload me-1"></i> ফাইল সিলেক্ট করুন</button>
            </div>
            <div id="loading" class="text-center mt-3" style="display:none;">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-primary fw-bold">ফাইল নিখুঁতভাবে প্রসেস করা হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...</p>
            </div>
        </div>

        <!-- Dashboard Result -->
        <div id="resultArea" style="display:none;">
            <!-- Key Metrics -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card p-3 stat-card-blue">
                        <small class="text-muted fw-bold text-uppercase" style="font-size: 0.75rem;">মোট ভয়েস কল</small>
                        <h3 id="statTotalCalls" class="fw-bold mb-0 mt-1">0</h3>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card-green">
                        <small class="text-muted fw-bold text-uppercase" style="font-size: 0.75rem;">মোট কথা বলার সময়</small>
                        <h3 id="statTotalDuration" class="fw-bold mb-0 mt-1">0 মি.</h3>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card-yellow">
                        <small class="text-muted fw-bold text-uppercase" style="font-size: 0.75rem;">IMSI / IMEI তথ্য</small>
                        <h6 id="statImsi" class="text-dark fw-bold mb-0 mt-1" style="font-size: 0.78rem; word-break: break-all;">-</h6>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card-red">
                        <small class="text-muted fw-bold text-uppercase" style="font-size: 0.75rem;">নাইট কল (০০:০০ - ০৬:০০)</small>
                        <h3 id="statNightCalls" class="fw-bold mb-0 mt-1">0</h3>
                    </div>
                </div>
            </div>

            <!-- AI Investigation Chat Assistant -->
            <div class="chat-box-container mb-4 p-4">
                <h5 class="fw-bold text-dark mb-3"><i class="fa-solid fa-robot text-indigo me-2" style="color: #4f46e5;"></i>CDR AI ইনভেস্টিগেশন অ্যাসিস্ট্যান্ট</h5>
                <div class="chat-messages rounded-3 mb-3" id="chatMessages">
                    <div class="chat-bubble chat-ai">হ্যালো! আমি আপনার CDR ইনভেস্টিগেশন অ্যাসিস্ট্যান্ট। ফাইল আপলোড করার পর আমাকে যেকোনো প্রশ্ন করুন।</div>
                </div>
                <div class="input-group">
                    <input type="text" id="chatInput" class="form-control rounded-start-pill px-4" placeholder="এখানে বাংলায় প্রশ্ন লিখুন যেমন: রাতে কার সাথে কথা হয়েছে?..." onkeypress="if(event.key === 'Enter') sendChatQuery()">
                    <button class="btn btn-primary px-4 rounded-end-pill fw-bold" onclick="sendChatQuery()"><i class="fa-solid fa-paper-plane me-1"></i> পাঠান</button>
                </div>
            </div>

            <!-- Custom Time Search & Filter Bar -->
            <div class="card p-4 mb-4 bg-white border">
                <h6 class="fw-bold text-dark mb-2"><i class="fa-solid fa-clock-rotate-left me-2" style="color: #4f46e5;"></i>নির্দিষ্ট সময় বা সেকেন্ড দিয়ে কল খুঁজুন (Custom Time Filter)</h6>
                <div class="row g-2 mt-1">
                    <div class="col-md-4">
                        <input type="text" id="timeSearchInput" class="form-control rounded-pill px-3" placeholder="সময় লিখুন যেমন: 14:01:45 বা 02:00">
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-primary w-100 rounded-pill fw-bold shadow-sm" onclick="filterByTime()"><i class="fa-solid fa-search me-1"></i> সার্চ করুন</button>
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-outline-secondary w-100 rounded-pill fw-bold" onclick="resetTimeFilter()">রিসেট</button>
                    </div>
                </div>
            </div>

            <!-- Top Contacts & Location Analysis -->
            <div class="row g-4 mb-4">
                <div class="col-md-4">
                    <div class="card p-4 h-100">
                        <h5 class="fw-bold text-dark mb-3" style="font-size: 1.05rem;"><i class="fa-solid fa-address-book text-primary me-2"></i>সবচেয়ে বেশিবার যোগাযোগ</h5>
                        <ul class="list-group list-group-flush" id="topCountList"></ul>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card p-4 h-100">
                        <h5 class="fw-bold text-dark mb-3" style="font-size: 1.05rem;"><i class="fa-solid fa-stopwatch text-success me-2"></i>সবচেয়ে দীর্ঘ সময় কথা</h5>
                        <ul class="list-group list-group-flush" id="topDurationList"></ul>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card p-4 h-100">
                        <h5 class="fw-bold text-dark mb-3" style="font-size: 1.05rem;"><i class="fa-solid fa-location-dot text-danger me-2"></i>সবচেয়ে বেশি ব্যবহৃত লোকেশন</h5>
                        <ul class="list-group list-group-flush" id="topLocationList"></ul>
                    </div>
                </div>
            </div>

            <!-- All Calls Table -->
            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-dark mb-3"><i class="fa-solid fa-list-ul me-2" style="color: #4f46e5;"></i>কল রেকর্ড তালিকা ও গুগল ম্যাপ লিংক (<span id="tableTitleCount">সকল কল</span>)</h5>
                <div class="table-responsive rounded-3 border" style="max-height: 480px;">
                    <table class="table table-hover align-middle table-custom mb-0">
                        <thead>
                            <tr>
                                <th style="width: 15%;">মোবাইল নম্বর</th>
                                <th style="width: 15%;">তারিখ ও সময়</th>
                                <th style="width: 12%;">কথা বলার সময়</th>
                                <th style="width: 30%;">ঠিকানা (যদি থাকে)</th>
                                <th style="width: 18%;">LAC / Cell ID</th>
                                <th style="width: 12%;">ম্যাপ</th>
                            </tr>
                        </thead>
                        <tbody id="callsTable"></tbody>
                    </table>
                </div>
            </div>

            <!-- Night Calls Detail Table -->
            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-danger mb-4"><i class="fa-solid fa-moon me-2"></i>রাতের বেলার কল (০০:০০ - ০৬:০০) ও গুগল ম্যাপ লিংক</h5>
                <div class="table-responsive rounded-3 border" style="max-height: 420px;">
                    <table class="table table-hover align-middle table-custom mb-0">
                        <thead>
                            <tr>
                                <th style="width: 15%; background-color: #991b1b !important; color:#fff !important;">মোবাইল নম্বর</th>
                                <th style="width: 15%; background-color: #991b1b !important; color:#fff !important;">তারিখ ও সময়</th>
                                <th style="width: 12%; background-color: #991b1b !important; color:#fff !important;">কথা বলার সময়</th>
                                <th style="width: 30%; background-color: #991b1b !important; color:#fff !important;">ঠিকানা (যদি থাকে)</th>
                                <th style="width: 18%; background-color: #991b1b !important; color:#fff !important;">LAC / Cell ID</th>
                                <th style="width: 12%; background-color: #991b1b !important; color:#fff !important;">ম্যাপ</th>
                            </tr>
                        </thead>
                        <tbody id="nightCallsTable"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <footer class="app-footer">
            <div><strong>CDR Intelligence</strong> <span class="ms-2">ব্যক্তিগত বিশ্লেষণ কর্ম-সহায়ক ড্যাশবোর্ড</span></div>
            <div class="footer-contact"><i class="fa-regular fa-user me-2"></i>নুর হোসেন · বাংলাদেশ পুলিশ সদস্য <span class="mx-2">|</span><i class="fa-solid fa-phone me-1"></i>{{CONTACT_NUMBER}}</div>
        </footer>
    </div>

    <script>
        let globalData = null;
        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, ch => ({
                '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
            }[ch]));
        }

        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            if(!fileInput.files.length) return;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            document.getElementById('loading').style.display = 'block';
            document.getElementById('resultArea').style.display = 'none';

            try {
                const response = await fetch('/analyze-cdr', { method: 'POST', body: formData });
                const data = await response.json();
                document.getElementById('loading').style.display = 'none';

                if(response.status === 401) {
                    window.location.href = "/";
                    return;
                }

                if(response.ok) {
                    globalData = data;
                    const chatMessages = document.getElementById('chatMessages');
                    chatMessages.innerHTML = `<div class="chat-bubble chat-ai">নতুন CDR ফাইল সফলভাবে প্রসেস করা হয়েছে! এখন এই ফাইলের ডেটা সম্পর্কে আমাকে যেকোনো প্রশ্ন করতে পারেন।</div>`;
                    renderDashboard(data);
                } else {
                    alert("ভুল হয়েছে: " + (data.detail || "ফাইল প্রসেস করা যায়নি"));
                }
            } catch(err) {
                document.getElementById('loading').style.display = 'none';
                alert("সার্ভারে সমস্যা হয়েছে!");
            }
        }

        function renderDashboard(data) {
            document.getElementById('resultArea').style.display = 'block';
            document.getElementById('statTotalCalls').innerText = data.total_calls;
            document.getElementById('statTotalDuration').innerText = data.total_duration_formatted;
            
            let imsiText = "";
            if(data.primary_imsi) imsiText += "IMSI: " + data.primary_imsi;
            if(data.primary_imei) imsiText += (imsiText ? "<br>" : "") + "IMEI: " + data.primary_imei;
            document.getElementById('statImsi').innerHTML = imsiText || "IMSI/IMEI পাওয়া যায়নি";

            document.getElementById('statNightCalls').innerText = data.night_calls_count;

            const countList = document.getElementById('topCountList');
            countList.innerHTML = '';
            if(!data.top_by_count || data.top_by_count.length === 0) {
                countList.innerHTML = '<li class="list-group-item text-muted">কোনো ডাটা নেই</li>';
            } else {
                data.top_by_count.forEach((item, index) => {
                    countList.innerHTML += `<li class="list-group-item d-flex justify-content-between align-items-center py-2">
                        <span><strong>#${index+1}</strong> ${escapeHtml(item.number)}</span>
                        <span class="badge bg-primary rounded-pill px-2 py-1">${escapeHtml(item.count)} কল</span>
                    </li>`;
                });
            }

            const durList = document.getElementById('topDurationList');
            durList.innerHTML = '';
            if(!data.top_by_duration || data.top_by_duration.length === 0) {
                durList.innerHTML = '<li class="list-group-item text-muted">কোনো ডাটা নেই</li>';
            } else {
                data.top_by_duration.forEach((item, index) => {
                    durList.innerHTML += `<li class="list-group-item d-flex justify-content-between align-items-center py-2">
                        <span><strong>#${index+1}</strong> ${escapeHtml(item.number)}</span>
                        <span class="badge bg-success rounded-pill px-2 py-1">${escapeHtml(item.duration)}</span>
                    </li>`;
                });
            }

            const locList = document.getElementById('topLocationList');
            locList.innerHTML = '';
            if(!data.top_locations || data.top_locations.length === 0) {
                locList.innerHTML = '<li class="list-group-item text-muted">লোকেশন ডাটা পাওয়া যায়নি</li>';
            } else {
                data.top_locations.forEach((item, index) => {
                    const mapBtn = item.map_url ? `<a href="${item.map_url}" target="_blank" class="btn btn-sm btn-outline-danger ms-2 rounded-pill px-2 py-0" title="ম্যাপে দেখুন"><i class="fa-solid fa-map-location-dot"></i></a>` : '';
                    locList.innerHTML += `<li class="list-group-item d-flex justify-content-between align-items-start py-2">
                        <div class="me-auto" style="font-size: 0.85rem; word-break: break-word;"><strong>#${index+1}</strong> ${escapeHtml(item.location)}</div>
                        <div class="d-flex align-items-center ms-2">
                            <span class="badge bg-secondary rounded-pill me-1">${escapeHtml(item.count)}</span>
                            ${mapBtn}
                        </div>
                    </li>`;
                });
            }

            fillTable('callsTable', data.all_calls_details);
            fillTable('nightCallsTable', data.night_calls_details);
        }

        function fillTable(tableId, records) {
            const tbody = document.getElementById(tableId);
            tbody.innerHTML = '';
            if(!records || records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">কোনো ডাটা পাওয়া যায়নি</td></tr>';
                return;
            }
            records.forEach(item => {
                const mapBtn = item.Map_URL ? `<a href="${escapeHtml(item.Map_URL)}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-danger rounded-pill px-3 shadow-sm"><i class="fa-solid fa-map-location-dot me-1"></i>ম্যাপ</a>` : '-';
                tbody.innerHTML += `<tr>
                    <td><strong>${escapeHtml(item.B_Party || '-')}</strong></td>
                    <td><span class="fw-semibold text-dark">${escapeHtml(item.Call_Date || '')}</span><br><small class="text-muted"><i class="fa-regular fa-clock me-1"></i>${escapeHtml(item.Call_Time || '')}</small></td>
                    <td><span class="badge bg-success bg-opacity-10 text-success border border-success px-2 py-1">${escapeHtml(item.Duration_Formatted || '0 সে.')}</span></td>
                    <td><div class="location-text">${escapeHtml(item.Location || 'ঠিকানা পাওয়া যায়নি')}</div></td>
                    <td>${escapeHtml(item.Cell_Reference || '-')}</td>
                    <td>${mapBtn}</td>
                </tr>`;
            });
        }

        function filterByTime() {
            if(!globalData) return;
            const query = document.getElementById('timeSearchInput').value.trim().toLowerCase();
            if(!query) {
                fillTable('callsTable', globalData.all_calls_details);
                document.getElementById('tableTitleCount').innerText = "সকল কল";
                return;
            }

            const filtered = globalData.all_calls_details.filter(item => {
                return (item.Call_Time && item.Call_Time.toLowerCase().includes(query)) || 
                       (item.Call_Date && item.Call_Date.toLowerCase().includes(query)) ||
                       (item.B_Party && item.B_Party.toLowerCase().includes(query));
            });

            fillTable('callsTable', filtered);
            document.getElementById('tableTitleCount').innerText = `ফিল্টার করা ফলাফল (${filtered.length}টি)`;
        }

        function resetTimeFilter() {
            document.getElementById('timeSearchInput').value = '';
            if(globalData) {
                fillTable('callsTable', globalData.all_calls_details);
                document.getElementById('tableTitleCount').innerText = "সকল কল";
            }
        }

        function sendChatQuery() {
            const input = document.getElementById('chatInput');
            const query = input.value.trim();
            if(!query) return;

            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML += `<div class="chat-bubble chat-user shadow-sm">${escapeHtml(query)}</div>`;
            input.value = '';
            chatMessages.scrollTop = chatMessages.scrollHeight;

            if(!globalData) {
                setTimeout(() => {
                    chatMessages.innerHTML += `<div class="chat-bubble chat-ai shadow-sm">দয়া করে প্রথমে একটি CDR এক্সেল ফাইল আপলোড করুন।</div>`;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 500);
                return;
            }

            let aiReply = "দুঃখিত, আপনার প্রশ্নটি বুঝতে পারিনি। নির্দিষ্ট কোনো মোবাইল নম্বর, সময় বা 'রাত' লিখে সার্চ করতে পারেন।";
            const qLower = query.toLowerCase();

            if(qLower.includes('রাত') || qLower.includes('night')) {
                aiReply = `ফাইলে মোট ${globalData.night_calls_count}টি নাইট কল (রাত ১২টা থেকে সকাল ৬টা) পাওয়া গেছে।`;
            } else if(qLower.includes('বেশি') || qLower.includes('most') || qLower.includes('top')) {
                if(globalData.top_by_count.length > 0) {
                    let topNum = globalData.top_by_count[0].number;
                    let topCnt = globalData.top_by_count[0].count;
                    aiReply = `সবচেয়ে বেশিবার যোগাযোগ করা হয়েছে ${topNum} নম্বরের সাথে (মোট ${topCnt} বার)।`;
                }
            } else if(qLower.includes('মোট') || qLower.includes('total')) {
                aiReply = `এই CDR ফাইলে মোট ${globalData.total_calls}টি ভয়েস কল এবং মোট কথা বলার সময় ${globalData.total_duration_formatted}।`;
            } else {
                const matches = globalData.all_calls_details.filter(item => 
                    (item.B_Party && item.B_Party.includes(query)) || 
                    (item.Call_Time && item.Call_Time.includes(query)) ||
                    (item.Call_Date && item.Call_Date.includes(query))
                );
                if(matches.length > 0) {
                    aiReply = `"${escapeHtml(query)}" এর সাথে মিলে যায় এমন ${matches.length}টি কল রেকর্ড পাওয়া গেছে। প্রথম রেকর্ডটি: নম্বর ${matches[0].B_Party}, তারিখ: ${matches[0].Call_Date}, সময়: ${matches[0].Call_Time}, লোকেশন: ${matches[0].Location}`;
                } else {
                    aiReply = `"${escapeHtml(query)}" সম্পর্কিত কোনো তথ্য ফাইলে পাওয়া যায়নি।`;
                }
            }

            setTimeout(() => {
                chatMessages.innerHTML += `<div class="chat-bubble chat-ai shadow-sm">${escapeHtml(aiReply)}</div>`;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 500);
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home_dashboard(session: str = Cookie(default=None, alias=SESSION_COOKIE)):
    if valid_session(session):
        return HTML_TEMPLATE.replace("{{CONTACT_NUMBER}}", CONTACT_NUMBER)
    return LOGIN_HTML


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if secrets.compare_digest(username, ADMIN_USER) and secrets.compare_digest(password, ADMIN_PASS):
        response = RedirectResponse(url="/", status_code=303)
        token = SESSION_SERIALIZER.dumps({"authenticated": True})
        response.set_cookie(
            key=SESSION_COOKIE, value=token, max_age=8 * 60 * 60,
            httponly=True, secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            samesite="lax", path="/"
        )
        return response
    return HTMLResponse(
        content="<script>alert('ভুল ইউজারনেম অথবা পাসওয়ার্ড!'); window.location.href='/';</script>",
        status_code=401
    )


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return response


@app.post("/analyze-cdr")
async def analyze_cdr(file: UploadFile = File(...), session: str = Cookie(default=None, alias=SESSION_COOKIE)):
    if not valid_session(session):
        raise HTTPException(status_code=401, detail="সেশন শেষ হয়েছে। আবার লগইন করুন।")
    filename = file.filename or ""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="শুধু .xlsx, .xls অথবা .csv ফাইল আপলোড করুন।")
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"ফাইলের সর্বোচ্চ সাইজ {MAX_UPLOAD_BYTES // (1024 * 1024)} MB।")
    if not contents:
        raise HTTPException(status_code=400, detail="ফাইলটি খালি।")
    try:
        result = process_cdr(contents, filename)
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        # Keep detailed exception traces out of responses because CDR may contain sensitive data.
        import logging
        logging.exception("CDR processing error")
        raise HTTPException(status_code=500, detail="ফাইল প্রসেস করতে সমস্যা হয়েছে। কলাম ও ফাইল ফরম্যাট পরীক্ষা করুন।")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
