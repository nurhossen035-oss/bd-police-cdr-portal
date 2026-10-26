import os
import pandas as pd
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

def load_and_process_cdr(file_path):
    """
    বিভিন্ন অপারেটরের ভিন্ন ভিন্ন কলামের নাম ও ফরম্যাটের CDR ফাইল (CSV, XLSX, XLS) 
    নিরাপদে রিড এবং সময়/তারিখ নিখুঁতভাবে প্রসেস করার ফাংশন।
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    df = None
    
    # ১. ফাইল ফরম্যাট অনুযায়ী নিরাপদে রিড করা
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
            # প্রথম শিট বা যেখানে CDR ডাটা আছে তা লোড করা
            sheet_name = xls.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            raise ValueError("অসমর্থিত ফাইল ফরম্যাট! দয়া করে .csv, .xlsx অথবা .xls ফাইল আপلود করুন।")
    except Exception as e:
        raise Exception(f"ফাইল পড়তে সমস্যা হয়েছে: {str(e)}")

    # কলামের নামগুলোর অতিরিক্ত স্পেস ট্রিম করা
    df.columns = [str(col).strip() for col in df.columns]

    # ২. ডাইনামিকভাবে ডেট/টাইম কলাম খুঁজে বের করা (গ্রামীণফোন, রবি, বাংলালিংক ইত্যাদির ভিন্ন নামের জন্য)
    dt_candidates = ['START', 'START_DTTIME', 'START_TIME', 'Start', 'start_time', 'Start_DateTime']
    date_candidates = ['DATE', 'CALL_DATE', 'Date', 'date']
    time_candidates = ['TIME', 'CALL_TIME', 'Time', 'time']

    found_dt_col = next((col for col in dt_candidates if col in df.columns), None)
    found_date_col = next((col for col in date_candidates if col in df.columns), None)
    found_time_col = next((col for col in time_candidates if col in df.columns), None)

    # ৩. সময় ও তারিখ নিখুঁতভাবে পার্স করার লজিক (এলোমেলো হওয়া রোধ করতে)
    df['Full_DateTime'] = pd.NaT

    if found_dt_col:
        # যদি একটিমাত্র কম্বাইন্ড ডেট-টাইম কলাম থাকে (যেমন: YYYYMMDDHHMMSS বা এক্সেল সিরিয়াল)
        if pd.api.types.is_numeric_dtype(df[found_dt_col]):
            df.loc[df[found_dt_col] <= 0, found_dt_col] = pd.NA
            # এক্সেল সিরিয়াল ডেটের জন্য unit='D' ব্যবহার করা হয়েছে
            df['Full_DateTime'] = pd.to_datetime(df[found_dt_col], unit='D', origin='1899-12-30', errors='coerce')
        else:
            dt_series = df[found_dt_col].astype(str).str.replace(r'\.0$', '', regex=True)
            dt_series = dt_series.replace(['0', '0.0', 'nan', 'NaT', 'None', ''], pd.NA)
            # dayfirst=False রেখে স্ট্যান্ডার্ড ফরম্যাট নিশ্চিত করা যাতে দিন ও মাস উল্টে না যায়
            df['Full_DateTime'] = pd.to_datetime(dt_series, errors='coerce', format='mixed')

    elif found_date_col:
        # যদি আলাদা ডেট এবং টাইম কলাম থাকে
        date_series = df[found_date_col].astype(str).str.replace(r'\.0$', '', regex=True)
        date_series = date_series.replace(['0', '0.0', 'nan', 'NaT', 'None', ''], pd.NA)
        
        if found_time_col:
            time_series = df[found_time_col].astype(str).str.replace(r'\.0$', '', regex=True).fillna('00:00:00')
            combined_series = date_series + ' ' + time_series
            df['Full_DateTime'] = pd.to_datetime(combined_series, errors='coerce', format='mixed')
        else:
            df['Full_DateTime'] = pd.to_datetime(date_series, errors='coerce', format='mixed')

    # ৪. বছর ফিল্টারিং লজিক (২০২৪ থেকে ২০২৬ এর মধ্যে সীমাবদ্ধ রাখা)
    if 'Full_DateTime' in df.columns:
        df['Full_DateTime'] = pd.to_datetime(df['Full_DateTime'], errors='coerce')
        valid_mask = (df['Full_DateTime'].dt.year >= 2024) & (df['Full_DateTime'].dt.year <= 2026)
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
        # এখানে আপনার অন্যান্য এনালাইসিস বা প্রসেসিং কোড যুক্ত করতে পারেন
        return jsonify({'success': True, 'message': 'ফাইল সফলভাবে প্রসেস হয়েছে!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
