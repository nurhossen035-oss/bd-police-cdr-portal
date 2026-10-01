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
                <input type="text" name="username" class="form-control rounded-pill px-3 py-2" required placeholder="admin id দিন">
            </div>
            
            <div class="mb-4 text-start">
                <label class="form-label fw-bold text-secondary">পাসওয়ার্ড</label>
                <div class="position-relative">
                    <input type="password" name="password" id="passwordField" class="form-control rounded-pill px-3 py-2 pe-5" required placeholder="police123 দিন">
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
                <p class="text-muted small mb-3">ক্লিক করে আপনার ফরেনসিক CDR ফাইল (.xlsx / .csv) নির্বাচন করুন</p>
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
                                <th style="width: 43%;">লোকেশন / টাওয়ার ঠিকানা (LAC & Cell ID)</th>
                                <th style="width: 15%;">গুগল ম্যাপ</th>
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
                                <th style="width: 43%; background-color: #991b1b !important; color:#fff !important;">লোকেশন / টাওয়ার ঠিকানা (LAC & Cell ID)</th>
                                <th style="width: 15%; background-color: #991b1b !important; color:#fff !important;">গুগল ম্যাপ</th>
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
                        <span><strong>#${index+1}</strong> ${item.number}</span>
                        <span class="badge bg-primary rounded-pill px-2 py-1">${item.count} কল</span>
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
                        <span><strong>#${index+1}</strong> ${item.number}</span>
                        <span class="badge bg-success rounded-pill px-2 py-1">${item.duration}</span>
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
                        <div class="me-auto" style="font-size: 0.85rem; word-break: break-word;"><strong>#${index+1}</strong> ${item.location}</div>
                        <div class="d-flex align-items-center ms-2">
                            <span class="badge bg-secondary rounded-pill me-1">${item.count}</span>
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
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">কোনো ডাটা পাওয়া যায়নি</td></tr>';
                return;
            }
            records.forEach(item => {
                const mapBtn = item.Map_URL ? `<a href="${item.Map_URL}" target="_blank" class="btn btn-sm btn-danger rounded-pill px-3 shadow-sm"><i class="fa-solid fa-map-location-dot me-1"></i>গুগল ম্যাপ</a>` : '-';
                tbody.innerHTML += `<tr>
                    <td><strong>${item.B_Party || '-'}</strong></td>
                    <td><span class="fw-semibold text-dark">${item.Call_Date || ''}</span><br><small class="text-muted"><i class="fa-regular fa-clock me-1"></i>${item.Call_Time || ''}</small></td>
                    <td><span class="badge bg-success bg-opacity-10 text-success border border-success px-2 py-1">${item.Duration_Formatted || '0 সে.'}</span></td>
                    <td><div class="location-text"><i class="fa-solid fa-location-pin text-danger me-1"></i>${item.Location || 'অজানা'}</div></td>
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
            chatMessages.innerHTML += `<div class="chat-bubble chat-user shadow-sm">${query}</div>`;
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
                    aiReply = `"${query}" এর সাথে মিলে যায় এমন ${matches.length}টি কল রেকর্ড পাওয়া গেছে। প্রথম রেকর্ডটি: নম্বর ${matches[0].B_Party}, তারিখ: ${matches[0].Call_Date}, সময়: ${matches[0].Call_Time}, লোকেশন: ${matches[0].Location}`;
                } else {
                    aiReply = `"${query}" সম্পর্কিত কোনো তথ্য ফাইলে পাওয়া যায়নি।`;
                }
            }

            setTimeout(() => {
                chatMessages.innerHTML += `<div class="chat-bubble chat-ai shadow-sm">${aiReply}</div>`;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 500);
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home_dashboard(session: str = Cookie(default=None)):
    if session == "authenticated_police_user":
        return HTML_TEMPLATE.replace("{{CONTACT_NUMBER}}", CONTACT_NUMBER)
    return LOGIN_HTML

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASS:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session", value="authenticated_police_user")
        return response
    else:
        return HTMLResponse(content="<script>alert('ভুল ইউজারনেম অথবা পাসওয়ার্ড!'); window.location.href='/';</script>")

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="session")
    return response

@app.post("/analyze-cdr")
async def analyze_cdr(file: UploadFile = File(...), session: str = Cookie(default=None)):
    if session != "authenticated_police_user":
        raise HTTPException(status_code=401, detail="অননুমোদিত প্রবেশ! দয়া করে লগইন করুন।")
    
    try:
        contents = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents), encoding='utf-8', errors='ignore')
        else:
            try:
                df = pd.read_excel(io.BytesIO(contents))
            except:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8', errors='ignore')
        
        df.columns = [str(col).strip() for col in df.columns]

        def find_column(keywords):
            for col in df.columns:
                c_clean = str(col).lower().replace(" ", "_").replace("-", "_").replace(".", "_")
                if any(k in c_clean for k in keywords):
                    return col
            return None

        # সকল অপারেটরের (GP, Robi, Banglalink, Teletalk ইত্যাদি) বিভিন্ন ভ্যারিয়েশন কলামের জন্য সুসংহত ম্যাপ
        date_col = find_column(['call_date', 'date', 'start_date', 'call_date_time', 'event_date', 'transaction_date', 'calling_date', 'start_date_time'])
        time_col = find_column(['call_time', 'time', 'start_time', 'call_start_time', 'event_time', 'calling_time'])
        dt_col = find_column(['start_dttime', 'dttime', 'datetime', 'time_stamp', 'timestamp', 'date_time', 'call_datetime', 'event_timestamp'])
        b_party_col = find_column(['bparty', 'b_party', 'called', 'dialed', 'other_party', 'destination', 'number', 'msisdn', 'to', 'target', 'called_number', 'calling_number', 'other_party_number', 'called_party'])
        dur_col = find_column(['call_duration', 'duration', 'dur', 'sec', 'bill', 'talktime', 'callduration', 'call_dur', 'holding_time'])
        type_col = find_column(['usage_type', 'type', 'service', 'call_type', 'event', 'category'])
        
        imsi_col = find_column(['imsi', 'imsia', 'calling_imsi', 'called_imsi'])
        imei_col = find_column(['imei', 'imeia', 'calling_imei', 'called_imei'])
        
        address_col = find_column(['address', 'site_address', 'tower_address', 'site_name', 'cell_name', 'location', 'site_description', 'location_description'])
        latlong_col = find_column(['lat_long', 'latlong', 'gps', 'coord', 'location_coord', 'latitude_longitude'])
        lat_col = find_column(['latitude', 'lat'])
        lon_col = find_column(['longitude', 'long', 'lng'])
        lac_col = find_column(['lacstarta', 'lac', 'first_lac', 'last_lac', 'lac_start', 'location_area_code', 'start_lac', 'orig_lac'])
        ci_col = find_column(['cistarta', 'ci', 'cell_id', 'cellid', 'first_ci', 'last_ci', 'cell', 'cgi', 'cell_identity', 'start_ci', 'orig_ci'])

        primary_imsi = str(df[imsi_col].dropna().iloc[0]).replace('.0', '') if imsi_col and imsi_col in df.columns and not df[imsi_col].dropna().empty else ''
        primary_imei = str(df[imei_col].dropna().iloc[0]).replace('.0', '') if imei_col and imei_col in df.columns and not df[imei_col].dropna().empty else ''

        def extract_clean_number(val):
            val_str = str(val).strip()
            if 'e+' in val_str.lower() or '.' in val_str:
                try:
                    val_str = str(int(float(val_str)))
                except:
                    pass
            digits = re.sub(r'[^\d+]', '', val_str)
            if digits.startswith('8801') and len(digits) == 13:
                return digits[2:]
            elif digits.startswith('01') and len(digits) == 11:
                return digits
            elif len(digits) >= 5 and not digits.startswith('4973'):
                return digits
            return None

        if b_party_col and b_party_col in df.columns:
            df['B_Party'] = df[b_party_col].apply(extract_clean_number)
        else:
            df['B_Party'] = 'অজানা'

        if dur_col and dur_col in df.columns:
            df['Duration_Sec'] = pd.to_numeric(df[dur_col], errors='coerce').fillna(0).astype(int)
        else:
            df['Duration_Sec'] = 0

        def extract_coords(row):
            if latlong_col and latlong_col in df.columns and pd.notna(row[latlong_col]):
                val = str(row[latlong_col])
                match = re.search(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', val)
                if match:
                    return float(match.group(1)), float(match.group(2))
            if lat_col and lon_col and lat_col in df.columns and lon_col in df.columns and pd.notna(row[lat_col]) and pd.notna(row[lon_col]):
                try:
                    return float(row[lat_col]), float(row[lon_col])
                except:
                    pass
            return None, None

        coords_list = [extract_coords(row) for _, row in df.iterrows()]
        df['Lat'] = [c[0] for c in coords_list]
        df['Lon'] = [c[1] for c in coords_list]

        df['LAC'] = df[lac_col].astype(str).str.replace(r'\.0$', '', regex=True) if lac_col and lac_col in df.columns else ''
        df['Cell_ID'] = df[ci_col].astype(str).str.replace(r'\.0$', '', regex=True) if ci_col and ci_col in df.columns else ''
        df['Address_Text'] = df[address_col].astype(str).replace(['nan', 'None', 'NAT', '0', '', 'N/A', 'NaN'], '') if address_col and address_col in df.columns else ''

        def build_location_info(row):
            addr = str(row['Address_Text']).strip() if 'Address_Text' in row and pd.notna(row['Address_Text']) else ''
            lac = str(row['LAC']).strip() if 'LAC' in row and pd.notna(row['LAC']) else ''
            cid = str(row['Cell_ID']).strip() if 'Cell_ID' in row and pd.notna(row['Cell_ID']) else ''
            lat, lon = row.get('Lat'), row.get('Lon')
            
            info_parts = []
            if addr and addr.lower() not in ['nan', 'none', 'null', 'nat', '0', 'n/a', '']:
                info_parts.append(addr)
            if lat is not None and lon is not None:
                info_parts.append(f"[GPS: {lat}, {lon}]")
            if lac and lac.lower() not in ['nan', 'none', 'null', '0', 'n/a', ''] and cid and cid.lower() not in ['nan', 'none', 'null', '0', 'n/a', '']:
                info_parts.append(f"(LAC: {lac}, Cell ID: {cid})")
            elif lac and lac.lower() not in ['nan', 'none', 'null', '0', 'n/a', '']:
                info_parts.append(f"(LAC: {lac})")
            
            return " ".join([str(p) for p in info_parts]) if info_parts else "অজানা লোকেশন"

        def build_map_url(row):
            lat, lon = row.get('Lat'), row.get('Lon')
            addr = str(row.get('Address_Text', '')).strip()

            try:
                lat_num, lon_num = float(lat), float(lon)
                if (pd.notna(lat_num) and pd.notna(lon_num)
                        and -90 <= lat_num <= 90 and -180 <= lon_num <= 180):
                    return f"https://www.google.com/maps/search/?api=1&query={lat_num:.6f}%2C{lon_num:.6f}"
            except (TypeError, ValueError):
                pass

            invalid_addr = {'nan', 'none', 'null', 'nat', '0', 'n/a', ''}
            if addr and len(addr) > 3 and addr.lower() not in invalid_addr:
                query_text = addr
                if 'bangladesh' not in query_text.lower():
                    query_text += ', Bangladesh'
                query = urllib.parse.quote(query_text, safe='')
                return f"https://www.google.com/maps/search/?api=1&query={query}"

            return ""

        df['Location'] = df.apply(build_location_info, axis=1)
        df['Map_URL'] = df.apply(build_map_url, axis=1)

        def format_duration(seconds):
            if seconds < 60:
                return f"{seconds} সে."
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins} মি. {secs} সে."

        df['Duration_Formatted'] = df['Duration_Sec'].apply(format_duration)

        # উন্নত ও নিখুঁত ডেট ও টাইম পার্সিং লজিক (সকল অপারেটরের জন্য)
        df['Full_DateTime'] = pd.NaT
        if dt_col and dt_col in df.columns:
            dt_series = df[dt_col].astype(str).str.replace(r'\.0$', '', regex=True)
            df['Full_DateTime'] = pd.to_datetime(dt_series, errors='coerce', dayfirst=True)
        elif date_col and date_col in df.columns:
            date_series = df[date_col].astype(str).str.replace(r'\.0$', '', regex=True)
            if time_col and time_col in df.columns:
                time_series = df[time_col].astype(str).str.replace(r'\.0$', '', regex=True)
                df['Full_DateTime'] = pd.to_datetime(date_series + ' ' + time_series, errors='coerce', dayfirst=True)
            else:
                df['Full_DateTime'] = pd.to_datetime(date_series, errors='coerce', dayfirst=True)

        if df['Full_DateTime'].isna().all():
            for col in df.columns:
                try:
                    parsed = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                    if parsed.notna().sum() > len(df) * 0.4:
                        df['Full_DateTime'] = parsed
                        break
                except:
                    continue

        # সিডিআরের মূল তারিখ এবং সময় সঠিকভাবে সেট করার ব্যাকআপ ফলব্যাক
        raw_dates = df[date_col].astype(str).str.replace(r'\.0$', '', regex=True) if date_col and date_col in df.columns else pd.Series(['N/A']*len(df))
        raw_times = df[time_col].astype(str).str.replace(r'\.0$', '', regex=True) if time_col and time_col in df.columns else pd.Series(['N/A']*len(df))

        df['Call_Date'] = df['Full_DateTime'].dt.strftime('%Y-%m-%d').fillna(raw_dates)
        df['Call_Time'] = df['Full_DateTime'].dt.strftime('%H:%M:%S').fillna(raw_times)

        if type_col and type_col in df.columns:
            df['Type_Str'] = df[type_col].astype(str).str.upper()
            voice_df = df[~df['Type_Str'].str.contains('SMS|TEXT|MMS|PROMO', case=False, na=False)].copy()
            if not voice_df.empty:
                df = voice_df

        valid_df = df[df['B_Party'].notna() & (df['B_Party'] != '') & (df['B_Party'] != 'অজানা')].copy()

        if 'Full_DateTime' in df.columns and df['Full_DateTime'].notna().any():
            night_calls = df[(df['Full_DateTime'].dt.hour >= 0) & (df['Full_DateTime'].dt.hour < 6)].copy()
        else:
            night_calls = pd.DataFrame()

        top_by_count = []
        if not valid_df.empty and 'B_Party' in valid_df.columns:
            for num, count in valid_df['B_Party'].value_counts().head(5).items():
                top_by_count.append({"number": num, "count": count})

        top_by_duration = []
        if not valid_df.empty and 'B_Party' in valid_df.columns and 'Duration_Sec' in valid_df.columns:
            dur_grouped = valid_df.groupby('B_Party')['Duration_Sec'].sum().sort_values(ascending=False).head(5)
            for num, dur in dur_grouped.items():
                top_by_duration.append({"number": num, "duration": format_duration(dur)})

        top_locations = []
        if 'Location' in df.columns:
            valid_locs = df[df['Location'] != 'অজানা লোকেশন']
            if not valid_locs.empty:
                loc_counts = valid_locs['Location'].value_counts().head(5)
                for loc, count in loc_counts.items():
                    m_url = valid_locs[valid_locs['Location'] == loc]['Map_URL'].iloc[0] if not valid_locs[valid_locs['Location'] == loc].empty else ''
                    top_locations.append({"location": loc, "count": int(count), "map_url": m_url})

        total_duration_sec = int(df['Duration_Sec'].sum()) if 'Duration_Sec' in df.columns else 0

        all_calls_details = valid_df.to_dict(orient='records')
        night_calls_details = night_calls.to_dict(orient='records') if not night_calls.empty else []

        return {
            "total_calls": int(len(valid_df)),
            "total_duration_formatted": format_duration(total_duration_sec),
            "primary_imsi": primary_imsi,
            "primary_imei": primary_imei,
            "night_calls_count": int(len(night_calls)),
            "top_by_count": top_by_count,
            "top_by_duration": top_by_duration,
            "top_locations": top_locations,
            "all_calls_details": all_calls_details,
            "night_calls_details": night_calls_details
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
