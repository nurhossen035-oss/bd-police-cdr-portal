import urllib.parse
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import pandas as pd
import io
import re

app = FastAPI(title="Police CDR Investigation Dashboard")

ADMIN_USER = "admin"
ADMIN_PASS = "police123"
# নিজের যোগাযোগ নম্বর এখানে বসান; যেমন: 01XXXXXXXXX
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
        body { 
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%); 
            height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-family: 'Segoe UI', sans-serif; 
        }
        .login-card { 
            background: rgba(255, 255, 255, 0.95); 
            backdrop-filter: blur(10px);
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.4); 
            width: 100%; 
            max-width: 420px; 
            border: 1px solid rgba(255,255,255,0.2);
        }
        .login-card { background: rgba(15,23,42,.92); color:#e5e7eb; border:1px solid rgba(148,163,184,.22); box-shadow:0 24px 80px rgba(0,0,0,.45); }
        .login-card h3 { color:#f8fafc !important; }
        .login-card .text-muted, .login-card .text-secondary { color:#9ca3af !important; }
        .login-card .form-control { background:#0b1220; color:#f8fafc; border:1px solid #334155; }
        .login-card .form-control::placeholder { color:#64748b; }
        .login-card .form-control:focus { border-color:#818cf8; box-shadow:0 0 0 .2rem rgba(99,102,241,.18); }
    
        @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700;800&display=swap');
        body { background:linear-gradient(135deg,#dbeafe 0%,#f0fdfa 48%,#ede9fe 100%) !important; font-family:'Noto Sans Bengali','Hind Siliguri',sans-serif !important; }
        .login-card { background:rgba(255,255,255,.97) !important; color:#172554 !important; border:1px solid #dbeafe !important; box-shadow:0 24px 70px rgba(37,99,235,.18) !important; }
        .login-card h3 { color:#172554 !important; }
        .login-card .text-muted,.login-card .text-secondary { color:#52627a !important; }
        .login-card .form-control { background:#fff !important; color:#172554 !important; border:1px solid #cbd5e1 !important; }
        .login-card .form-control::placeholder { color:#94a3b8 !important; }
        .login-card button { background:linear-gradient(110deg,#2563eb,#7c3aed) !important; box-shadow:0 8px 20px rgba(79,70,229,.22); }
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <title>CDR সিকিউর পোর্টাল</title>
    <!-- Bootstrap 5 CSS CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- FontAwesome Icons CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fa;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: #ffffff;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
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
            
            <!-- পাসওয়ার্ড ফিল্ড ও চোখ বাটন -->
            <div class="mb-4 text-start">
                <label class="form-label fw-bold text-secondary">পাসওয়ার্ড</label>
                <div class="position-relative">
                    <input type="password" name="password" id="passwordField" class="form-control rounded-pill px-3 py-2 pe-5" required placeholder="police123 দিন">
                    <span class="position-absolute top-50 end-0 translate-middle-y me-3 text-secondary" id="togglePassword" style="cursor: pointer;">
                        <i class="fa-solid fa-eye" id="eyeIcon"></i>
                    </span>
                </div>
            </div>

            <button type="submit" class="btn btn-primary w-100 py-2 rounded-pill fw-bold shadow-sm" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border: none;">
                <i class="fa-solid fa-right-to-bracket me-1"></i> লগইন করুন
            </button>
        </form>
    </div>

    <!-- পাসওয়ার্ড শো/হাইডের জন্য জাভাস্ক্রিপ্ট -->
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
        body { background-color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; }
        .hero-header { 
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4f46e5 100%); 
            color: white; 
            padding: 2.5rem 0; 
            border-radius: 0 0 30px 30px; 
            box-shadow: 0 10px 25px rgba(79, 70, 229, 0.2); 
        }
        .card { border: none; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); transition: transform 0.2s; background: #ffffff; }
        .card:hover { transform: translateY(-2px); }
        
        .stat-card-blue { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 6px solid #3b82f6; }
        .stat-card-green { background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-left: 6px solid #22c55e; }
        .stat-card-yellow { background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%); border-left: 6px solid #eab308; }
        .stat-card-red { background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border-left: 6px solid #ef4444; }

        .upload-box { 
            border: 2px dashed #6366f1; 
            border-radius: 20px; 
            padding: 35px; 
            text-align: center; 
            background: linear-gradient(180deg, #fafafa 0%, #f5f3ff 100%); 
            cursor: pointer; 
            transition: all 0.3s ease; 
        }
        .upload-box:hover { background: #ede9fe; border-color: #4f46e5; box-shadow: 0 8px 25px rgba(99, 102, 241, 0.15); }
        
        .table-custom th { background-color: #312e81; color: white; font-weight: 600; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.5px; padding: 12px; }
        .table-custom td { vertical-align: middle; word-break: break-word; padding: 12px; font-size: 0.92rem; }
        .location-text { font-size: 0.88rem; line-height: 1.4; color: #475569; }
        
        .chat-box-container { background: #ffffff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e2e8f0; }
        .chat-messages { height: 260px; overflow-y: auto; background: #f8fafc; padding: 20px; border-bottom: 1px solid #e2e8f0; }
        .chat-bubble { padding: 12px 18px; border-radius: 14px; margin-bottom: 12px; max-width: 80%; font-size: 0.92rem; line-height: 1.4; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
        .chat-user { background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); color: white; margin-left: auto; text-align: right; border-bottom-right-radius: 2px; }
        .chat-ai { background: #e2e8f0; color: #1e293b; margin-right: auto; border-bottom-left-radius: 2px; }
        
        .badge-call { background: #3b82f6; font-size: 0.8rem; }
        .badge-time { background: #22c55e; font-size: 0.8rem; }

        /* AI2-inspired dark workspace theme */
        :root { color-scheme: dark; --panel:#111827; --panel-2:#0f172a; --line:#293548; --muted:#94a3b8; --accent:#8b7cff; }
        body { background: radial-gradient(ellipse at 15% 0%, #20204b 0%, #0b1020 42%, #080c16 100%); color:#e5e7eb; min-height:100vh; }
        .hero-header { background:rgba(12,18,34,.88); border-bottom:1px solid #273047; border-radius:0; padding:1.6rem 0; box-shadow:0 12px 40px rgba(0,0,0,.24); backdrop-filter:blur(18px); }
        .hero-header h2 { color:#f8fafc; font-size:clamp(1.2rem,2.3vw,1.85rem); font-weight:750; letter-spacing:-.025em; }
        .hero-header p { color:#a5b4fc !important; }
        .container { max-width:1480px; }
        .card, .chat-box-container { background:linear-gradient(145deg,rgba(19,28,47,.96),rgba(13,19,34,.98)) !important; color:#e5e7eb; border:1px solid #293548 !important; border-radius:18px; box-shadow:0 14px 36px rgba(0,0,0,.18) !important; }
        .card:hover { transform:translateY(-1px); border-color:#3b4964 !important; }
        .text-dark { color:#f1f5f9 !important; }
        .text-muted, small.text-muted { color:#94a3b8 !important; }
        .stat-card-blue,.stat-card-green,.stat-card-yellow,.stat-card-red { background:linear-gradient(145deg,#151f35,#111827) !important; border:1px solid #2d3b54 !important; border-left:4px solid #818cf8 !important; }
        .stat-card-green { border-left-color:#34d399 !important; }
        .stat-card-yellow { border-left-color:#fbbf24 !important; }
        .stat-card-red { border-left-color:#fb7185 !important; }
        .upload-box { background:linear-gradient(145deg,#121b30,#0e1628); border:1px dashed #6366f1; border-radius:16px; }
        .upload-box:hover { background:#17213a; border-color:#a5b4fc; }
        .form-control,.form-select { background:#0b1220 !important; color:#e5e7eb !important; border:1px solid #344158 !important; }
        .form-control::placeholder { color:#64748b !important; }
        .form-control:focus,.form-select:focus { border-color:#818cf8 !important; box-shadow:0 0 0 .2rem rgba(129,140,248,.14) !important; }
        .table-responsive { border-color:#293548 !important; }
        .table { --bs-table-bg:transparent; --bs-table-color:#dbe4f0; --bs-table-hover-bg:rgba(99,102,241,.09); --bs-table-hover-color:#fff; margin-bottom:0; }
        .table-custom th { background:#1b2540; color:#c7d2fe; border-bottom:1px solid #394766; text-transform:none; letter-spacing:0; }
        .table-custom td { border-color:#263247; }
        .table-custom tr:hover td { background:rgba(99,102,241,.055); }
        .location-text { color:#cbd5e1; }
        .chat-messages { background:linear-gradient(180deg,#0b1220,#101827); border-color:#293548; }
        .chat-bubble { border:1px solid rgba(148,163,184,.12); }
        .chat-ai { background:#1a2437; color:#dbeafe; }
        .chat-user { background:linear-gradient(135deg,#4f46e5,#7c3aed); color:#fff; }
        .list-group-item { background:transparent; color:#dbe4f0; border-color:#293548; }
        .btn-outline-secondary { color:#cbd5e1; border-color:#475569; }
        .btn-outline-secondary:hover { background:#334155; color:#fff; }
        .badge.bg-secondary { background:#334155 !important; }
        .text-primary { color:#a5b4fc !important; }
        .text-success { color:#6ee7b7 !important; }
        .text-danger { color:#fda4af !important; }
        .text-indigo { color:#a5b4fc !important; }
        /* Premium, polished AI workspace layer */
        :root { --bg:#080d18; --surface:#101827; --surface2:#131f32; --stroke:#26354c; --muted:#91a1b9; --violet:#8b7cff; --cyan:#67e8f9; }
        html { scroll-behavior:smooth; }
        body { background:radial-gradient(ellipse at 8% -8%,rgba(93,75,205,.20),transparent 35%),radial-gradient(ellipse at 95% 12%,rgba(14,165,233,.08),transparent 28%),#080d18; color:#e8eef8; font-family:Inter,'Noto Sans Bengali','Segoe UI',sans-serif; }
        .hero-header { padding:22px 0; background:rgba(9,14,26,.84); border-bottom:1px solid rgba(132,151,190,.16); box-shadow:0 12px 40px rgba(0,0,0,.20); backdrop-filter:blur(22px); }
        .header-inner,.brand-area,.header-actions,.profile-pill,.workspace-welcome { display:flex; align-items:center; }
        .header-inner { justify-content:space-between; gap:24px; }
        .brand-area { gap:15px; }
        .brand-mark { width:54px;height:54px;display:grid;place-items:center;position:relative;border-radius:17px;background:linear-gradient(145deg,rgba(139,124,255,.23),rgba(34,211,238,.10));border:1px solid rgba(139,124,255,.38);color:#b9b0ff;font-size:24px;box-shadow:inset 0 1px rgba(255,255,255,.08),0 8px 26px rgba(99,102,241,.12); }
        .brand-spark { position:absolute;width:7px;height:7px;border-radius:50%;background:#67e8f9;right:8px;top:8px;box-shadow:0 0 12px #67e8f9; }
        .brand-copy .eyebrow,.section-kicker { color:#8797b3;font-size:.68rem;font-weight:800;letter-spacing:.16em; }
        .status-dot,.chip-dot { display:inline-block;width:7px;height:7px;border-radius:50%;background:#34d399;box-shadow:0 0 10px rgba(52,211,153,.65);margin-right:7px; }
        .brand-copy h2 { margin:3px 0 1px;font-size:clamp(1.25rem,2vw,1.8rem);font-weight:800;letter-spacing:-.04em;color:#f4f7ff; }
        .brand-copy h2 span { background:linear-gradient(90deg,#b5aaff,#67e8f9);-webkit-background-clip:text;background-clip:text;color:transparent; }
        .brand-copy p { margin:0;color:#8999b3;font-size:.84rem; }
        .header-actions { gap:14px; }
        .profile-pill { gap:10px;padding:8px 13px 8px 8px;border:1px solid rgba(130,150,190,.19);border-radius:15px;background:rgba(20,30,49,.75); }
        .profile-avatar { width:39px;height:39px;display:grid;place-items:center;border-radius:12px;background:linear-gradient(145deg,#7464e8,#3e8dbd);font-size:.82rem;font-weight:800;color:white;box-shadow:0 5px 16px rgba(88,80,220,.22); }
        .profile-copy strong,.profile-copy span { display:block;white-space:nowrap; }
        .profile-copy strong { font-size:.85rem;color:#f2f5ff; }
        .profile-copy span { margin-top:2px;font-size:.7rem;color:#94a3b8; }
        .logout-btn { color:#d7dff0;text-decoration:none;font-size:.82rem;font-weight:700;padding:11px 14px;border:1px solid #35435b;border-radius:12px;background:#111b2c;transition:.2s; }
        .logout-btn:hover { background:#202b40;border-color:#6878a0;color:white; }
        .workspace-container { max-width:1500px;padding-top:28px;padding-bottom:30px; }
        .workspace-welcome { justify-content:space-between;gap:20px;margin-bottom:22px; }
        .workspace-welcome h1 { font-size:1.65rem;font-weight:800;letter-spacing:-.035em;color:#f3f6ff;margin:6px 0 4px; }
        .workspace-welcome p { margin:0;color:#8e9db5;font-size:.9rem; }
        .workspace-chip { display:flex;align-items:center;padding:10px 14px;border:1px solid #26364d;border-radius:99px;background:rgba(16,27,44,.75);color:#a9bad2;font-size:.75rem;font-weight:700;white-space:nowrap; }
        .workspace-chip .chip-dot { margin:0 0 0 10px; }
        .card,.chat-box-container { border:1px solid rgba(116,139,177,.19) !important;border-radius:20px !important;background:linear-gradient(145deg,rgba(17,27,45,.97),rgba(12,19,33,.98)) !important;box-shadow:0 16px 45px rgba(0,0,0,.15),inset 0 1px rgba(255,255,255,.025) !important; }
        .card:hover { transform:translateY(-2px);border-color:rgba(139,124,255,.32) !important; }
        .upload-box { padding:35px 20px;background:radial-gradient(ellipse at 50% 0%,rgba(110,94,229,.12),transparent 65%),#0c1424;border:1px dashed #5e62a5;border-radius:17px; }
        .upload-box:hover { background:radial-gradient(ellipse at 50% 0%,rgba(110,94,229,.19),transparent 65%),#101b30;border-color:#a59aff; }
        .upload-box h5 { font-size:1.02rem; }
        .stat-card-blue,.stat-card-green,.stat-card-yellow,.stat-card-red { min-height:94px;padding:19px !important;border-radius:17px !important;background:linear-gradient(145deg,#131e31,#101827) !important;border:1px solid #28364c !important;border-left:3px solid #8b7cff !important; }
        .stat-card-green { border-left-color:#34d399 !important; }.stat-card-yellow { border-left-color:#fbbf24 !important; }.stat-card-red { border-left-color:#fb7185 !important; }
        .stat-card-blue h3,.stat-card-green h3,.stat-card-yellow h3,.stat-card-red h3 { font-size:1.55rem;letter-spacing:-.03em; }
        .chat-box-container { padding:23px !important; }
        .chat-messages { min-height:220px;height:280px;background:linear-gradient(180deg,#0a1120,#0d1626);border:1px solid #25334a;border-radius:15px !important;padding:18px; }
        .chat-bubble { padding:13px 16px;border-radius:15px;line-height:1.65;max-width:84%; }
        .chat-ai { background:#17243a;color:#dce7f8;border-color:#293b56; }
        .chat-user { background:linear-gradient(120deg,#5b51d8,#7956d9);border:1px solid rgba(190,180,255,.20); }
        .table-custom th { background:#17243a;color:#cbd5f5;border-bottom:1px solid #33435d; }
        .table-custom td { border-color:#263247; }
        .list-group-item { padding:12px 2px !important; }
        .btn-primary { background:linear-gradient(110deg,#6657df,#8656df) !important;border:1px solid rgba(191,180,255,.18) !important;box-shadow:0 7px 20px rgba(103,80,220,.18); }
        .btn-primary:hover { filter:brightness(1.12);transform:translateY(-1px); }
        .form-control { border-radius:12px !important;min-height:43px; }
        .table-responsive { border-radius:14px !important; }
        .app-footer { display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:12px;padding:19px 4px 8px;border-top:1px solid rgba(116,139,177,.15);color:#72829c;font-size:.76rem; }
        .app-footer strong { color:#aab8d0;font-weight:700; }
        .app-footer .footer-contact { color:#8e9fba; }
        @media (max-width:768px) { .header-inner,.workspace-welcome { align-items:flex-start;flex-direction:column; }.header-actions { width:100%;justify-content:space-between; }.brand-copy p { max-width:240px; }.workspace-container { padding-top:20px; }.workspace-chip { align-self:flex-start; }.profile-copy span { white-space:normal; }.card.p-4 { padding:1rem !important; }.upload-box { padding:25px 14px; }.app-footer { flex-direction:column;align-items:flex-start; } }
        /* Brighter professional AI workspace palette */
        :root { color-scheme:light; --bright-bg:#f3f6ff; --bright-panel:#ffffff; --bright-line:#dce5f5; --bright-ink:#17233d; --bright-muted:#64748b; }
        body { background:radial-gradient(ellipse at 0% 0%,rgba(120,109,255,.15),transparent 32%),radial-gradient(ellipse at 100% 10%,rgba(45,212,191,.12),transparent 28%),#f3f6ff !important;color:#17233d !important; }
        .hero-header { background:linear-gradient(115deg,#ffffff 0%,#f2f4ff 58%,#eafaff 100%) !important;border-bottom:1px solid #dce5f5 !important;box-shadow:0 8px 30px rgba(40,65,120,.08) !important; }
        .brand-copy h2 { color:#17233d !important; }.brand-copy h2 span { background:linear-gradient(90deg,#635bdb,#0891b2);-webkit-background-clip:text;background-clip:text;color:transparent; }
        .brand-copy p,.brand-copy .eyebrow,.section-kicker,.workspace-welcome p { color:#64748b !important; }
        .profile-pill,.workspace-chip { background:#ffffff !important;border-color:#dce5f5 !important;box-shadow:0 4px 15px rgba(40,65,120,.05); }
        .profile-copy strong { color:#17233d !important; }.profile-copy span,.workspace-chip { color:#64748b !important; }
        .logout-btn { background:#fff !important;color:#475569 !important;border-color:#dce5f5 !important; }.logout-btn:hover { background:#f1f5ff !important;color:#4338ca !important; }
        .workspace-welcome h1 { color:#17233d !important; }
        .card,.chat-box-container { background:rgba(255,255,255,.96) !important;color:#17233d !important;border:1px solid #dce5f5 !important;box-shadow:0 12px 32px rgba(42,62,110,.07) !important; }
        .card:hover { border-color:#b9c8f4 !important;box-shadow:0 16px 36px rgba(65,76,160,.11) !important; }
        .upload-box { background:linear-gradient(135deg,#f7f8ff,#effaff) !important;border:2px dashed #9ba8f5 !important; }
        .upload-box:hover { background:linear-gradient(135deg,#eef0ff,#e5fbff) !important;border-color:#6965e8 !important; }
        .stat-card-blue { background:linear-gradient(135deg,#eff6ff,#e0f2fe) !important;border:1px solid #c8e1fb !important;border-left:4px solid #3b82f6 !important; }
        .stat-card-green { background:linear-gradient(135deg,#ecfdf5,#d1fae5) !important;border:1px solid #b7efd5 !important;border-left:4px solid #10b981 !important; }
        .stat-card-yellow { background:linear-gradient(135deg,#fffbeb,#fef3c7) !important;border:1px solid #f7e3a0 !important;border-left:4px solid #f59e0b !important; }
        .stat-card-red { background:linear-gradient(135deg,#fff1f2,#ffe4e6) !important;border:1px solid #fecdd3 !important;border-left:4px solid #f43f5e !important; }
        .stat-card-blue h3,.stat-card-green h3,.stat-card-yellow h3,.stat-card-red h3 { color:#17233d !important; }
        .chat-messages { background:linear-gradient(180deg,#f7f9ff,#eef4ff) !important;border-color:#dce5f5 !important; }
        .chat-ai { background:#e8edff !important;color:#29345b !important;border-color:#d4dcff !important; }.chat-user { background:linear-gradient(120deg,#625be7,#8b5cf6) !important;color:#fff !important; }
        .table-custom th { background:linear-gradient(90deg,#4f46e5,#6366f1) !important;color:#fff !important;border-color:#d7dcff !important; }
        .table-custom td { color:#26344f !important;border-color:#e7ecf5 !important; }.table-custom tr:hover td { background:#f4f6ff !important; }
        .table,.list-group-item { color:#26344f !important; }.list-group-item { border-color:#e7ecf5 !important; }
        .form-control,.form-select { background:#fff !important;color:#17233d !important;border:1px solid #cfd9eb !important; }
        .form-control::placeholder { color:#94a3b8 !important; }.form-control:focus,.form-select:focus { border-color:#818cf8 !important;box-shadow:0 0 0 .2rem rgba(99,102,241,.13) !important; }
        .text-dark { color:#17233d !important; }.text-muted,small.text-muted { color:#64748b !important; }
        .app-footer { border-color:#dce5f5 !important;color:#64748b !important; }.app-footer strong { color:#334155 !important; }
        .tower-result { background:linear-gradient(135deg,#f0fdfa,#eff6ff);border:1px solid #c9e8ee;border-radius:14px;padding:15px; }
        .tower-result .result-label { color:#64748b;font-size:.76rem;font-weight:700; }.tower-result .result-value { color:#17233d;font-weight:750;overflow-wrap:anywhere; }
        .btn-primary { background:linear-gradient(110deg,#4f46e5,#0891b2) !important;border-color:transparent !important; }
        /* Readability and refreshed high-contrast color system */
        body,button,input,select,textarea { font-family:'Noto Sans Bengali','Hind Siliguri','SolaimanLipi','Segoe UI',Tahoma,sans-serif !important; }
        body { font-size:16px !important; line-height:1.65 !important; }
        .brand-copy h2 { font-size:clamp(1.45rem,2.2vw,1.95rem) !important; }
        .brand-copy p,.workspace-welcome p,.form-label,.form-control,.form-select { font-size:1rem !important; }
        .section-kicker { font-size:.78rem !important; letter-spacing:.08em !important; color:#475569 !important; }
        .workspace-welcome h1 { font-size:1.9rem !important; color:#172554 !important; }
        .card,.chat-box-container { border-radius:18px !important; }
        #towerLookupSection { background:linear-gradient(135deg,#ffffff 0%,#f0fdfa 48%,#eef2ff 100%) !important; border-top:4px solid #0d9488 !important; }
        #towerLookupSection h5,#towerLookupSection h6 { color:#172554 !important; }
        #towerLookupSection p,.tower-result .result-label { color:#475569 !important; }
        .form-control,.form-select { min-height:48px !important; font-size:1rem !important; border:1px solid #b8c7dc !important; border-radius:10px !important; }
        .form-label { color:#24334f !important; font-weight:700 !important; margin-bottom:.45rem !important; }
        .btn { font-size:.98rem !important; font-weight:700 !important; border-radius:10px !important; padding:.65rem .9rem !important; }
        .btn-outline-secondary { color:#334155 !important; border-color:#a8b6ca !important; background:#fff !important; }
        .badge.text-bg-info { background:#cffafe !important; color:#155e75 !important; font-size:.88rem !important; padding:.55rem .8rem !important; }
        #towerSearchStatus,#towerUploadStatus { color:#334155 !important; font-size:.92rem !important; }
        .upload-box h5 { color:#172554 !important; font-size:1.15rem !important; }
        .upload-box p { color:#475569 !important; font-size:.98rem !important; }
        .table-custom td { font-size:.95rem !important; }
        @media (max-width:768px) { body { font-size:15px !important; } .workspace-welcome h1 { font-size:1.55rem !important; } }
    
        /* Bright, colorful, high-readability dashboard theme */
        @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700;800&display=swap');
        :root { color-scheme:light !important; }
        body { background:linear-gradient(135deg,#f0f7ff 0%,#f8fafc 48%,#f5f3ff 100%) !important; color:#172554 !important; font-family:'Noto Sans Bengali','Hind Siliguri','Segoe UI',sans-serif !important; }
        .hero-header { background:linear-gradient(105deg,#123b82 0%,#075985 48%,#4338ca 100%) !important; border-bottom:3px solid #22d3ee !important; box-shadow:0 10px 28px rgba(30,64,175,.20) !important; }
        .brand-copy .eyebrow,.brand-copy p { color:#dbeafe !important; }
        .brand-mark { background:linear-gradient(145deg,#2563eb,#06b6d4) !important; color:#fff !important; border:1px solid rgba(255,255,255,.35) !important; }
        .brand-copy h2 { color:#fff !important; }
        .brand-copy h2 span { background:linear-gradient(90deg,#fff,#a5f3fc) !important; -webkit-background-clip:text !important; background-clip:text !important; color:transparent !important; }
        .profile-pill { background:rgba(255,255,255,.12) !important; border-color:rgba(255,255,255,.22) !important; }
        .profile-copy strong { color:#fff !important; }.profile-copy span { color:#dbeafe !important; }
        .logout-btn { background:#ef233c !important; color:#fff !important; border:1px solid #ff8794 !important; border-radius:12px !important; box-shadow:0 6px 16px rgba(239,35,60,.28) !important; }
        .logout-btn:hover { background:#c1122f !important; color:#fff !important; transform:translateY(-1px); }
        .workspace-welcome h1 { color:#172554 !important; }.workspace-welcome p { color:#52627a !important; }
        .section-kicker { color:#2563eb !important; }
        .workspace-chip { background:#fff !important; border-color:#bfdbfe !important; color:#1d4ed8 !important; }
        .card,.chat-box-container { background:#fff !important; color:#172554 !important; border:1px solid #dbeafe !important; box-shadow:0 10px 28px rgba(37,99,235,.08) !important; }
        .card:hover { border-color:#93c5fd !important; box-shadow:0 14px 34px rgba(37,99,235,.13) !important; }
        .upload-box { background:linear-gradient(135deg,#eff6ff 0%,#f5f3ff 52%,#ecfeff 100%) !important; border:2px dashed #60a5fa !important; }
        .upload-box:hover { background:linear-gradient(135deg,#dbeafe,#ede9fe,#cffafe) !important; border-color:#4f46e5 !important; }
        .upload-box h5 { color:#172554 !important; }.upload-box p { color:#52627a !important; }
        .stat-card-blue { background:linear-gradient(135deg,#dbeafe,#eff6ff) !important; border:1px solid #93c5fd !important; border-left:5px solid #2563eb !important; }
        .stat-card-green { background:linear-gradient(135deg,#d1fae5,#ecfdf5) !important; border:1px solid #6ee7b7 !important; border-left:5px solid #059669 !important; }
        .stat-card-yellow { background:linear-gradient(135deg,#fef3c7,#fffbeb) !important; border:1px solid #fcd34d !important; border-left:5px solid #d97706 !important; }
        .stat-card-red { background:linear-gradient(135deg,#ffe4e6,#fff1f2) !important; border:1px solid #fda4af !important; border-left:5px solid #e11d48 !important; }
        .stat-card-blue small,.stat-card-green small,.stat-card-yellow small,.stat-card-red small { color:#334155 !important; }
        .stat-card-blue h3 { color:#1d4ed8 !important; }.stat-card-green h3 { color:#047857 !important; }.stat-card-yellow h3 { color:#b45309 !important; }.stat-card-red h3 { color:#be123c !important; }
        .form-control,.form-select { background:#fff !important; color:#172554 !important; border:1px solid #cbd5e1 !important; }
        .form-control::placeholder { color:#94a3b8 !important; }
        .table { --bs-table-bg:#fff; --bs-table-color:#24334f; --bs-table-hover-bg:#eff6ff; --bs-table-hover-color:#172554; }
        .table-custom th { background:linear-gradient(90deg,#1d4ed8,#4338ca) !important; color:#fff !important; border-color:#c7d2fe !important; }
        .table-custom td { color:#24334f !important; border-color:#e2e8f0 !important; }
        .location-text { color:#334155 !important; }
        .list-group-item { background:#fff !important; color:#24334f !important; border-color:#e2e8f0 !important; }
        .chat-messages { background:linear-gradient(180deg,#f8fafc,#eff6ff) !important; border:1px solid #dbeafe !important; }
        .chat-ai { background:#e0f2fe !important; color:#164e63 !important; border-color:#bae6fd !important; }
        .chat-user { background:linear-gradient(120deg,#4f46e5,#7c3aed) !important; color:#fff !important; }
        .btn-primary { background:linear-gradient(110deg,#2563eb,#7c3aed) !important; border:0 !important; color:#fff !important; }
        .btn-outline-secondary { background:#fff !important; color:#334155 !important; border-color:#cbd5e1 !important; }
        .app-footer { border-color:#dbeafe !important; color:#64748b !important; }.app-footer strong { color:#1d4ed8 !important; }
        @media (max-width:768px) { .header-inner { align-items:flex-start; flex-direction:column; }.header-actions { flex-wrap:wrap; }.workspace-container { padding-top:18px; } }
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
                    <i class="fa-solid fa-cloud-arrow-up fa-3x text-indigo" style="color: #4f46e5;"></i>
                </div>
                <h5 class="fw-bold text-dark mb-1">CDR এক্সেল / সিএসভি ফাইল আপলোড করুন</h5>
                <p class="text-muted small mb-3">ক্লিক করে আপনার ফরেনসিক CDR ফাইল (.xlsx / .csv) নির্বাচন করুন</p>
                <input type="file" id="fileInput" accept=".xlsx, .xls, .csv" style="display:none;" onchange="uploadFile()">
                <button class="btn btn-primary px-4 rounded-pill fw-bold shadow-sm" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border: none;"><i class="fa-solid fa-upload me-1"></i> ফাইল সিলেক্ট করুন</button>
            </div>
            <div id="loading" class="text-center mt-3" style="display:none;">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-primary fw-bold">ফাইল নিখুঁতভাবে প্রসেস করা হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...</p>
            </div>
        </div>

        <!-- CDR analysis results appear after a file is uploaded -->
        <!-- Dashboard Result -->
        <div id="resultArea" style="display:none;">
            <!-- Key Metrics -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card p-3 stat-card-blue">
                        <small class="text-muted fw-bold text-uppercase" style="font-size: 0.75rem;">মোট ভয়েস কল</small>
                        <h3 id="statTotalCalls" class="text-primary fw-bold mb-0 mt-1">0</h3>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card-green">
                        <small class="text-muted fw-bold text-uppercase" style="font-size: 0.75rem;">মোট কথা বলার সময়</small>
                        <h3 id="statTotalDuration" class="text-success fw-bold mb-0 mt-1">0 মি.</h3>
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
                        <h3 id="statNightCalls" class="text-danger fw-bold mb-0 mt-1">0</h3>
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
                    <button class="btn btn-primary px-4 rounded-end-pill fw-bold" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border: none;" onclick="sendChatQuery()"><i class="fa-solid fa-paper-plane me-1"></i> পাঠান</button>
                </div>
            </div>

            <!-- Custom Time Search & Filter Bar -->
            <div class="card p-4 mb-4 bg-white border">
                <h6 class="fw-bold text-dark mb-2"><i class="fa-solid fa-clock-rotate-left text-indigo me-2" style="color: #4f46e5;"></i>নির্দিষ্ট সময় বা সেকেন্ড দিয়ে কল খুঁজুন (Custom Time Filter)</h6>
                <div class="row g-2 mt-1">
                    <div class="col-md-4">
                        <input type="text" id="timeSearchInput" class="form-control rounded-pill px-3" placeholder="সময় লিখুন যেমন: 14:01:45 বা 02:00">
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-primary w-100 rounded-pill fw-bold shadow-sm" style="background: #4f46e5; border: none;" onclick="filterByTime()"><i class="fa-solid fa-search me-1"></i> সার্চ করুন</button>
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
                <h5 class="fw-bold text-dark mb-3"><i class="fa-solid fa-list-ul me-2 text-indigo" style="color: #4f46e5;"></i>কল রেকর্ড তালিকা ও গুগল ম্যাপ লিংক (<span id="tableTitleCount">সকল কল</span>)</h5>
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
                                <th style="width: 15%; background-color: #991b1b !important;">মোবাইল নম্বর</th>
                                <th style="width: 15%; background-color: #991b1b !important;">তারিখ ও সময়</th>
                                <th style="width: 12%; background-color: #991b1b !important;">কথা বলার সময়</th>
                                <th style="width: 43%; background-color: #991b1b !important;">লোকেশন / টাওয়ার ঠিকানা (LAC & Cell ID)</th>
                                <th style="width: 15%; background-color: #991b1b !important;">গুগল ম্যাপ</th>
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
                    
                    // সফলভাবে নতুন ফাইল আপলোড হলে চ্যাট বক্স একদম ফ্রেশ (Nil) করা হবে
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
                        <span class="badge badge-call rounded-pill px-2 py-1">${item.count} কল</span>
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
                        <span class="badge badge-time rounded-pill px-2 py-1">${item.duration}</span>
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
                    (item.Call_Time && item.Call_Time.includes(query))
                );
                if(matches.length > 0) {
                    aiReply = `"${query}" এর সাথে মিলে যায় এমন ${matches.length}টি কল রেকর্ড পাওয়া গেছে। প্রথম রেকর্ডটি: নম্বর ${matches[0].B_Party}, সময়: ${matches[0].Call_Time}, লোকেশন: ${matches[0].Location}`;
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

        date_col = find_column(['call_date', 'date', 'start_date', 'call_date_time'])
        time_col = find_column(['call_time', 'time', 'start_time', 'call_start_time'])
        dt_col = find_column(['start_dttime', 'dttime', 'datetime', 'time_stamp', 'timestamp', 'date_time'])
        b_party_col = find_column(['bparty', 'b_party', 'called', 'dialed', 'other_party', 'destination', 'number', 'msisdn', 'to', 'target'])
        dur_col = find_column(['call_duration', 'duration', 'dur', 'sec', 'bill', 'talktime', 'callduration'])
        type_col = find_column(['usage_type', 'type', 'service', 'call_type', 'event', 'category'])
        
        imsi_col = find_column(['imsi', 'imsia'])
        imei_col = find_column(['imei'])
        
        address_col = find_column(['address', 'site_address', 'tower_address', 'site_name', 'cell_name', 'location'])
        latlong_col = find_column(['lat_long', 'latlong', 'gps', 'coord', 'location_coord', 'latitude_longitude'])
        lat_col = find_column(['latitude', 'lat'])
        lon_col = find_column(['longitude', 'long', 'lng'])
        lac_col = find_column(['lacstarta', 'lac', 'first_lac', 'last_lac'])
        ci_col = find_column(['cistarta', 'ci', 'cell_id', 'cellid', 'first_ci', 'last_ci', 'cell'])

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
            """Prefer exact GPS coordinates; otherwise search the complete tower/site address.
            LAC/Cell ID alone is not a geographic coordinate and must not be treated as a precise pin.
            """
            lat, lon = row.get('Lat'), row.get('Lon')
            addr = str(row.get('Address_Text', '')).strip()

            # Use a precise map pin only when valid GPS coordinates are present.
            try:
                lat_num, lon_num = float(lat), float(lon)
                if (pd.notna(lat_num) and pd.notna(lon_num)
                        and -90 <= lat_num <= 90 and -180 <= lon_num <= 180):
                    return f"https://www.google.com/maps/search/?api=1&query={lat_num:.6f}%2C{lon_num:.6f}"
            except (TypeError, ValueError):
                pass

            # Do not truncate to the last one or two address components: that can resolve
            # to a whole upazila/district instead of the actual tower/site address.
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

        # উন্নত ডেট ও টাইম পার্সিং লজিক
        df['Full_DateTime'] = pd.NaT
        if dt_col and dt_col in df.columns:
            dt_series = df[dt_col].astype(str).str.replace(r'\.0$', '', regex=True)
            df['Full_DateTime'] = pd.to_datetime(dt_series, errors='coerce')
        elif date_col and date_col in df.columns:
            date_series = df[date_col].astype(str).str.replace(r'\.0$', '', regex=True)
            if time_col and time_col in df.columns:
                time_series = df[time_col].astype(str).str.replace(r'\.0$', '', regex=True)
                df['Full_DateTime'] = pd.to_datetime(date_series + ' ' + time_series, errors='coerce')
            else:
                df['Full_DateTime'] = pd.to_datetime(date_series, errors='coerce')

        if df['Full_DateTime'].isna().all():
            for col in df.columns:
                try:
                    parsed = pd.to_datetime(df[col], errors='coerce')
                    if parsed.notna().sum() > len(df) * 0.4:
                        df['Full_DateTime'] = parsed
                        break
                except:
                    continue

        df['Call_Date'] = df['Full_DateTime'].dt.strftime('%Y-%m-%d').fillna(df[date_col].astype(str) if date_col and date_col in df.columns else 'N/A')
        df['Call_Time'] = df['Full_DateTime'].dt.strftime('%H:%M:%S').fillna(df[time_col].astype(str) if time_col and time_col in df.columns else 'N/A')

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