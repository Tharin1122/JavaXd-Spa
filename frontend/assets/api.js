/* ============================================================
   JavaXd — API client (เชื่อม MMS backend จริง)
   ใช้ใน login + ทุกหน้า: API.get/post/put/patch/del
   ============================================================ */
(function () {
  const BASE = location.origin + '/api';
  const TOKEN_KEY = 'th_token';
  const REFRESH_KEY = 'th_refresh';
  const USER_KEY = 'th_user';

  function getToken() { return localStorage.getItem(TOKEN_KEY) || ''; }
  function setAuth(d) {
    if (d.accessToken) localStorage.setItem(TOKEN_KEY, d.accessToken);
    if (d.refreshToken) localStorage.setItem(REFRESH_KEY, d.refreshToken);
    if (d.user) localStorage.setItem(USER_KEY, JSON.stringify(d.user));
    localStorage.setItem('th_auth', '1');
  }
  function getUser() { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; } }
  function logout() {
    localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY); localStorage.removeItem('th_auth');
  }

  async function req(method, path, body) {
    const res = await fetch(BASE + path, {
      method,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        ...(getToken() ? { Authorization: 'Bearer ' + getToken() } : {}),
      },
      body: body != null ? JSON.stringify(body) : undefined,
    });
    let data = null;
    const txt = await res.text();
    if (txt) { try { data = JSON.parse(txt); } catch { data = txt; } }
    if (res.status === 401 && path !== '/auth/login') {
      // token หมดอายุ → กลับไป login
      logout();
      if (!/login\.html$/.test(location.pathname)) location.href = (window.BASE || '') + 'login.html';
    }
    // โชว์เหตุผลภาษาคนจาก backend เสมอ — ห้ามหลุดรหัส "HTTP 409" ถึงตาผู้ใช้
    if (!res.ok) throw new Error((data && (data.detail || data.message)) ||
      ({400:'ข้อมูลไม่ถูกต้อง',403:'ไม่มีสิทธิ์ทำรายการนี้',404:'ไม่พบข้อมูล',409:'รายการนี้ขัดกับคิว/นัดที่มีอยู่',422:'กรอกข้อมูลไม่ครบหรือผิดรูปแบบ',500:'ระบบขัดข้อง ลองใหม่อีกครั้ง'}[res.status]||'เกิดข้อผิดพลาด ลองใหม่อีกครั้ง'));
    return data;
  }

  window.API = {
    base: BASE,
    get: (p) => req('GET', p),
    post: (p, b) => req('POST', p, b),
    put: (p, b) => req('PUT', p, b),
    patch: (p, b) => req('PATCH', p, b),
    del: (p) => req('DELETE', p),
    setAuth, getUser, logout, getToken,
    // helper: แปลง UTC ISO → เวลาไทยแสดงผล
    fmtTime: (iso) => iso ? new Date(iso).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }) : '',
    fmtDate: (iso) => iso ? new Date(iso).toLocaleDateString('th-TH', { day: 'numeric', month: 'long', year: 'numeric' }) : '',
    baht: (n) => (n || 0).toLocaleString('th-TH'),
  };

  /* ============================================================
     Realtime ผ่าน SignalR — อัปเดตข้ามผู้ใช้แบบไม่ต้องรีเฟรช
     ใช้: window.RT.onUpdate((event,data)=>{ ...reload... })
     ============================================================ */
  const HOST = BASE.replace(/\/api$/, '');
  const _subs = [];
  let _conn = null;
  function fire(ev, data) { _subs.forEach(cb => { try { cb(ev, data); } catch (e) {} }); }
  window.RT = {
    onUpdate(cb) { _subs.push(cb); },
    get connection() { return _conn; },
  };
  function startRT() {
    if (!window.signalR || !getToken() || _conn) return;
    try {
      _conn = new signalR.HubConnectionBuilder()
        .withUrl(HOST + '/hubs/mms', { accessTokenFactory: () => getToken() })
        .withAutomaticReconnect()
        .build();
      ['QueueUpdated', 'BookingUpdated', 'TherapistStatusChanged', 'RoomStatusChanged', 'DashboardSnapshot', 'CleaningCheck']
        .forEach(ev => _conn.on(ev, d => fire(ev, d)));
      _conn.start().catch(() => {});
    } catch (e) {}
  }
  // backend local ไม่มี SignalR hub — ปิด realtime (ทุกหน้ามี polling สำรองทุก 60 วิอยู่แล้ว)
  var RT_ENABLED = false;
  if (RT_ENABLED && getToken()) {
    var s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/microsoft-signalr/8.0.7/signalr.min.js';
    s.onload = startRT;
    document.head.appendChild(s);
  }
})();
