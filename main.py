import os
import pandas as pd
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

def load_and_process_cdr(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()
    df = None
    
    # ১. ফাইল নিরাপদে রিড করা (কোনো অতিরিক্ত errors প্যারামিটার ছাড়া)
    try:
        if file_ext == '.csv':
            for encoding in ['utf-8', 'latin1', 'cp1252']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                df = pd.read_csv(file_path, encoding='latin1', low_memory=False)
                
        elif file_ext in ['.xlsx', '.xls']:
            xls = pd.ExcelFile(file_path)
            # প্রথম শিট রিড করা
            df = pd.read_excel(file_path, sheet_name=xls.sheet_names[0])
        else:
            raise ValueError("অসমর্থিত ফাইল ফরম্যাট!")
    except Exception as e:
        raise Exception(f"ফাইল পড়তে সমস্যা হয়েছে: {str(e)}")

    # কলামের নামগুলোর স্পেস ট্রিম করা
    df.columns = [str(col).strip() for col in df.columns]

    # ২. সব অপারেটরের ভিন্ন ভিন্ন ডেট কলামের নামগুলোর লিস্ট
    dt_candidates = ['START_DTTIME', 'START', 'START_TIME', 'Start', 'start_time', 'Start_DateTime', 'CALL_START_TIME']
    date_candidates = ['DATE', 'CALL_DATE', 'Date', 'date']
    time_candidates = ['TIME', 'CALL_TIME', 'Time', 'time']

    found_dt_col = next((col for col in dt_candidates if col in df.columns), None)
    found_date_col = next((col for col in date_candidates if col in df.columns), None)
    found_time_col = next((col for col in time_candidates if col in df.columns), None)

    df['Full_DateTime'] = pd.NaT

    # ৩. নিখুঁত ডেট ও টাইম পার্সিং (১৯৭০ এ যাওয়া রোধ করতে)
    if found_dt_col:
        raw_series = df[found_dt_col]
        
        # যদি সংখ্যা বা এক্সেল সিরিয়াল হয়
        if pd.api.types.is_numeric_dtype(raw_series):
            df.loc[raw_series <= 0, found_dt_col] = pd.NA
            df['Full_DateTime'] = pd.to_datetime(raw_series, unit='D', origin='1899-12-30', errors='coerce')
        else:
            # স্ট্রিং ফরম্যাট (যেমন: YYYYMMDDHHMMSS বা সাধারণ ডেট স্ট্রিং) পরিষ্কার করা
            dt_series = raw_series.astype(str).str.replace(r'\.0$', '', regex=True)
            dt_series = dt_series.replace(['0', '0.0', 'nan', 'NaT', 'None', ''], pd.NA)
            
            # গ্রামীণফোন বা অন্যান্য অপারেটরের ১৪ ডিজিটের স্ট্রিং (যেমন: 20260901204241) সরাসরি পার্স করার চেষ্টা
            parsed_dates = pd.to_datetime(dt_series, format='%Y%m%d%H%M%S', errors='coerce')
            
            # যদি স্ট্যান্ডার্ড ফরম্যাটে কাজ না করে, তবে জেনারেল মিক্সড ফরম্যাট ট্রাই করা
            if parsed_dates.isna().all():
                parsed_dates = pd.to_datetime(dt_series, errors='coerce', dayfirst=True, format='mixed')
                
            df['Full_DateTime'] = parsed_dates

    elif found_date_col:
        date_series = df[found_date_col].astype(str).str.replace(r'\.0$', '', regex=True)
        date_series = date_series.replace(['0', '0.0', 'nan', 'NaT', 'None', ''], pd.NA)
        
        if found_time_col:
            time_series = df[found_time_col].astype(str).str.replace(r'\.0$', '', regex=True).fillna('00:00:00')
            combined_series = date_series + ' ' + time_series
            df['Full_DateTime'] = pd.to_datetime(combined_series, errors='coerce', format='mixed')
        else:
            df['Full_DateTime'] = pd.to_datetime(date_series, errors='coerce', format='mixed')

    # ৪. সাল ফিল্টারিং (১৯৭০ বা অন্য কোনো ভুল সাল বাদ দিয়ে শুধু ২০২৪-২০২৬ রাখা)
    if 'Full_DateTime' in df.columns:
        df['Full_DateTime'] = pd.to_datetime(df['Full_DateTime'], errors='coerce')
        # যেসব ডেটের সাল ২০২৪ থেকে ২০২৬ এর বাইরে (বা NaT), সেগুলোকে বাদ দেওয়া
        valid_mask = (df['Full_DateTime'].dt.year >= 2024) & (df['Full_DateTime'].dt.year <= 2026)
        
        # ভুল ডেটগুলোকে NaT করে দেওয়া যাতে ইন্টারফেসে ১৯৭০ না দেখায়
        df.loc[~valid_mask, 'Full_DateTime'] = pd.NaT

    return df

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'কোনো ফাইল পাওয়া যায়নি'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ফাইল নির্বাচন করা হয়নি'}), 400
        
    file_path = os.path.join('/tmp', file.filename)
    file.save(file_path)
    
    try:
        processed_df = load_and_process_cdr(file_path)
        return jsonify({'success': True, 'message': 'ফাইল সফলভাবে প্রসেস হয়েছে!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
