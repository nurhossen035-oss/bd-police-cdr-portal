import pandas as pd

def process_cdr_dates(df, dt_col=None, date_col=None, time_col=None):
    # প্রথমে ডেট কলামের ফাঁকা বা জিরো ভ্যালুগুলোকে পরিষ্কার করা
    if dt_col and dt_col in df.columns:
        # যদি নিউমেরিক বা এক্সেল সিরিয়াল হয়
        if pd.api.types.is_numeric_dtype(df[dt_col]):
            # ০ বা নেগেটিভ মানগুলোকে NaT এ রূপান্তর করা
            df.loc[df[dt_col] <= 0, dt_col] = pd.NA
            df['Full_DateTime'] = pd.to_datetime(df[dt_col], unit='s', origin='1899-12-30', errors='coerce')
        else:
            dt_series = df[dt_col].astype(str).str.replace(r'\.0$', '', regex=True)
            dt_series = dt_series.replace(['0', '0.0', 'nan', 'NaT', 'None', ''], pd.NA)
            df['Full_DateTime'] = pd.to_datetime(dt_series, errors='coerce', dayfirst=True, format='mixed')

    # যদি আলাদা ডেট এবং টাইম কলাম থাকে
    elif date_col and date_col in df.columns:
        date_series = df[date_col].astype(str).str.replace(r'\.0$', '', regex=True)
        date_series = date_series.replace(['0', '0.0', 'nan', 'NaT', 'None', ''], pd.NA)
        
        if time_col and time_col in df.columns:
            time_series = df[time_col].astype(str).str.replace(r'\.0$', '', regex=True).fillna('00:00:00')
            combined_series = date_series + ' ' + time_series
            df['Full_DateTime'] = pd.to_datetime(combined_series, errors='coerce', dayfirst=True, format='mixed')
        else:
            df['Full_DateTime'] = pd.to_datetime(date_series, errors='coerce', dayfirst=True, format='mixed')

    # সিডিআর ডেটা সর্বোচ্চ ২ বছরের (২০২৪ থেকে ২০২৬) মধ্যে সীমাবদ্ধ রাখার লজিক
    # এর বাইরের কোনো পুরোনো তারিখ (যেমন ১৯৭০ বা ১৮৯৯) থাকলে তা স্বয়ংক্রিয়ভাবে মুছে (NaT) যাবে
    if 'Full_DateTime' in df.columns:
        df['Full_DateTime'] = pd.to_datetime(df['Full_DateTime'], errors='coerce')
        
        # বর্তমান বছর ২০২৬ হলে, ২০২৪ এর আগের বা ভবিষ্যতের তারিখগুলো ফিল্টার করা
        valid_mask = (df['Full_DateTime'].dt.year >= 2024) & (df['Full_DateTime'].dt.year <= 2026)
        df.loc[~valid_mask, 'Full_DateTime'] = pd.NaT

    return df
