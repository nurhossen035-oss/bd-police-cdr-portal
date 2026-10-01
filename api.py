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
        body { background: linear-gradient(135deg,#f0f7ff 0%,#f8fafc 48%,#f5f3ff 100%) !important; color:#172554 !important; font-family:'Noto Sans Bengali','Hind Siliguri',sans-serif !important; }
        .hero-header { background: linear-gradient(105deg,#123b82 0%,#075985 48%,#4338ca 100%) !important; border-bottom:3px solid #22d3ee !important; padding: 2rem 0; color: white; border-radius: 0 0 30px 30px; box-shadow:0 10px 28px rgba(30,64,175,.20); }
        .card { border: none; border-radius: 18px; box-shadow: 0 10px 28px rgba(37,99,235,.08); background: #fff; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 14px 34px rgba(37,99,235,.13); }
        .stat-card-blue { background: linear-gradient(135deg,#dbeafe,#eff6ff); border-left: 5px solid #2563eb; }
        .stat-card-green { background: linear-gradient(135deg,#d1fae5,#ecfdf5); border-left: 5px solid #059669; }
        .stat-card-yellow { background: linear-gradient(135deg,#fef3c7,#fffbeb); border-left: 5px solid #d97706; }
        .stat-card-red { background: linear-gradient(135deg,#ffe4e6,#fff1f2); border-left: 5px solid #e11d48; }
        .upload-box { border: 2px dashed #60a5fa; border-radius: 20px; padding: 35px; text-align: center; background: linear-gradient(135deg,#eff6ff,#f5f3ff); cursor: pointer; transition: all 0.3s ease; }
        .upload-box:hover { background: #dbeafe; border-color: #4f46e5; }
        .table-custom th { background: linear-gradient(90deg,#1d4ed8,#4338ca) !important; color: white; font-weight: 600; padding: 12px; }
        .table-custom td { vertical-align: middle; padding: 12px; font-size: 0.95rem; color: #24334f; }
        .chat-messages { height: 260px; overflow-y: auto; background: #f8fafc; padding: 20px; border: 1px solid #dbeafe; border-radius: 12px; }
        .chat-bubble { padding: 12px 18px; border-radius: 14px; margin-bottom: 12px; max-width: 80%; font-size: 0.92rem; line-height: 1.4; }
        .chat-user { background: linear-gradient(120deg,#4f46e5,#7c3aed); color: white; margin-left: auto; text-align: right; }
        .chat-ai { background: #e0f2fe; color: #164e63; margin-right: auto; }
        .app-footer { border-top: 1px solid #dbeafe; margin-top: 30px; padding: 20px 0; color: #64748b; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <header class="hero-header">
        <div class="container d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-3">
                <div class="bg-white text-primary p-3 rounded-4 shadow-sm fs-4"><i class="fa-solid fa-shield-halved"></i></div>
                <div>
                    <h2 class="fw-bold mb-0 text-white">CDR <span>Intelligence</span> Dashboard</h2>
                    <p class="mb-0 text-light opacity-75">বাংলাদেশ পুলিশ · তদন্ত ও বিশ্লেষণ কর্ম-সহায়ক পোর্টাল</p>
                </div>
            </div>
            <div class="d-flex align-items-center gap-3">
                <div class="bg-white bg-opacity-10 px-3 py-2 rounded-pill text-white border border-white border-opacity-25">
                    <strong>নুর হোসেন</strong> · খাগড়াছড়ি জেলা পুলিশ
                </div>
                <a href="/logout" class="btn btn-danger btn-sm rounded-pill px-3 fw-bold shadow-sm"><i class="fa-solid fa-right-from-bracket me-1"></i>লগআউট</a>
            </div>
        </div>
    </header>

    <div class="container py-4" style="max-width: 1450px;">
        <!-- Upload Box -->
        <div class="card p-4 mb-4">
            <div class="upload-box" onclick="document.getElementById('fileInput').click()">
                <div class="mb-2"><i class="fa-solid fa-cloud-arrow-up fa-3x text-primary"></i></div>
                <h5 class="fw-bold text-dark mb-1">CDR এক্সেল / সিএসভি ফাইল আপলোড করুন</h5>
                <p class="text-muted small mb-3">ক্লিক করে আপনার ফাইলে থাকা CDR ফরমেট (.xlsx / .csv) নির্বাচন করুন</p>
                <input type="file" id="fileInput" accept=".xlsx, .xls, .csv" style="display:none;" onchange="uploadFile()">
                <button class="btn btn-primary px-4 rounded-pill fw-bold shadow-sm"><i class="fa-solid fa-upload me-1"></i> ফাইল সিলেক্ট করুন</button>
            </div>
            <div id="loading" class="text-center mt-3" style="display:none;">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-primary fw-bold">CDR ডেটা নিখুঁতভাবে যাচাই ও প্রসেস করা হচ্ছে...</p>
            </div>
        </div>

        <!-- Dashboard Result Area -->
        <div id="resultArea" style="display:none;">
            <!-- Metrics -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card p-3 stat-card-blue">
                        <small class="text-muted fw-bold text-uppercase">মোট ভয়েস কল</small>
                        <h3 id="statTotalCalls" class="text-primary fw-bold mb-0 mt-1">0</h3>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card-green">
                        <small class="text-muted fw-bold text-uppercase">মোট কথা বলার সময়</small>
                        <h3 id="statTotalDuration" class="text-success fw-bold mb-0 mt-1">0 মি.</h3>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card-yellow">
                        <small class="text-muted fw-bold text-uppercase">IMSI / IMEI তথ্য</small>
                        <h6 id="statImsi" class="text-dark fw-bold mb-0 mt-1" style="font-size: 0.78rem; word-break: break-all;">-</h6>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card-red">
                        <small class="text-muted fw-bold text-uppercase">নাইট কল (০০:০০ - ০৬:০০)</small>
                        <h3 id="statNightCalls" class="text-danger fw-bold mb-0 mt-1">0</h3>
                    </div>
                </div>
            </div>

            <!-- AI Chat Assistant -->
            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-dark mb-3"><i class="fa-solid fa-robot text-primary me-2"></i>CDR AI ইনভেস্টিগেশন অ্যাসিস্ট্যান্ট</h5>
                <div class="chat-messages mb-3" id="chatMessages">
                    <div class="chat-bubble chat-ai">হ্যালো! আমি আপনার CDR বিশ্লেষণ অ্যাসিস্ট্যান্ট। ফাইল আপলোড করার পর যেকোনো প্রশ্ন করুন।</div>
                </div>
                <div class="input-group">
                    <input type="text" id="chatInput" class="form-control rounded-start-pill px-4" placeholder="প্রশ্ন লিখুন যেমন: রাতে কার সাথে কথা হয়েছে?..." onkeypress="if(event.key === 'Enter') sendChatQuery()">
                    <button class="btn btn-primary px-4 rounded-end-pill fw-bold" onclick="sendChatQuery()"><i class="fa-solid fa-paper-plane me-1"></i> পাঠান</button>
                </div>
            </div>

            <!-- Custom Time Filter Bar -->
            <div class="card p-4 mb-4">
                <h6 class="fw-bold text-dark mb-2"><i class="fa-solid fa-clock-rotate-left text-primary me-2"></i>নির্দিষ্ট সময় বা নম্বর দিয়ে কল ফিল্টার করুন</h6>
                <div class="row g-2 mt-1">
                    <div class="col-md-4">
                        <input type="text" id="timeSearchInput" class="form-control rounded-pill px-3" placeholder="সময় বা নম্বর লিখুন যেমন: 14:01 বা 018...">
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-primary w-100 rounded-pill fw-bold shadow-sm" onclick="filterByTime()"><i class="fa-solid fa-search me-1"></i> সার্চ করুন</button>
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-outline-secondary w-100 rounded-pill fw-bold" onclick="resetTimeFilter()">রিসেট</button>
                    </div>
                </div>
            </div>

            <!-- Top Contacts & Locations -->
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
                <h5 class="fw-bold text-dark mb-3"><i class="fa-solid fa-list-ul me-2 text-primary"></i>কল রেকর্ড তালিকা (<span id="tableTitleCount">সকল কল</span>)</h5>
                <div class="table-responsive rounded-3 border" style="max-height: 480px;">
                    <table class="table table-hover align-middle table-custom mb-0">
                        <thead>
                            <tr>
                                <th style="width: 15%;">মোবাইল নম্বর</th>
                                <th style="width: 15%;">তারিখ ও সময়</th>
                                <th style="width: 12%;">ቆালাকাল</th>
                                <th style="width: 43%;">টাওয়ার লোকেশন (LAC & Cell ID)</th>
                                <th style="width: 15%;">গুগল ম্যাপ</th>
                            </tr>
                        </thead>
                        <tbody id="callsTable"></tbody>
                    </table>
                </div>
            </div>

            <!-- Night Calls Table -->
            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-danger mb-4"><i class="fa-solid fa-moon me-2"></i>রাতের বেলার কল (০০:০০ - ০৬:০০) তালিকা</h5>
                <div class="table-responsive rounded-3 border" style="max-height: 420px;">
                    <table class="table table-hover align-middle table-custom mb-0">
                        <thead>
                            <tr>
                                <th style="width: 15%; background-color: #991b1b !important;">মোবাইল নম্বর</th>
                                <th style="width: 15%; background-color: #991b1b !important;">তারিখ ও সময়</th>
                                <th style="width: 12%; background-color: #991b1b !important;">ቆালাকাল</th>
                                <th style="width: 43%; background-color: #991b1b !important;">টাওয়ার লোকেশন</th>
                                <th style="width: 15%; background-color: #991b1b !important;">গুগল ম্যাপ</th>
                            </tr>
                        </thead>
                        <tbody id="nightCallsTable"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <footer class="app-footer">
            <div><strong>CDR Intelligence</strong> · পুলিশ ইনভেস্টিগেশন ড্যাশবোর্ড</div>
            <div><i class="fa-solid fa-phone me-1"></i>{{CONTACT_NUMBER}} · নুর হোসেন, বাংলাদেশ পুলিশ</div>
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

                if(response.status === 401) { window.location.href = "/"; return; }

                if(response.ok) {
                    globalData = data;
                    document.getElementById('chatMessages').innerHTML = `<div class="chat-bubble chat-ai">নতুন CDR ফাইল সফলভাবে বিশ্লেষণ করা হয়েছে! এখন এই ডেটা নিয়ে আমাকে যেকোনো প্রশ্ন করুন।</div>`;
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
            if(data.primary_imei) imsiText += (imsiText ? "<br>" : "") + "IMEI: " + data.primary_imei;
            document.getElementById('statImsi').innerHTML = imsiText || "পাওয়া যায়নি";

            document.getElementById('statNightCalls').innerText = data.night_calls_count;

            fillList('topCountList', data.top_by_count, item => `<span><strong>#${item.rank}</strong> ${item.number}</span><span class="badge bg-primary rounded-pill px-2 py-1">${item.count} কল</span>`);
            fillList('topDurationList', data.top_by_duration, item => `<span><strong>#${item.rank}</strong> ${item.number}</span><span class="badge bg-success rounded-pill px-2 py-1">${item.duration}</span>`);
            fillList('topLocationList', data.top_locations, item => {
                const mapBtn = item.map_url ? `<a href="${item.map_url}" target="_blank" class="btn btn-sm btn-outline-danger ms-2 rounded-pill px-2 py-0"><i class="fa-solid fa-map-location-dot"></i></a>` : '';
                return `<div class="me-auto" style="font-size: 0.85rem;"><strong>#${item.rank}</strong> ${item.location}</div><div class="d-flex align-items-center ms-2"><span class="badge bg-secondary rounded-pill me-1">${item.count}</span>${mapBtn}</div>`;
            });

            fillTable('callsTable', data.all_calls_details);
            fillTable('nightCallsTable', data.night_calls_details);
        }

        function fillList(listId, items, formatter) {
            const list = document.getElementById(listId);
            list.innerHTML = '';
            if(!items || items.length === 0) {
                list.innerHTML = '<li class="list-group-item text-muted">কোনো ডাটা নেই</li>';
                return;
            }
            items.forEach((item, index) => {
                item.rank = index + 1;
                list.innerHTML += `<li class="list-group-item d-flex justify-content-between align-items-center py-2">${formatter(item)}</li>`;
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
                const mapBtn = item.Map_URL ? `<a href="${item.Map_URL}" target="_blank" class="btn btn-sm btn-danger rounded-pill px-3 shadow-sm"><i class="fa-solid fa-map-location-dot me-1"></i>গুগল ম্যাপ</a>` : '-';
                tbody.innerHTML += `<tr>
                    <td><strong>${item.B_Party || '-'}</strong></td>
                    <td><span class="fw-semibold">${item.Call_Date || ''}</span><br><small class="text-muted">${item.Call_Time || ''}</small></td>
                    <td><span class="badge bg-success bg-opacity-10 text-success border border-success px-2 py-1">${item.Duration_Formatted || '0 সে.'}</span></td>
                    <td><div style="font-size: 0.88rem;"><i class="fa-solid fa-location-pin text-danger me-1"></i>${item.Location || 'অজানা'}</div></td>
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
            const filtered = globalData.all_calls_details.filter(item => 
                (item.Call_Time && item.Call_Time.toLowerCase().includes(query)) || 
                (item.B_Party && item.B_Party.toLowerCase().includes(query))
            );
            fillTable('callsTable', filtered);
            document.getElementById('tableTitleCount').innerText = `ফিল্টার ফলাফল (${filtered.length}টি)`;
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
            chatMessages.innerHTML += `<div class="chat-bubble chat-user">${query}</div>`;
            input.value = '';
            chatMessages.scrollTop = chatMessages.scrollHeight;

            if(!globalData) {
                setTimeout(() => {
                    chatMessages.innerHTML += `<div class="chat-bubble chat-ai">দয়া করে প্রথমে একটি CDR ফাইল আপলোড করুন।</div>`;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 400);
                return;
            }

            let aiReply = "দুঃখিত, বিষয়টি পরিষ্কার নয়। আপনি নির্দিষ্ট কোনো নম্বর বা 'রাত' লিখে সার্চ করতে পারেন।";
            const qLower = query.toLowerCase();

            if(qLower.includes('রাত') || qLower.includes('night')) {
                aiReply = `ফাইলে মোট ${globalData.night_calls_count}টি নাইট কল (রাত ১২টা থেকে সকাল ৬টা) পাওয়া গেছে।`;
            } else if(qLower.includes('বেশি') || qLower.includes('top')) {
                if(globalData.top_by_count.length > 0) {
                    aiReply = `সবচেয়ে বেশিবার যোগাযোগ করা হয়েছে ${globalData.top_by_count[0].number} নম্বরের সাথে (মোট ${globalData.top_by_count[0].count} বার)।`;
                }
            }
            setTimeout(() => {
                chatMessages.innerHTML += `<div class="chat-bubble chat-ai">${aiReply}</div>`;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 500);
        }
    </script>
</body>
</html>
"""

# Cookie authentication helpers
def check_auth(auth_cookie: str = Cookie(None)):
    if auth_cookie != "authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/", response_class=HTMLResponse)
def login_page(auth_cookie: str = Cookie(None)):
    if auth_cookie == "authenticated":
        return RedirectResponse(url="/dashboard", status_code=303)
    return HTML_TEMPLATE.replace("{{CONTACT_NUMBER}}", CONTACT_NUMBER) if False else LOGIN_HTML

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
    html_content = HTML_TEMPLATE.replace("{{CONTACT_NUMBER}}", CONTACT_NUMBER)
    return HTMLResponse(content=html_content)

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
            raise HTTPException(status_code=400, detail="দয়া করে .xlsx, .xls অথবা .csv ফাইল আপলোড করুন।")

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # Flexible column mapping for various operator CDR formats
        b_party_col = next((c for c in df.columns if any(k in c.lower() for k in ['b_party', 'other', 'number', 'called', 'calling', 'party', 'msisdn'])), None)
        date_col = next((c for c in df.columns if any(k in c.lower() for k in ['date', 'day'])), None)
        time_col = next((c for c in df.columns if any(k in c.lower() for k in ['time', 'hour'])), None)
        dt_col = next((c for c in df.columns if any(k in c.lower() for k in ['datetime', 'date_time', 'timestamp', 'call_time'])), None)
        duration_col = next((c for c in df.columns if any(k in c.lower() for k in ['duration', 'dur', 'sec', 'call_duration'])), None)
        
        lac_col = next((c for c in df.columns if any(k in c.lower() for k in ['lac', 'location area'])), None)
        cell_col = next((c for c in df.columns if any(k in c.lower() for k in ['cell', 'ci', 'cell id', 'site'])), None)
        lat_col = next((c for c in df.columns if any(k in c.lower() for k in ['lat', 'latitude'])), None)
        lon_col = next((c for c in df.columns if any(k in c.lower() for k in ['lon', 'long', 'longitude'])), None)

        imsi_col = next((c for c in df.columns if 'imsi' in c.lower()), None)
        imei_col = next((c for c in df.columns if 'imei' in c.lower()), None)

        # Standardizing B_Party
        if b_party_col:
            df['B_Party'] = df[b_party_col].astype(str).str.strip()
        else:
            df['B_Party'] = 'অজানা'

        # Duration in seconds
        if duration_col:
            df['Duration_Sec'] = pd.to_numeric(df[duration_col], errors='coerce').fillna(0).astype(int)
        else:
            df['Duration_Sec'] = 0

        # Date and Time handling
        if dt_col and dt_col in df.columns:
            df['Full_DateTime'] = pd.to_datetime(df[dt_col], errors='coerce')
        elif date_col and time_col:
            df['Full_DateTime'] = pd.to_datetime(df[date_col].astype(str) + ' ' + df[time_col].astype(str), errors='coerce')
        elif date_col:
            df['Full_DateTime'] = pd.to_datetime(df[date_col], errors='coerce')
        else:
            df['Full_DateTime'] = pd.NaT

        df['Call_Date'] = df['Full_DateTime'].dt.strftime('%Y-%m-%d').fillna(df[date_col].astype(str) if date_col else 'N/A')
        df['Call_Time'] = df['Full_DateTime'].dt.strftime('%H:%M:%S').fillna(df[time_col].astype(str) if time_col else 'N/A')

        # Hour extraction for Night calls (00:00 to 05:59)
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

        # IMSI / IMEI
        primary_imsi = str(df[imsi_col].dropna().iloc[0]) if imsi_col and not df[imsi_col].dropna().empty else ""
        primary_imei = str(df[imei_col].dropna().iloc[0]) if imei_col and not df[imei_col].dropna().empty else ""

        # Top Contacts by count
        top_by_count = []
        if 'B_Party' in df.columns:
            vc = df[df['B_Party'] != 'অজানা']['B_Party'].value_counts().head(5)
            top_by_count = [{"number": num, "count": int(cnt)} for num, cnt in vc.items()]

        # Top Contacts by duration
        top_by_duration = []
        if 'B_Party' in df.columns and 'Duration_Sec' in df.columns:
            dur_grp = df[df['B_Party'] != 'অজানা'].groupby('B_Party')['Duration_Sec'].sum().reset_index()
            dur_grp = dur_grp.sort_values(by='Duration_Sec', ascending=False).head(5)
            for _, row in dur_grp.iterrows():
                d_sec = int(row['Duration_Sec'])
                d_min = d_sec // 60
                d_s = d_sec % 60
                d_fmt = f"{d_min} মি. {d_s} সে." if d_min > 0 else f"{d_s} সে."
                top_by_duration.append({"number": row['B_Party'], "duration": d_fmt})

        # Locations & Google Map URLs
        locations = []
        for _, row in df.iterrows():
            loc_parts = []
            if lac_col and pd.notna(row.get(lac_col)):
                loc_parts.append(f"LAC: {row[lac_col]}")
            if cell_col and pd.notna(row.get(cell_col)):
                loc_parts.append(f"Cell ID: {row[cell_col]}")
            
            loc_str = " | ".join(loc_parts) if loc_parts else "অজানা লোকেশন"
            map_url = ""
            if lat_col and lon_col and pd.notna(row.get(lat_col)) and pd.notna(row.get(lon_col)):
                lat, lon = row[lat_col], row[lon_col]
                map_url = f"https://www.google.com/maps?q={lat},{lon}"
            
            df.loc[_, 'Location_Full'] = loc_str
            df.loc[_, 'Map_URL'] = map_url

        top_locations = []
        if 'Location_Full' in df.columns:
            loc_vc = df['Location_Full'].replace(['অজানা লোকেশন'], pd.NA).dropna().value_counts().head(5)
            for loc_str, cnt in loc_vc.items():
                # generate map url if lat/lon exist
                m_url = ""
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
        raise HTTPException(status_code=500, detail=f"বিশ্লেষণ করতে গিয়ে ত্রুটি ঘটেছে: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
