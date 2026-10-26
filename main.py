import os
import re
import tempfile
import numbers
from datetime import datetime

import pandas as pd
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MIN_VALID_YEAR = 2000
MAX_VALID_YEAR = 2100


def normalize_column_name(value):
    """Normalize column labels so BOM, spaces, underscores and case don't break matching."""
    value = str(value).replace("\ufeff", "").strip().lower()
    return re.sub(r"[^a-z0-9]", "", value)


def find_column(columns, candidates):
    """Find a column by normalized exact name, then by a cautious partial match."""
    normalized = {normalize_column_name(col): col for col in columns}
    for candidate in candidates:
        key = normalize_column_name(candidate)
        if key in normalized:
            return normalized[key]

    # Partial matching is only a fallback; exact matches are preferred.
    for candidate in candidates:
        key = normalize_column_name(candidate)
        if len(key) >= 4:
            for normalized_name, original_name in normalized.items():
                if key in normalized_name:
                    return original_name
    return None


def read_cdr_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        last_error = None
        # utf-8-sig handles CSV files that begin with a UTF-8 BOM.
        for encoding in ("utf-8-sig", "cp1252", "latin1"):
            try:
                return pd.read_csv(
                    file_path,
                    encoding=encoding,
                    low_memory=False,
                    sep=None,
                    engine="python",
                )
            except (UnicodeDecodeError, pd.errors.ParserError) as exc:
                last_error = exc
        raise ValueError(f"CSV ফাইল পড়া যায়নি: {last_error}")

    if ext in {".xlsx", ".xls"}:
        # pandas selects the first worksheet; .xls may require xlrd to be installed.
        return pd.read_excel(file_path, sheet_name=0)

    raise ValueError("অসমর্থিত ফাইল ফরম্যাট। CSV, XLSX অথবা XLS ফাইল দিন।")


def parse_datetime_value(value):
    """Parse a single CDR date/time value without interpreting YYYYMMDDHHMMSS as epoch."""
    if pd.isna(value):
        return pd.NaT

    # Preserve actual datetime objects from Excel.
    if isinstance(value, (pd.Timestamp, datetime)):
        result = pd.to_datetime(value, errors="coerce")
        if pd.isna(result) or not (MIN_VALID_YEAR <= result.year <= MAX_VALID_YEAR):
            return pd.NaT
        return result

    # Numeric values can be 14-digit CDR timestamps or Excel serial dates.
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        if pd.isna(value):
            return pd.NaT
        number = float(value)

        if number <= 0:
            return pd.NaT

        # YYYYMMDDHHMMSS, sometimes stored as a number in Excel.
        digits = str(int(number)) if number.is_integer() else ""
        if len(digits) == 14:
            result = pd.to_datetime(digits, format="%Y%m%d%H%M%S", errors="coerce")
            if not pd.isna(result) and MIN_VALID_YEAR <= result.year <= MAX_VALID_YEAR:
                return result
            return pd.NaT

        # Excel date serials are normally around 20,000–80,000 for modern dates.
        if number.is_integer() and 20000 <= number <= 80000:
            result = pd.to_datetime(number, unit="D", origin="1899-12-30", errors="coerce")
            if not pd.isna(result) and MIN_VALID_YEAR <= result.year <= MAX_VALID_YEAR:
                return result
            return pd.NaT

        return pd.NaT

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none", "null", "0", "0.0"}:
        return pd.NaT

    text = re.sub(r"\.0$", "", text)

    # Explicit 14-digit timestamp, e.g. 20260901204241.
    if re.fullmatch(r"\d{14}", text):
        result = pd.to_datetime(text, format="%Y%m%d%H%M%S", errors="coerce")
    # Explicit YYYYMMDD date.
    elif re.fullmatch(r"\d{8}", text):
        result = pd.to_datetime(text, format="%Y%m%d", errors="coerce")
    else:
        # Handles formats such as 23/03/2026 18:12:31 and Excel-exported date strings.
        try:
            result = pd.to_datetime(text, errors="coerce", dayfirst=True, format="mixed")
        except (TypeError, ValueError):
            # Compatibility fallback for older pandas versions.
            result = pd.to_datetime(text, errors="coerce", dayfirst=True)

    if pd.isna(result) or not (MIN_VALID_YEAR <= result.year <= MAX_VALID_YEAR):
        return pd.NaT
    return result


def parse_datetime_series(series):
    return pd.to_datetime(series.map(parse_datetime_value), errors="coerce")


