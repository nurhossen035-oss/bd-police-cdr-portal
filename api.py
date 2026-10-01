import urllib.parse
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import pandas as pd
import io
import re

app = FastAPI(title="Police CDR Investigation Dashboard")

ADMIN_USER = "admin"
ADMIN_PASS = "police123"
CONTACT_NUMBER = "01828941367"

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <title>CDR সিকিউর পোর্টাল - বাংলাদেশ পুলিশ</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700;800&display=swap');
        body { background: linear-gradient(135deg,#dbeafe 0%,#f0fdfa 48%,#ede9fe 100%) !important; font-family:'Noto Sans Bengali','Hind Siliguri',sans-serif !important; height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-card { background:rgba(255,255,255,.97) !important; color:#172554 !important; border:1px solid #dbeafe !important; box-shadow:0 24px 70px rgba(37,99,235,.18) !important; padding: 40px; border-radius: 20px; width: 100%; max-width: 400px; }
        .login-card h3 { color:#172554 !important; font-weight: 700; }
        .login-card .text-muted,.login-card .text-secondary { color:#52627a !important; }
        .login-card .form-control { background:#fff !important; color:#172554 !important; border:1px solid #cbd5e1 !important; border-radius: 50px; padding: 10px 20px; }
        .login-card button { background:linear-gradient(135deg,#2563eb,#7c3aed) !important; box-shadow:0 8px 20px rgba(79,70,229,.22); border: none; border-radius: 50px; }
    </style>
</head>
<body>
    <div class="login-card text-center">
        <div class="mb-3">
            <i class="fa-solid fa-shield-halved fa-3x text-primary"></i>
        </div>
        <h3 class="mb-1">CDR সিকিউর পোর্টাল</h3>
        <p class="text-muted mb-4">লগইন করতে আপনার ইউজারনেম ও পাসওয়ার্ড দিন</p>
        
        <form action="/login" method="POST">
            <div class="mb-3 text-start">
                <label class="form-label fw-bold text-secondary">ইউজারনেম</label>
                <input type="text" name="username" class="form-control" required placeholder="admin id দিন">
            </div>
            
            <div class="mb-4 text-start">
                <label class="form-label fw-bold text-secondary">পাসওয়ার্ড</label>
                <div class="position-relative">
                    <input type="password" name="password" id="passwordField" class="form-control pe-5" required placeholder="police123 দিন">
                    <span class="position-absolute top-50 end-0 translate-middle-y me-3 text-secondary" id="togglePassword" style="cursor: pointer;">
                        <i class="fa-solid fa-eye" id="eyeIcon"></i>
                    </span>
                </div>
            </div>

            <button type="submit" class="btn btn-primary w-100 py-2 fw-bold text-white shadow-sm">
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
            eyeIcon.className = type === 'text' ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
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
        body { background: #f4f6f9 !important; color:#334155 !important; font-family:'Noto Sans Bengali','Hind Siliguri',sans-serif !important; }
        .hero-header { background: linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%) !important; padding: 1.8rem 0; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .card { border: none; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); background: #fff; margin-bottom: 20px; }
        .upload-card { border: 2px dashed #cbd5e1; background: #fafafa; text-align: center; padding: 30px; border-radius: 12px; cursor: pointer; }
        .upload-card:hover { border-color: #2563eb; background: #f0f4ff; }
        .table-custom th { background: #1e3a8a !important; color: white; font-weight: 600; padding: 12px; }
        .table-custom td { vertical-align: middle; padding: 10px 12px; font-size: 0.92rem; }
        .chat-box { height: 240px; overflow-y: auto; background: #f8fafc; padding: 15px; border: 1px solid #e2e8f0; border-radius: 8px; }
        .chat-bubble { padding: 10px 14px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; font-size: 0.9rem; }
        .chat-user { background: #2563eb; color: white; margin-left: auto; text-align: right; }
        .chat-ai { background: #e2e8f0; color: #1e293b; margin-right: auto; }
    </style>
</head>
<body>
    <header class="hero-header">
        <div class="container d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-3">
                <div class="bg-white text-primary p-2 rounded-3 fs-4 shadow-sm"><i class="fa-solid fa-shield-halved"></i></div>
                <div>
                    <h4 class="fw-bold mb-0 text-white">CDR Investigation Dashboard</h4>
                    <p class="mb-0 text-light small">বাংলাদেশ পুলিশ · খাগড়াছড়ি জেলা</p>
                </div>
            </div>
            <div class="d-flex align-items-center gap-3">
                <span class="text-white small fw-semibold">নুর হোসেন</span>
                <a href="/logout" class="btn btn-light btn-sm text-danger fw-bold rounded-pill px-3 shadow-sm">লগআউট</a>
            </div>
        </div>
    </header>

    <div class="container py-4" style="max-width: 1400px;">
        <!-- Upload Box -->
        <div class="card p-4">
            <div class="upload-card" onclick="document.getElementById('fileInput').click()">
                <i class="fa-solid fa-cloud-arrow-up fa-3x text-primary mb-2"></i>
                <h5 class="fw-bold text-dark mb-1">CDR ফাইল আপলোড করুন (.xlsx / .csv)</h5>
                <p class="text-muted small mb-2">ক্লিক করে আপনার সিডিআর ফাইলটি সিলেক্ট করুন</p>
                <input type="file" id="fileInput" accept=".xlsx, .xls, .csv" style="display:none;" onchange="uploadFile()">
                <button class="btn btn-primary btn-sm px-4 fw-bold rounded-pill">ফাইল সিলেক্ট করুন</button>
            </div>
            <div id="loading" class="text-center mt-3" style="display:none;">
                <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
                <span class="ms-2 text-primary fw-bold">তথ্য বিশ্লেষণ করা হচ্ছে...</span>
            </div>
        </div>

        <!-- Dashboard Result Area -->
        <div id="resultArea" style="display:none;">
            <!-- Top Summary Cards -->
            <div class="row g-3 mb-3">
                <div class="col-md-3">
                    <div class="card p-3 border-start border-primary border-4">
                        <small class="text-muted fw-bold">মোট কল</small>
                        <h4 id="statTotalCalls" class="text-primary fw-bold mb-0">0</h4>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 border-start border-success border-4">
                        <small class="text-muted fw-bold">মোট কথা বলার সময়</small>
                        <h4 id="statTotalDuration" class="text-success fw-bold mb-0">0 মি.</h4>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 border-start border-warning border-4">
                        <small class="text-muted fw-bold">IMSI / IMEI</small>
                        <h6 id="statImsi" class="text-dark fw-bold mb-0" style="font-size: 0.8rem; word-break: break-all;">-</h6>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 border-start border-danger border-4">
                        <small class="text-muted fw-bold">নাইট কল (০০:০০ - ০৬:০০)</small>
                        <h4 id="statNightCalls" class="text-danger fw-bold mb-0">0</h4>
                    </div>
                </div>
            </div>

            <!-- Top Stats & Lists -->
            <div class="row g-3 mb-3">
                <div class="col-md-4">
                    <div class="card p-3 h-100">
                        <h6 class="fw-bold text-dark mb-3"><i class="fa-solid fa-address-book text-primary me-2"></i>বেশিবার যোগাযোগ</h6>
                        <ul class="list-group list-group-flush" id="topCountList"></ul>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card p-3 h-100">
                        <h6 class="fw-bold text-dark mb-3"><i class="fa-solid fa-stopwatch text-success me-2"></i>দীর্ঘ সময় কথা</h6>
                        <ul class="list-group list-group-flush" id="topDurationList"></ul>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card p-3 h-100">
                        <h6 class="fw-bold text-dark mb-3"><i class="fa-solid fa-location-dot text-danger me-2"></i>প্রধান লোকেশনসমূহ</h6>
                        <ul class="list-group list-group-flush" id="topLocationList"></ul>
                    </div>
                </div>
            </div>

            <!-- AI Assistant -->
            <div class="card p-3 mb-3">
                <h6 class="fw-bold text-dark mb-2"><i class="fa-solid fa-robot text-primary me-2"></i>CDR AI অ্যাসিস্ট্যান্ট</h6>
                <div class="chat-box mb-2" id="chatMessages">
                    <div class="chat-bubble chat-ai">হ্যালো! CDR ফাইল বিশ্লেষণ সম্পন্ন হয়েছে। যেকোনো প্রশ্ন করতে পারেন।</div>
                </div>
                <div class="input-group input-group-sm">
                    <input type="text" id="chatInput" class="form-control" placeholder="প্রশ্ন লিখুন..." onkeypress="if(event.key === 'Enter') sendChatQuery()">
                    <button class="btn btn-primary px-3 fw-bold" onclick="sendChatQuery()">পাঠান</button>
                </div>
            </div>

            <!-- Filter Bar -->
            <div class="card p-3 mb-3">
                <div class="row g-2 align-items-center">
                    <div class="col-md-4">
                        <input type="text" id="timeSearchInput" class="form-control form-control-sm" placeholder="নম্বর বা সময় দিয়ে খুঁজুন (যেমন: 018...)">
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-primary btn-sm w-100 fw-bold" onclick="filterByTime()">ফিল্টার</button>
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-outline-secondary btn-sm w-100 fw-bold" onclick="resetTimeFilter()">রিসেট</button>
                    </div>
                </div>
            </div>

            <!-- All Calls Table -->
            <div class="card p-3 mb-3">
                <h6 class="fw-bold text-dark mb-3"><i class="fa-solid fa-list me-2 text-primary"></i>সকল কল রেকর্ড তালিকা (<span id="tableTitleCount">সকল</span>)</h6>
                <div class="table-responsive" style="max-height: 450px;">
                    <table class="table table-hover align-middle table-custom mb-0">
                        <thead>
                            <tr>
                                <th>মোবাইল নম্বর</th>
                                <th>তারিখ ও সময়</th>
                                <th>ቆালাকাল</th>
                                <th>টাওয়ার লোকেশন (LAC & Cell ID)</th>
                                <th>গুগল ম্যাপ</th>
                            </tr>
                        </thead>
                        <tbody id="callsTable"></tbody>
                    </table>
                </div>
            </div>

            <!-- Night Calls Table -->
            <div class="card p-3">
                <h6 class="fw-bold text-danger mb-3"><i class="fa-solid fa-moon me-2"></i>রাতের বেলার কল তালিকা (০০:০০ - ০৬:০০)</h6>
                <div class="table-responsive" style="max-height: 380px;">
                    <table class="table table-hover align-middle table-custom mb-0">
                        <thead>
                            <tr>
                                <th style="background-color: #991b1b !important;">মোবাইল নম্বর</th>
                                <th style="background-color: #991b1b !important;">তারিখ ও সময়</th>
                                <th style="background-color: #991b1b !important;">ቆালাকাল</th>
                                <th style="background-color: #991b1b !important;">টাওয়ার লোকেশন</th>
                                <th style="background-color: #991b1b !important;">গুগল ম্যাপ</th>
                            </tr>
                        </thead>
                        <tbody id="nightCallsTable"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        let globalData = null;

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

                if(response.status === 401) { window.location.href = "/"; return; }

                if(response.ok) {
                    globalData = data;
                    document.getElementById('chatMessages').innerHTML = `<div class="chat-bubble chat-ai">নতুন CDR ফাইল সফলভাবে বিশ্লেষণ করা হয়েছে!</div>`;
                    renderDashboard(data);
                } else {
                    alert("ত্রুটি: " + (data.detail || "ফাইল প্রসেস করা যায়নি"));
                }
            } catch(err) {
                document.getElementById('loading').style.display = 'none';
                alert("সার্ভারে সংযোগ স্থাপন করা যায়নি!");
            }
        }

        function renderDashboard(data) {
            document.getElementById('resultArea').style.display = 'block';
            document.getElementById('statTotalCalls').innerText = data.total_calls;
            document.getElementById('statTotalDuration').innerText = data.total_duration_formatted;
            
            let imsiText = "";
            if(data.primary_imsi) imsiText += "IMSI: " + data.primary_imsi;
            if(data.primary_imei) imsiText += (imsiText ? " | " : "") + "IMEI: " + data.primary_imei;
            document.getElementById('statImsi').innerHTML = imsiText || "পাওয়া যায়নি";

            document.getElementById('statNightCalls').innerText = data.night_calls_count;

            fillList('topCountList', data.top_by_count, item => `<span><strong>#${item.rank}</strong> ${item.number}</span><span class="badge bg-primary rounded-pill">${item.count} কল</span>`);
            fillList('topDurationList', data.top_by_duration, item => `<span><strong>#${item.rank}</strong> ${item.number}</span><span class="badge bg-success rounded-pill">${item.duration}</span>`);
            fillList('topLocationList', data.top_locations, item => {
                const mapBtn = item.map_url ? `<a href="${item.map_url}" target="_blank" class="btn btn-sm btn-outline-danger py-0 ms-1"><i class="fa-solid fa-map-location-dot"></i></a>` : '';
                return `<div class="d-flex justify-content-between align-items-center w-100" style="font-size:0.85rem;"><span><strong>#${item.rank}</strong> ${item.location}</span><div><span class="badge bg-secondary">${item.count}</span>${mapBtn}</div></div>`;
            });

            fillTable('callsTable', data.all_calls_details);
            fillTable('nightCallsTable', data.night_calls_details);
        }

        function fillList(listId, items, formatter) {
            const list = document.getElementById(listId);
            list.innerHTML = '';
            if(!items || items.length === 0) {
                list.innerHTML = '<li class="list-group-item text-muted small">কোনো ডাটা নেই</li>';
                return;
            }
            items.forEach((item, index) => {
                item.rank = index + 1;
                list.innerHTML += `<li class="list-group-item py-2">${formatter(item)}</li>`;
            });
        }

        function fillTable(tableId, records) {
            const tbody = document.getElementById(tableId);
            tbody.innerHTML = '';
            if(!records || records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">কোনো ডাটা পাওয়া যায়নি</td></tr>';
                return;
            }
            records.forEach(item => {
                const mapBtn = item.Map_URL ? `<a href="${item.Map_URL}" target="_blank" class="btn btn-sm btn-danger py-0 px-2 rounded-pill"><i class="fa-solid fa-map-location-dot me-1"></i>ম্যাপ</a>` : '-';
                tbody.innerHTML += `<tr>
                    <td><strong>${item.B_Party || '-'}</strong></td>
                    <td><span class="fw-semibold">${item.Call_Date || ''}</span> <small class="text-muted">${item.Call_Time || ''}</small></td>
                    <td><span class="badge bg-success bg-opacity-15 text-success">${item.Duration_Formatted || '0 সে.'}</span></td>
                    <td><small><i class="fa-solid fa-location-pin text-danger me-1"></i>${item.Location || 'অজানা'}</small></td>
                    <td>${mapBtn}</td>
                </tr>`;
            });
        }

        function filterByTime() {
            if(!globalData) return;
            const query = document.getElementById('timeSearchInput').value.trim().toLowerCase();
            if(!query) {
                fillTable('callsTable', globalData.all_calls_details);
                document.getElementById('tableTitleCount').innerText = "সকল";
                return;
            }
            const filtered = globalData.all_calls_details.filter(item => 
                (item.Call_Time && item.Call_Time.toLowerCase().includes(query)) || 
                (item.B_Party && item.B_Party.toLowerCase().includes(query))
            );
            fillTable('callsTable', filtered);
            document.getElementById('tableTitleCount').innerText = `ফিল্টারকৃত (${filtered.length})`;
        }

        function resetTimeFilter() {
            document.getElementById('timeSearchInput').value = '';
            if(globalData) {
                fillTable('callsTable', globalData.all_calls_details);
                document.getElementById('tableTitleCount').innerText = "সকল";
            }
        }

        function sendChatQuery() {
            const input = document.getElementById('chatInput');
            const query = input.value.trim();
            if(!query) return;

            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML += `<div class="chat-bubble chat-user">${query}</div>`;
            input.value = '';
            chatMessages.scrollTop = chatMessages.scrollHeight;

            if(!globalData) {
                setTimeout(() => {
                    chatMessages.innerHTML += `<div class="chat-bubble chat-ai">দয়া করে প্রথমে একটি CDR ফাইল আপلود করুন।</div>`;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 300);
                return;
            }

            let aiReply = "আপনার অনুসন্ধানের জন্য ধন্যবাদ। নির্দিষ্ট কোনো নম্বর বা সময় দিয়ে দেখতে পারেন।";
            const qLower = query.toLowerCase();

            if(qLower.includes('রাত') || qLower.includes('night')) {
                aiReply = `ফাইলে মোট ${globalData.night_calls_count}টি নাইট কল পাওয়া গেছে।`;
            } else if(qLower.includes('বেশি') || qLower.includes('top')) {
                if(globalData.top_by_count.length > 0) {
                    aiReply = `সবচেয়ে বেশিবার যোগাযোগ করা হয়েছে ${globalData.top_by_count[0].number} নম্বরের সাথে (${globalData.top_by_count[0].count} বার)।`;
                }
            }
            setTimeout(() => {
                chatMessages.innerHTML += `<div class="chat-bubble chat-ai">${aiReply}</div>`;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 400);
        }
    </script>
</body>
</html>
"""

def check_auth(auth_cookie: str = Cookie(None)):
    if auth_cookie != "authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/", response_class=HTMLResponse)
def login_page(auth_cookie: str = Cookie(None)):
    if auth_cookie == "authenticated":
        return RedirectResponse(url="/dashboard", status_code=303)
    return LOGIN_HTML

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASS:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="auth_cookie", value="authenticated", httponly=True)
        return response
    return RedirectResponse(url="/?error=1", status_code=303)

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="auth_cookie")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(auth_cookie: str = Cookie(None)):
    if auth_cookie != "authenticated":
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(content=HTML_TEMPLATE.replace("{{CONTACT_NUMBER}}", CONTACT_NUMBER))

@app.post("/analyze-cdr")
async def analyze_cdr(file: UploadFile = File(...), auth_cookie: str = Cookie(None)):
    if auth_cookie != "authenticated":
        raise JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    try:
        contents = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except:
                df = pd.read_csv(io.BytesIO(contents), encoding='latin1')
        elif filename.endswith(('.xls', '.xlsx')):
            try:
                df = pd.read_excel(io.BytesIO(contents))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"এক্সেল ফাইল পড়তে সমস্যা হয়েছে: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="দয়া করে সঠিক এক্সেল বা সিএসভি ফাইল দিন।")

        df.columns = [str(c).strip() for c in df.columns]

        # Robust column finding for numbers, dates, times, and locations
        b_party_col = next((c for c in df.columns if any(k in c.lower() for k in ['b_party', 'other', 'number', 'called', 'calling', 'party', 'msisdn', 'remote_party'])), None)
        date_col = next((c for c in df.columns if any(k in c.lower() for k in ['date', 'day'])), None)
        time_col = next((c for c in df.columns if any(k in c.lower() for k in ['time', 'hour'])), None)
        dt_col = next((c for c in df.columns if any(k in c.lower() for k in ['datetime', 'date_time', 'timestamp', 'call_time'])), None)
        duration_col = next((c for c in df.columns if any(k in c.lower() for k in ['duration', 'dur', 'sec', 'call_duration'])), None)
        
        lac_col = next((c for c in df.columns if any(k in c.lower() for k in ['lac', 'location area', 'site_id'])), None)
        cell_col = next((c for c in df.columns if any(k in c.lower() for k in ['cell', 'ci', 'cell id', 'cell_id', 'cid'])), None)
        lat_col = next((c for c in df.columns if any(k in c.lower() for k in ['lat', 'latitude'])), None)
        lon_col = next((c for c in df.columns if any(k in c.lower() for k in ['lon', 'long', 'longitude'])), None)

        imsi_col = next((c for c in df.columns if 'imsi' in c.lower()), None)
        imei_col = next((c for c in df.columns if 'imei' in c.lower()), None)

        # Ensure correct B_Party extraction
        if b_party_col:
            df['B_Party'] = df[b_party_col].astype(str).str.strip().replace(['nan', 'None', 'NAT'], '-')
        else:
            df['B_Party'] = '-'

        if duration_col:
            df['Duration_Sec'] = pd.to_numeric(df[duration_col], errors='coerce').fillna(0).astype(int)
        else:
            df['Duration_Sec'] = 0

        if dt_col and dt_col in df.columns:
            df['Full_DateTime'] = pd.to_datetime(df[dt_col], errors='coerce')
        elif date_col and time_col:
            df['Full_DateTime'] = pd.to_datetime(df[date_col].astype(str) + ' ' + df[time_col].astype(str), errors='coerce')
        elif date_col:
            df['Full_DateTime'] = pd.to_datetime(df[date_col], errors='coerce')
        else:
            df['Full_DateTime'] = pd.NaT

        df['Call_Date'] = df['Full_DateTime'].dt.strftime('%Y-%m-%d').fillna(df[date_col].astype(str) if date_col else '-')
        df['Call_Time'] = df['Full_DateTime'].dt.strftime('%H:%M:%S').fillna(df[time_col].astype(str) if time_col else '-')

        df['Hour'] = df['Full_DateTime'].dt.hour
        if df['Hour'].isna().all() and time_col:
            extracted = pd.to_numeric(df[time_col].astype(str).str.extract(r'^(\d{1,2})')[0], errors='coerce')
            df['Hour'] = extracted.fillna(0)
        else:
            df['Hour'] = df['Hour'].fillna(0)

        night_df = df[(df['Hour'] >= 0) & (df['Hour'] < 6)]
        night_calls_count = len(night_df)

        total_calls = len(df)
        total_duration_sec = df['Duration_Sec'].sum()
        hours = total_duration_sec // 3600
        minutes = (total_duration_sec % 3600) // 60
        seconds = total_duration_sec % 60
        total_duration_formatted = f"{hours} ঘণ্টা {minutes} মি." if hours > 0 else f"{minutes} মিনিট {seconds} সে."

        primary_imsi = str(df[imsi_col].dropna().iloc[0]) if imsi_col and not df[imsi_col].dropna().empty else ""
        primary_imei = str(df[imei_col].dropna().iloc[0]) if imei_col and not df[imei_col].dropna().empty else ""

        top_by_count = []
        if 'B_Party' in df.columns:
            vc = df[df['B_Party'] != '-']['B_Party'].value_counts().head(5)
            top_by_count = [{"number": num, "count": int(cnt)} for num, cnt in vc.items()]

        top_by_duration = []
        if 'B_Party' in df.columns and 'Duration_Sec' in df.columns:
            dur_grp = df[df['B_Party'] != '-'].groupby('B_Party')['Duration_Sec'].sum().reset_index()
            dur_grp = dur_grp.sort_values(by='Duration_Sec', ascending=False).head(5)
            for _, row in dur_grp.iterrows():
                d_sec = int(row['Duration_Sec'])
                d_min = d_sec // 60
                d_s = d_sec % 60
                d_fmt = f"{d_min} মি. {d_s} সে." if d_min > 0 else f"{d_s} সে."
                top_by_duration.append({"number": row['B_Party'], "duration": d_fmt})

        for idx, row in df.iterrows():
            loc_parts = []
            lac_val = row.get(lac_col) if lac_col else None
            cell_val = row.get(cell_col) if cell_col else None
            
            if lac_val and pd.notna(lac_val):
                loc_parts.append(f"LAC: {lac_val}")
            if cell_val and pd.notna(cell_val):
                loc_parts.append(f"Cell ID: {cell_val}")
            
            loc_str = " | ".join(loc_parts) if loc_parts else "অজানা লোকেশন"
            
            map_url = ""
            if lat_col and lon_col and pd.notna(row.get(lat_col)) and pd.notna(row.get(lon_col)):
                lat, lon = row[lat_col], row[lon_col]
                map_url = f"https://www.google.com/maps?q={lat},{lon}"
            elif lac_val and cell_val and pd.notna(lac_val) and pd.notna(cell_val):
                map_url = f"https://www.google.com/maps/search/Cell+Tower+LAC+{lac_val}+Cell+ID+{cell_val}"
            
            df.loc[idx, 'Location_Full'] = loc_str
            df.loc[idx, 'Map_URL'] = map_url

        top_locations = []
        if 'Location_Full' in df.columns:
            loc_vc = df['Location_Full'].replace(['অজানা লোকেশন'], pd.NA).dropna().value_counts().head(5)
            for loc_str, cnt in loc_vc.items():
                m_url = f"https://www.google.com/maps/search/{urllib.parse.quote(loc_str)}"
                top_locations.append({"location": loc_str, "count": int(cnt), "map_url": m_url})

        all_calls_details = []
        for _, row in df.head(300).iterrows():
            d_sec = row['Duration_Sec']
            all_calls_details.append({
                "B_Party": row.get('B_Party', '-'),
                "Call_Date": row.get('Call_Date', ''),
                "Call_Time": row.get('Call_Time', ''),
                "Duration_Formatted": f"{d_sec // 60} মি. {d_sec % 60} সে.",
                "Location": row.get('Location_Full', 'অজানা'),
                "Map_URL": row.get('Map_URL', '')
            })

        night_df_records = df[(df['Hour'] >= 0) & (df['Hour'] < 6)]
        night_calls_details = []
        for _, row in night_df_records.head(300).iterrows():
            d_sec = row['Duration_Sec']
            night_calls_details.append({
                "B_Party": row.get('B_Party', '-'),
                "Call_Date": row.get('Call_Date', ''),
                "Call_Time": row.get('Call_Time', ''),
                "Duration_Formatted": f"{d_sec // 60} মি. {d_sec % 60} সে.",
                "Location": row.get('Location_Full', 'অজানা'),
                "Map_URL": row.get('Map_URL', '')
            })

        return JSONResponse({
            "total_calls": total_calls,
            "total_duration_formatted": total_duration_formatted,
            "primary_imsi": primary_imsi,
            "primary_imei": primary_imei,
            "night_calls_count": night_calls_count,
            "top_by_count": top_by_count,
            "top_by_duration": top_by_duration,
            "top_locations": top_locations,
            "all_calls_details": all_calls_details,
            "night_calls_details": night_calls_details
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"বিশ্লেষণ ত্রুটি: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