def parse_date_and_time(date_series, time_series=None):
    dates = date_series.map(parse_datetime_value)

    if time_series is None:
        return pd.to_datetime(dates, errors="coerce")

    def time_to_text(value):
        if pd.isna(value):
            return "00:00:00"
        text = str(value).strip()
        if not text or text.lower() in {"nan", "nat", "none", "null"}:
            return "00:00:00"
        # Numeric time fractions exported from Excel, e.g. 0.5 = 12:00.
        try:
            number = float(text)
            if 0 <= number < 1 and re.fullmatch(r"\d+(?:\.\d+)?", text):
                seconds = round(number * 24 * 60 * 60)
                hours, remainder = divmod(seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours % 24:02d}:{minutes:02d}:{seconds:02d}"
        except ValueError:
            pass
        return text

    combined = []
    for parsed_date, raw_time in zip(dates, time_series):
        if pd.isna(parsed_date):
            combined.append(pd.NaT)
            continue

        time_text = time_to_text(raw_time)
        # If date column already contains a time, don't append a second time.
        if parsed_date.hour or parsed_date.minute or parsed_date.second:
            combined.append(parsed_date)
            continue

        candidate = pd.to_datetime(
            f"{parsed_date.strftime('%Y-%m-%d')} {time_text}",
            errors="coerce",
        )
        if pd.isna(candidate):
            candidate = parsed_date
        combined.append(candidate)

    return pd.to_datetime(combined, errors="coerce")


def load_and_process_cdr(file_path):
    df = read_cdr_file(file_path)

    if df is None or df.empty:
        raise ValueError("ফাইলে কোনো ডেটা পাওয়া যায়নি।")

    # Remove BOM and surrounding spaces from column labels, while preserving original names otherwise.
    df.columns = [str(col).replace("\ufeff", "").strip() for col in df.columns]

    dt_candidates = [
        "START_DTTIME", "START_DATETIME", "START_DATE_TIME", "START",
        "START_TIME", "Start_DateTime", "CALL_START_TIME", "CALL_DATETIME",
        "DATETIME", "DATE_TIME", "EVENT_TIME", "STARTTIME",
    ]
    date_candidates = ["CALL_DATE", "DATE", "START_DATE", "EVENT_DATE", "TRANSACTION_DATE"]
    time_candidates = ["CALL_TIME", "TIME", "START_CLOCK", "EVENT_CLOCK"]

    found_dt_col = find_column(df.columns, dt_candidates)
    found_date_col = find_column(df.columns, date_candidates)
    found_time_col = find_column(df.columns, time_candidates)

    # A START_TIME column may contain a full date and time (common in some operator exports).
    # Prefer it as the datetime field when no stronger datetime column was found.
    if found_dt_col is None:
        found_dt_col = find_column(df.columns, ["START_TIME", "STARTTIME", "CALL_START_TIME"])

    df["Full_DateTime"] = pd.NaT

    if found_dt_col is not None:
        df["Full_DateTime"] = parse_datetime_series(df[found_dt_col])
    elif found_date_col is not None:
        df["Full_DateTime"] = parse_date_and_time(
            df[found_date_col],
            df[found_time_col] if found_time_col is not None else None,
        )
    else:
        available = ", ".join(map(str, df.columns[:25]))
        raise ValueError(
            "তারিখ/সময় কলাম শনাক্ত করা যায়নি। "
            f"ফাইলের কলামগুলো: {available}"
        )

    # Invalid/implausible dates become NaT, never 1970.
    years = df["Full_DateTime"].dt.year
    valid_mask = years.between(MIN_VALID_YEAR, MAX_VALID_YEAR)
    df.loc[~valid_mask, "Full_DateTime"] = pd.NaT

    # Convenient, consistent display fields for downstream templates/API responses.
    df["Call_Date"] = df["Full_DateTime"].dt.strftime("%Y-%m-%d").fillna("N/A")
    df["Call_Time"] = df["Full_DateTime"].dt.strftime("%H:%M:%S").fillna("N/A")

    return df


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "কোনো ফাইল পাওয়া যায়নি।"}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"success": False, "error": "ফাইল নির্বাচন করা হয়নি।"}), 400

    safe_name = secure_filename(uploaded_file.filename)
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": "শুধু CSV, XLSX অথবা XLS ফাইল আপলোড করা যাবে।",
        }), 400

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_path = temp_file.name
            uploaded_file.save(temp_path)

        processed_df = load_and_process_cdr(temp_path)
        valid_count = int(processed_df["Full_DateTime"].notna().sum())
        invalid_count = int(processed_df["Full_DateTime"].isna().sum())

        return jsonify({
            "success": True,
            "message": "ফাইল সফলভাবে পড়া ও প্রসেস করা হয়েছে।",
            "filename": safe_name,
            "total_rows": int(len(processed_df)),
            "valid_datetime_rows": valid_count,
            "invalid_datetime_rows": invalid_count,
            "detected_date_range": {
                "start": (
                    processed_df["Full_DateTime"].min().strftime("%Y-%m-%d %H:%M:%S")
                    if valid_count else None
                ),
                "end": (
                    processed_df["Full_DateTime"].max().strftime("%Y-%m-%d %H:%M:%S")
                    if valid_count else None
                ),
            },
        }), 200

    except Exception as exc:
        app.logger.exception("CDR upload failed")
        return jsonify({"success": False, "error": str(exc)}), 400
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                app.logger.warning("Temporary upload could not be deleted: %s", temp_path)


if __name__ == "__main__":
    # For local testing only; use a production WSGI server for deployment.
    app.run(debug=False)
