/* ============================================================
   JavaXd — Shared shell: sidebar, topbar, modal, helpers
   Each page sets window.BASE ('' at root, '../' inside /pages)
   and window.PAGE (active nav key) before this script runs.
   ============================================================ */
(function(){
const B = window.BASE || '';
const PAGE = window.PAGE || 'dashboard';

/* ---------- icons ---------- */
const I = {
  lotus:'<path d="M12 21c-4.5 0-8-2.6-8-6 0 0 2.4.4 4 1.6C10.7 11.7 12 9 12 9s1.3 2.7 4 7.6c1.6-1.2 4-1.6 4-1.6 0 3.4-3.5 6-8 6Z" fill="currentColor"/><path d="M12 18c-2 0-3.6-1.6-3.6-4 0-2 1.6-4.5 3.6-6 2 1.5 3.6 4 3.6 6 0 2.4-1.6 4-3.6 4Z" fill="currentColor" opacity=".55"/>',
  home:'<path d="M3 10.5 12 3l9 7.5M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  cal:'<rect x="3" y="4.5" width="18" height="16" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M3 9h18M8 2.5v4M16 2.5v4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  flow:'<path d="M4 7h10M4 7l3-3M4 7l3 3M20 17H10M20 17l-3-3M20 17l-3 3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  users:'<circle cx="9" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0M16 6.2a3 3 0 0 1 0 5.6M17.5 19a5.2 5.2 0 0 0-2.3-3.4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  spa:'<path d="M12 4c2.5 2.5 4 5 4 8a4 4 0 1 1-8 0c0-3 1.5-5.5 4-8Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M12 12v6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  badge:'<circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M5 21a7 7 0 0 1 14 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  wallet:'<rect x="3" y="6" width="18" height="13" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M3 10h18M16 14.5h2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  money:'<path d="M12 3v18M16.5 6.5C15.5 5.2 13.9 4.5 12 4.5c-2.5 0-4 1.3-4 3s1.5 2.6 4 3 4 1.3 4 3-1.5 3-4 3c-1.9 0-3.5-.7-4.5-2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  tag:'<path d="M3.5 11.5 11 4a2 2 0 0 1 1.4-.6H19a1.5 1.5 0 0 1 1.5 1.5v6.6a2 2 0 0 1-.6 1.4l-7.5 7.5a2 2 0 0 1-2.8 0l-6.1-6.1a2 2 0 0 1 0-2.8Z" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="16" cy="8" r="1.4" fill="currentColor"/>',
  box:'<path d="M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5v-9Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M3.5 7.5 12 12m0 9V12m8.5-4.5L12 12" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
  shield:'<path d="M12 3l7 2.5v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10v-5L12 3Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M9 12l2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  gear:'<circle cx="12" cy="12" r="3.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 2.5v2.6M12 18.9v2.6M21.5 12h-2.6M5.1 12H2.5M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8M18.4 18.4l-1.8-1.8M7.4 7.4 5.6 5.6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  chart:'<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  logs:'<path d="M5 4h11l3 3v13H5V4Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M9 12h6M9 16h6M9 8h3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  search:'<circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m20 20-3.2-3.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  bell:'<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M10 19a2 2 0 0 0 4 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  chat:'<path d="M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-4 4v-4H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
  plus:'<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  chev:'<path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  chevR:'<path d="m9 6 6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  chevL:'<path d="m15 6-6 6 6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  line:'<path d="M20 10.5c0-3.9-3.9-7-8.7-7S2.6 6.6 2.6 10.5c0 3.5 3.1 6.4 7.3 7 .3 0 .7.2.8.5.1.2 0 .6 0 .8l-.1.8c0 .2-.2.9.8.5s5.3-3.1 7.2-5.3c1.3-1.4 1.9-2.9 1.9-4.3Z" fill="currentColor"/>',
  check:'<path d="M20 6 9 17l-5-5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
  edit:'<path d="M4 20h4L18.5 9.5a2 2 0 0 0 0-2.8l-1.2-1.2a2 2 0 0 0-2.8 0L4 16v4Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="2.6" fill="none" stroke="currentColor" stroke-width="1.6"/>',
  filter:'<path d="M3 5h18l-7 8v6l-4-2v-4L3 5Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  clock:'<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 7.5V12l3 2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  phone:'<path d="M5 4h3l1.5 4-2 1.5a11 11 0 0 0 5 5l1.5-2 4 1.5v3a2 2 0 0 1-2 2A15 15 0 0 1 3 6a2 2 0 0 1 2-2Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  dots:'<circle cx="5" cy="12" r="1.7" fill="currentColor"/><circle cx="12" cy="12" r="1.7" fill="currentColor"/><circle cx="19" cy="12" r="1.7" fill="currentColor"/>',
  down:'<path d="M12 4v12m0 0 4-4m-4 4-4-4M5 20h14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  star:'<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 17l-5.2 2.6 1-5.8-4.3-4.1 5.9-.9L12 3.5Z" fill="currentColor"/>',
  x:'<path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>',
  receipt:'<path d="M5 3.5h14v18l-2.4-1.5-2.3 1.5L12 20l-2.3 1.5L7.4 20 5 21.5v-18Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8.5 8h7M8.5 12h7M8.5 15.5h4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  gem:'<path d="M6 3.5h12l3 5-9 12-9-12 3-5Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M3 8.5h18M9 3.5 7.5 8.5 12 20.5M15 3.5l1.5 5L12 20.5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>',
  print:'<path d="M7 8V3.5h10V8M7 18H5a1 1 0 0 1-1-1v-6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6a1 1 0 0 1-1 1h-2M7 14h10v6.5H7V14Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  qr:'<path d="M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 3h3m3 0h0m-6 3h6v-3m0-3v3m-3-3h0" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>',
  trash:'<path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
  menu:'<path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>',
  screen:'<rect x="3" y="4.5" width="18" height="12.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M9 20.5h6M12 17v3.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
};
function svg(name,cls){return `<svg viewBox="0 0 24 24" ${cls?`class="${cls}"`:''}>${I[name]||''}</svg>`}
window.svg = svg; window.ICONS = I;

/* ---------- avatar ---------- */
const AV_COLORS=[['#7b6bf0','#6c5ce7'],['#34c98a','#22b07d'],['#f7b955','#f5a623'],['#5fb4ff','#3b9bff'],
['#f08aa8','#ec5f86'],['#9b8cff','#7c6bf0'],['#56cdc0','#2bb3a3'],['#f0907a','#e8674b']];
function hash(s){let h=0;for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))>>>0;return h}
function initials(n){const p=n.replace(/^(คุณ|พี่|น้อง)/,'').trim().split(/\s+/);return (p[0]?p[0][0]:'')+(p[1]?p[1][0]:'')}
window.av=function(name,size,sq,img){
  name=(name==null?'':String(name));
  // ถ้ามีรูป (เช่นโปรไฟล์ LINE) → แสดงรูป, โหลดไม่ได้ค่อย fallback เป็นตัวย่อ
  if(img&&typeof img==='string'&&/^https?:\/\//.test(img)){
    return `<img class="av${sq?' sq':''}" src="${img}" referrerpolicy="no-referrer" alt="" style="width:${size}px;height:${size}px;object-fit:cover" onerror="this.outerHTML=window.av(${JSON.stringify(name||'')},${size},${sq?1:0})">`;
  }
  const c=AV_COLORS[hash(name)%AV_COLORS.length];
  const fs=Math.round(size*0.4);
  return `<span class="av${sq?' sq':''}" style="width:${size}px;height:${size}px;font-size:${fs}px;background:linear-gradient(135deg,${c[0]},${c[1]})">${initials(name)||'•'}</span>`;
};
/* ผู้ใช้ที่ล็อกอินอยู่ (จาก localStorage หลัง login) */
function curUser(){return (window.API&&API.getUser&&API.getUser())||{};}
function curName(){return curUser().displayName||'ผู้ใช้';}
const ROLE_TH={Owner:'เจ้าของร้าน',Manager:'ผู้จัดการ',Reception:'แอดมิน / รีเซป',Therapist:'หมอนวด',Cashier:'แคชเชียร์'};
function roleThai(r){return ROLE_TH[r]||r||'พนักงาน';}
function curRole(){const u=curUser();return roleThai((u.roles&&u.roles[0])||u.role);}
window.fmt=function(n){return (typeof n==='number'&&isFinite(n)?n:0).toLocaleString('en-US')};

/* ---------- nav config ---------- */
const NAV=[
  {k:'dashboard',ic:'home',t:'แดชบอร์ด',h:'index.html'},
  {k:'bookings',ic:'cal',t:'การจอง & คิวงาน',h:'pages/bookings.html',
    sub:[{t:'รายการจอง',h:'pages/bookings.html'},{t:'คิวงาน (เรียลไทม์)',h:'pages/bookings.html#queue'}]},
  {k:'pos',ic:'receipt',t:'ชำระเงิน / ออกบิล',h:'pages/pos.html'},
  {k:'schedule',ic:'flow',t:'ตารางงานหมอนวด',h:'pages/schedule.html'},
  {k:'customers',ic:'users',t:'ลูกค้า',h:'pages/customers.html'},
  {k:'services',ic:'spa',t:'บริการ & คอร์ส',h:'pages/services.html'},
  {k:'staff',ic:'badge',t:'หมอนวด / พนักงาน',h:'pages/staff.html'},
  {k:'finance',ic:'wallet',t:'การเงิน',h:'pages/finance.html',
    sub:[{t:'ภาพรวมการเงิน',h:'pages/finance.html'},{t:'ใบเสร็จ / บิล',h:'pages/finance.html#bills'},{t:'รายรับ - รายจ่าย',h:'pages/finance.html#flow'}]},
  {k:'packages',ic:'tag',t:'แพ็กเกจ & โปรโมชัน',h:'pages/packages.html'},
  {k:'inventory',ic:'box',t:'สต็อกสินค้า',h:'pages/inventory.html'},
  {k:'roles',ic:'shield',t:'สิทธิ์การใช้งาน (Roles)',h:'pages/roles.html'},
  {k:'reports',ic:'chart',t:'รายงาน',h:'pages/reports.html'},
  {k:'logs',ic:'logs',t:'Logs & กิจกรรม',h:'pages/logs.html'},
  {k:'settings',ic:'gear',t:'ตั้งค่า',h:'pages/settings.html'},
  {k:'subscription',ic:'gem',t:'แพ็กเกจการใช้งาน',h:'pages/subscription.html'},
];

/* ============================================================
   เมนู & หน้าแรกตามบทบาท (Role-based UI)
   หลักการ: แต่ละ role เห็น “หน้าที่ออกแบบมาเพื่องานตัวเอง” ไม่ใช่หน้าเดียวซ่อนปุ่ม
   - Owner     → ทุกเมนู · หน้าแรก index.html (การเงินเต็ม)
   - Manager   → ทุกเมนูยกเว้น สิทธิ์/แพ็กเกจ · index.html จะซ่อนกำไร/รายเดือน + โชว์สต็อกใกล้หมดแทน
   - Reception → หน้าแรก pages/front-desk.html (จอต้อนรับ: คิว+นัด+ปุ่มลัด)
   - Therapist → หน้าเดียว pages/my-queue.html (งานของตัวเองเท่านั้น)
   - Cashier   → หน้าแรก pages/pos.html (POS + คิวรอชำระ)
   TODO(Backend): role อ่านจาก JWT (user.roles[0]) — ฝั่ง server ต้องบังคับซ้ำทุก endpoint ด้วย
   ============================================================ */
const ROLE_KEY=(function(){const u=curUser();return (u.roles&&u.roles[0])||u.role||'Owner';})();
window.ROLE_KEY=ROLE_KEY;
const NAV_EXTRA={
  frontdesk:{k:'frontdesk',ic:'home',t:'หน้าจอต้อนรับ (Front Desk)',h:'pages/front-desk.html'},
  myqueue:{k:'myqueue',ic:'home',t:'คิวของฉัน',h:'pages/my-queue.html'},
};
const ROLE_HOME={Owner:'index.html',Manager:'index.html',Reception:'pages/front-desk.html',Therapist:'pages/my-queue.html',Cashier:'pages/pos.html'};
const ROLE_MENU={
  Owner:null, // ทุกเมนู
  Manager:['dashboard','bookings','pos','schedule','customers','services','staff','finance','packages','inventory','reports','logs','settings'],
  Reception:['frontdesk','bookings','pos','schedule','customers','services'],
  Therapist:['myqueue'],
  Cashier:['pos','bookings'],
};
function navList(){
  const keys=ROLE_MENU[ROLE_KEY];
  if(!keys)return NAV;
  return keys.map(k=>NAV_EXTRA[k]||NAV.find(n=>n.k===k)).filter(Boolean);
}
/* เข้า index.html แต่บทบาทมีหน้าแรกเฉพาะ → พาไปหน้าของตัวเอง */
(function(){
  const home=ROLE_HOME[ROLE_KEY]||'index.html';
  const cur=location.pathname.split('/').pop()||'index.html';
  if(cur==='index.html'&&home!=='index.html')location.replace(B+home);
})();

function navHtml(){
  return navList().map(n=>{
    const act=n.k===PAGE?' active':'';
    const hasSub=n.sub&&n.k===PAGE;
    const sub=n.sub?`<div class="nav-sub${hasSub?' show':''}">${n.sub.map(s=>`<a href="${B}${s.h}">${s.t}</a>`).join('')}</div>`:'';
    return `<a href="${B}${n.h}" class="nav-item${act}${hasSub?' open':''}">${svg(n.ic)}<span>${n.t}</span>${n.sub?`<span class="chev" onclick="return BS.navToggle(event,this)" title="เปิด/ปิดเมนูย่อย">${svg('chev')}</span>`:''}</a>${sub}`;
  }).join('');
}

/* ---------- sidebar ---------- */
function sidebar(){
  return `<aside class="side">
    <div class="side-brand">
      <div class="mark"><svg viewBox="0 0 24 24">${I.lotus}</svg></div>
      <div><div class="name">JavaXd</div><div class="sub">Massage &amp; Spa</div></div>
    </div>
    <nav class="nav">${navHtml()}</nav>
    ${ROLE_KEY==='Owner'?`<a class="side-card upsell" href="${B}pages/subscription.html">
      <div class="up-row"><div class="ic">${svg('gem')}</div><span class="plan-now">แพ็กเกจ เริ่มต้น</span></div>
      <h4>ปลดล็อกศักยภาพเต็มร้าน</h4>
      <p>รับชำระผ่านพร้อมเพย์ · จองออนไลน์ · รายงานเชิงลึก</p>
      <span class="up-btn">${svg('gem')} อัปเกรดแพ็กเกจ</span>
    </a>`:''}
    <div class="side-user" onclick="BS.accountPanel()" title="บัญชีผู้ใช้">
      ${av(curName(),36,true,curUser().avatarUrl)}
      <div><div class="nm">${curName()}</div><div class="rl">${curRole()}</div></div>
      <span class="mr">${svg('chev')}</span>
    </div>
  </aside>`;
}

/* ---------- central mock database (ใช้ร่วมทุกหน้า — ภายหลังแทนที่ด้วยข้อมูลจาก API) ---------- */
window.DB={
  customers:[
    {name:'คุณเมย์ ลีลาวดี',phone:'091-222-3344',tier:'สมาชิกคนสำคัญ',visits:42},
    {name:'คุณวิภา ทองคำ',phone:'087-111-2233',tier:'สมาชิกสะสมแต้ม',visits:28},
    {name:'คุณริรินทร์ ศรีสุข',phone:'081-234-5678',tier:'สมาชิกสะสมแต้ม',visits:17},
    {name:'คุณดารา แสงทอง',phone:'083-101-2020',tier:'ทั่วไป',visits:9},
    {name:'คุณวรพล ธนะวัฒน์',phone:'089-555-7788',tier:'ทั่วไป',visits:6},
    {name:'คุณณัฐชา พึ่งพร',phone:'086-909-1122',tier:'สมาชิกสะสมแต้ม',visits:14},
  ],
  staff:[
    {name:'อ้อม',role:'Senior Therapist'},{name:'นุ่น',role:'Therapist'},{name:'ใบเตย',role:'Therapist'},
    {name:'ปลา',role:'Therapist'},{name:'ฟ้า',role:'Junior Therapist'},{name:'บัว',role:'Reception'},
  ],
  bookings:[
    {id:'B-2401',cust:'คุณริรินทร์ ศรีสุข',svc:'นวดไทย 60 นาที',time:'10:30',th:'อ้อม'},
    {id:'B-2402',cust:'คุณวรพล ธนะวัฒน์',svc:'นวดน้ำมัน 90 นาที',time:'11:00',th:'นุ่น'},
    {id:'B-2403',cust:'คุณณัฐชา พึ่งพร',svc:'ประคบสมุนไพร 60 นาที',time:'11:30',th:'ฟ้า'},
    {id:'B-2404',cust:'Walk-in',svc:'นวดเท้า 45 นาที',time:'11:45',th:'ใบเตย'},
    {id:'B-2405',cust:'คุณกฤษฎา มั่นคง',svc:'คอบ่าไหล่ 45 นาที',time:'12:00',th:'ปลา'},
  ],
  notifications:[
    {dot:'#22b07d',html:'<b>คุณริรินทร์</b> เช็คอินแล้ว',time:'10:30 น.',href:'pages/bookings.html#queue'},
    {dot:'#f5a623',html:'ใกล้ถึงเวลานัด <b>คุณวรพล</b>',time:'10:55 น.',href:'pages/bookings.html'},
    {dot:'#3b9bff',html:'มีการจองใหม่จาก Line OA',time:'09:40 น.',href:'pages/bookings.html'},
    {dot:'#c2c7d6',html:'คอร์สหมดอายุของ <b>คุณเมย์</b>',time:'เมื่อวาน',href:'pages/customers.html'},
    {dot:'#ef5d6b',html:'สต็อกน้ำมันนวดใกล้หมด',time:'เมื่อวาน',href:'pages/inventory.html'},
  ],
};

/* ---------- topbar ---------- */
function topbar(title){
  return `<header class="topbar">
    <button class="icon-btn ham" onclick="document.body.classList.toggle('side-open')" title="เปิดเมนู">${svg('menu')}</button>
    <h1>${title}</h1>
    <div class="search" style="position:relative">${svg('search')}<input id="gsearch" placeholder="ค้นหาลูกค้า การจอง หมอนวด หรือเมนู..." autocomplete="off"><div class="gs-drop" id="gsdrop"></div></div>
    <div class="top-actions">
      ${['Therapist','Cashier'].includes(ROLE_KEY)?'':`<button class="btn-primary" onclick="BS.openBooking()">${svg('plus')} สร้างการจอง</button>`}
      <button class="icon-btn" id="bellBtn" onclick="BS.notifPanel()">${svg('bell')}<span class="dot">5</span></button>
      <button class="icon-btn" onclick="BS.chatPanel()">${svg('chat')}</button>
      <span style="cursor:pointer;display:inline-flex" onclick="BS.accountPanel()" title="บัญชีผู้ใช้">${av(curName(),42,true,curUser().avatarUrl)}</span>
    </div>
  </header>`;
}

/* ---------- booking modal ---------- */
function bookingModal(){
  return `<div class="modal-bg" id="bkModal">
   <div class="modal">
    <div class="modal-h"><h3 id="bkTitle">สร้างการจอง / รับลูกค้า</h3><button class="x" onclick="BS.closeBooking()">${svg('x')}</button></div>
    <div class="modal-b">
      <div class="seg-full" id="bkType" style="margin-bottom:14px">
        <button class="on" data-t="booking" type="button">จองล่วงหน้า</button>
        <button data-t="walkin" type="button">Walk-in (เข้าคิวเลย)</button>
      </div>
      <div class="field"><label>ลูกค้า</label>
        <input id="bkCustSearch" placeholder="ค้นหาลูกค้าเดิม (ชื่อ/เบอร์) หรือพิมพ์ชื่อลูกค้าใหม่" autocomplete="off">
        <div id="bkCustRes"></div>
      </div>
      <div class="grid2" id="bkNewCust">
        <div class="field" style="margin-bottom:0"><label>เบอร์โทร <span class="sub" style="font-weight:400;font-size:11px">(ลูกค้าใหม่)</span></label><input id="bkPhone" placeholder="08x-xxx-xxxx"></div>
        <label class="flex ac g8" style="align-self:end;padding:10px 0;cursor:pointer"><input id="bkMember" type="checkbox" checked style="width:17px;height:17px;accent-color:var(--brand)"><span style="font-size:13px">สมัครเป็นสมาชิก (เก็บประวัติ)</span></label>
      </div>
      <div class="grid2">
        <div class="field"><label>หมวดหมู่บริการ</label><select id="bkCat"><option value="">ทุกหมวด</option></select></div>
        <div class="field"><label>บริการ</label><select id="bkSvc"><option value="">กำลังโหลด...</option></select></div>
      </div>
      <div class="field"><label>หมอนวด</label><select id="bkTh"><option value="">เลือกอัตโนมัติ (ระบบจัดให้)</option></select></div>
      <div class="grid2" id="bkWhen">
        <div class="field"><label>วันที่</label><input type="date" id="bkDate"></div>
        <div class="field"><label>เวลา</label><input type="time" id="bkTime" value="14:00"></div>
      </div>
      <div id="bkErr" style="display:none;color:var(--red);font-size:12.5px;margin-top:4px"></div>
    </div>
    <div class="modal-f">
      <button class="btn btn-ghost" onclick="BS.closeBooking()">ยกเลิก</button>
      <button class="btn btn-pri" id="bkConfirm" onclick="BS.confirmBooking()">${svg('check')} <span id="bkConfirmTxt">ยืนยันการจอง</span></button>
    </div>
   </div>
  </div>`;
}

/* ---------- mount ---------- */
const title = document.body.getAttribute('data-title') || 'แดชบอร์ด';
const content = document.getElementById('page') ? document.getElementById('page').innerHTML : '';
document.body.innerHTML =
  `<div class="app">${sidebar()}<div class="scrim" onclick="document.body.classList.remove('side-open')"></div><div class="main">${topbar(title)}<div class="content" id="content">${content}</div>`+
  `<footer class="ft">© 2024 JavaXd Massage &amp; Spa. สงวนลิขสิทธิ์ · เวอร์ชัน 1.0.0</footer></div></div>`+
  bookingModal()+
  `<div class="modal-bg" id="genModal"><div class="modal" id="genCard"></div></div>`+
  `<div id="printArea"></div>`+
  `<div class="toast" id="toast"></div>`;

/* chip toggles in modal */
document.addEventListener('click',e=>{
  const c=e.target.closest('.chip-sel'); if(c){c.classList.toggle('on')}
});

/* ---------- public API ---------- */
let toastT;
window.BS={
  _bkType:'booking', _bkCust:null,
  async openBooking(opts){
    document.getElementById('bkModal').classList.add('show');
    const err=document.getElementById('bkErr');if(err)err.style.display='none';
    const dt=document.getElementById('bkDate');if(dt&&!dt.value)dt.value=(d=>new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10))(new Date());
    // reset customer pick
    BS._bkCust=null;const cs=document.getElementById('bkCustSearch');if(cs)cs.value='';
    const cr=document.getElementById('bkCustRes');if(cr)cr.innerHTML='';
    const nc=document.getElementById('bkNewCust');if(nc)nc.style.display='grid';
    const ph=document.getElementById('bkPhone');if(ph)ph.value='';
    // ตั้งประเภทเริ่มต้น (booking ปกติ; pages เรียก openBooking({type:'walkin'}) ได้)
    BS._setBkType((opts&&opts.type)||'booking');
    // wire type toggle + customer search (ครั้งเดียว)
    const seg=document.getElementById('bkType');
    if(seg&&!seg.dataset.wired){seg.dataset.wired='1';seg.querySelectorAll('button').forEach(b=>b.onclick=()=>BS._setBkType(b.dataset.t));}
    if(cs&&!cs.dataset.wired){cs.dataset.wired='1';let tmr;
      cs.addEventListener('input',()=>{BS._bkCust=null;const nc2=document.getElementById('bkNewCust');if(nc2)nc2.style.display='grid';
        clearTimeout(tmr);const q=cs.value.trim();const box=document.getElementById('bkCustRes');
        if(q.length<2){box.innerHTML='';return;}
        tmr=setTimeout(async()=>{try{const r=await API.get('/customer?search='+encodeURIComponent(q)+'&pageSize=6');const items=(r&&r.items)||[];
          box.innerHTML=items.length?items.map(c=>`<div class="bk-cust-hit" data-id="${c.id}" data-name="${(c.displayName||'').replace(/"/g,'&quot;')}" style="padding:8px 11px;border:1px solid var(--line);border-radius:9px;margin-top:5px;cursor:pointer;display:flex;justify-content:space-between"><span style="font-weight:600;font-size:13px">${c.displayName}</span><span class="sub" style="font-size:11.5px">${c.phone||''} · ${c.totalVisits||0} ครั้ง</span></div>`).join(''):'<div class="sub" style="font-size:12px;padding:5px 0">ไม่พบลูกค้าเดิม — จะสร้างเป็นลูกค้าใหม่</div>';
          box.querySelectorAll('.bk-cust-hit').forEach(el=>el.onclick=()=>{BS._bkCust={id:el.dataset.id,name:el.dataset.name};cs.value=el.dataset.name;box.innerHTML='<div style="color:#178a61;font-size:12px;padding:5px 0">✓ ลูกค้าเดิม: '+el.dataset.name+'</div>';document.getElementById('bkNewCust').style.display='none';});
        }catch(e){}},250);});
    }
    // โหลดบริการ + หมอนวดจริง
    try{
      if(window.API){
        const svcSel=document.getElementById('bkSvc'),thSel=document.getElementById('bkTh'),catSel=document.getElementById('bkCat');
        if(svcSel&&svcSel.dataset.loaded!=='1'){
          const svc=(await API.get('/services')||[]).filter(s=>s.isActive!==false);
          BS._bkSvcs=svc;
          // หมวดหมู่ → กรองรายการบริการตามหมวดที่เลือก
          const cats=[...new Map(svc.filter(s=>s.category).map(s=>[s.category.id,s.category.name]))];
          if(catSel)catSel.innerHTML='<option value="">ทุกหมวด</option>'+cats.map(c=>`<option value="${c[0]}">${c[1]}</option>`).join('');
          const fill=(catId)=>{const list=svc.filter(s=>!catId||(s.category&&s.category.id===catId));
            svcSel.innerHTML=list.map(s=>`<option value="${s.id}">${s.name} · ${s.durationMins} น. · ${s.price} ฿</option>`).join('')||'<option value="">ไม่มีบริการในหมวดนี้</option>';};
          fill('');
          if(catSel)catSel.onchange=()=>fill(catSel.value);
          svcSel.dataset.loaded='1';
        }
        if(thSel&&thSel.dataset.loaded!=='1'){
          thSel.dataset.loaded='1';
          // หมอแต่ละคน ว่าง/ไม่ว่างเพราะอะไร ถึงกี่โมง — คนไม่ว่างเลือกไม่ได้ (เช็คตามวัน/เวลา/บริการที่เลือกจริง)
          BS._refreshBkTh=async function(){
            try{
              const d=document.getElementById('bkDate'),tm=document.getElementById('bkTime'),sv=document.getElementById('bkSvc');
              const isWalk=BS._bkType==='walkin';
              const qs='?serviceId='+encodeURIComponent(sv&&sv.value||'')+(isWalk?'':'&date='+(d&&d.value||'')+'&time='+(tm&&tm.value||''));
              const avail=await API.get('/walk-in/therapist-availability'+qs)||[];
              const cur=thSel.value;
              thSel.innerHTML='<option value="">เลือกอัตโนมัติ (ระบบจัดให้)</option>'+avail.map(t=>{
                if(t.free)return `<option value="${t.id}">✓ ${t.displayName} · ว่าง</option>`;
                const why=(t.reason||'ไม่ว่าง')+(t.freeAt?' · ว่าง ~'+t.freeAt+' น.':'');
                return `<option value="${t.id}" disabled>✕ ${t.displayName} · ${why}</option>`;
              }).join('');
              if(cur&&[...thSel.options].some(o=>o.value===cur&&!o.disabled))thSel.value=cur;
            }catch(e){}
          };
          ['bkDate','bkTime','bkSvc'].forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener('change',()=>BS._refreshBkTh());});
          await BS._refreshBkTh();
        } else if(BS._refreshBkTh){await BS._refreshBkTh();}
      }
    }catch(e){console.error('booking opts',e);}
  },
  _setBkType(t){BS._bkType=t;
    document.querySelectorAll('#bkType button').forEach(b=>b.classList.toggle('on',b.dataset.t===t));
    const when=document.getElementById('bkWhen');if(when)when.style.display=t==='walkin'?'none':'grid';
    const title=document.getElementById('bkTitle');if(title)title.textContent=t==='walkin'?'รับลูกค้า Walk-in (เข้าคิว)':'สร้างการจองล่วงหน้า';
    const ct=document.getElementById('bkConfirmTxt');if(ct)ct.textContent=t==='walkin'?'เข้าคิวเลย':'ยืนยันการจอง';
  },
  async confirmBooking(){
    const err=document.getElementById('bkErr');const show=m=>{if(err){err.textContent=m;err.style.display='';}};
    const isWalk=BS._bkType==='walkin';
    const name=(document.getElementById('bkCustSearch').value||'').trim();
    const phone=(document.getElementById('bkPhone').value||'').trim();
    const asMember=document.getElementById('bkMember').checked;
    const serviceId=document.getElementById('bkSvc').value;
    const therapistId=document.getElementById('bkTh').value;
    const date=document.getElementById('bkDate').value;
    const time=document.getElementById('bkTime').value;
    if(!BS._bkCust&&!name){show('กรุณาเลือกหรือกรอกชื่อลูกค้า');return;}
    // กันข้อมูลขยะ: พิมพ์เบอร์โทรในช่องชื่อ → จะกลายเป็นลูกค้าชื่อ "086..." ในฐานข้อมูล
    if(!BS._bkCust&&/^[\d\s\-+().]{3,}$/.test(name)){show('ช่องนี้ต้องเป็น "ชื่อลูกค้า" — ตัวเลขที่พิมพ์ดูเหมือนเบอร์โทร (ใส่เบอร์ในช่องด้านล่าง)');return;}
    if(!serviceId){show('กรุณาเลือกบริการ');return;}
    if(!isWalk&&(!date||!time)){show('กรุณาเลือกวันและเวลา');return;}
    const btn=document.getElementById('bkConfirm');btn.disabled=true;const old=btn.innerHTML;btn.innerHTML=svg('clock')+' กำลังบันทึก...';
    try{
      // หา/สร้างลูกค้า
      let customerId=BS._bkCust&&BS._bkCust.id;
      if(!customerId){
        try{const r=await API.get('/customer?search='+encodeURIComponent(phone||name)+'&pageSize=5');const hit=((r&&r.items)||[]).find(c=>(phone&&c.phone===phone)||c.displayName===name);if(hit)customerId=hit.id;}catch{}
      }
      if(!customerId){
        // สมาชิก = เก็บเบอร์ + ประวัติ · ไม่สมัคร = บันทึกชื่อพอใช้คิว
        const c=await API.post('/customer',{displayName:name,phone:asMember?(phone||null):null,notes:null});customerId=c.id;
      }
      if(isWalk){
        await API.post('/walk-in',{customerId,items:[{serviceId,therapistId:therapistId||null,roomId:null,sortOrder:0}],notes:null});
        BS.closeBooking();BS.toast('รับ '+(BS._bkCust?BS._bkCust.name:name)+' เข้าคิวแล้ว','flow');
      } else {
        await API.post('/booking',{customerId,bookingDate:date,startTime:time.length===5?time+':00':time,
          items:[{serviceId,therapistId:therapistId||null,roomId:null,therapistSelectionMode:therapistId?0:1,sortOrder:0}]});
        BS.closeBooking();BS.toast('สร้างการจองให้ '+(BS._bkCust?BS._bkCust.name:name)+' เรียบร้อย');
      }
      // reset
      document.getElementById('bkCustSearch').value='';document.getElementById('bkPhone').value='';BS._bkCust=null;
      if(typeof loadBookings==='function')loadBookings();
      if(typeof loadKanban==='function')loadKanban();
      if(typeof loadQueue==='function')loadQueue();
      if(typeof loadDashboardReal==='function')loadDashboardReal();
    }catch(e){show('บันทึกไม่สำเร็จ: '+e.message);}
    btn.disabled=false;btn.innerHTML=old;
  },
  closeBooking(){document.getElementById('bkModal').classList.remove('show')},
  toast(msg,ic){
    const t=document.getElementById('toast');
    t.innerHTML=svg(ic||'check')+`<span>${msg}</span>`;
    t.classList.add('show');clearTimeout(toastT);
    toastT=setTimeout(()=>t.classList.remove('show'),2400);
  },
  /* generic modal — pass {title, sub, body, foot, w} */
  modal(o){
    const card=document.getElementById('genCard');
    card.style.maxWidth=(o.w||560)+'px';
    card.innerHTML=
      `<div class="modal-h"><div><h3>${o.title||''}</h3>${o.sub?`<div class="modal-sub">${o.sub}</div>`:''}</div>`+
      `<button class="x" onclick="BS.closeModal()">${svg('x')}</button></div>`+
      `<div class="modal-b"${o.flush?' style="padding:0"':''}>${o.body||''}</div>`+
      (o.foot?`<div class="modal-f">${o.foot}</div>`:'');
    document.getElementById('genModal').classList.add('show');
    if(o.onopen)setTimeout(o.onopen,30);
  },
  closeModal(){document.getElementById('genModal').classList.remove('show')},
  /* พับ/กางเมนูย่อยใน sidebar (คลิกลูกศร) */
  navToggle(e,el){
    e.preventDefault();e.stopPropagation();
    const a=el.closest('.nav-item');a.classList.toggle('open');
    const sub=a.nextElementSibling;
    if(sub&&sub.classList.contains('nav-sub'))sub.classList.toggle('show');
    return false;
  },
  fmtTHB(n){return Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})},
  /* tax-invoice / receipt preview (prices are VAT-inclusive) */
  invoiceData:null,
  invoice(d){
    BS.invoiceData=d;
    const items=d.items||[];
    const gross=items.reduce((s,i)=>s+i.qty*i.price,0);
    const disc=d.discount?d.discount.amount:0;
    const total=gross-disc;
    const net=total/1.07, vat=total-net;
    const paid=d.paid!=null?d.paid:total;
    const change=Math.max(0,paid-total);
    const rows=items.map(i=>`<tr><td>${i.name}${i.sub?`<div class="ln-sub">${i.sub}</div>`:''}</td><td class="num">${i.qty}</td><td class="num">${BS.fmtTHB(i.price)}</td><td class="num">${BS.fmtTHB(i.qty*i.price)}</td></tr>`).join('');
    const sheet=`<div class="invoice-sheet" id="invSheet">
      <div class="inv-top">
        <div class="inv-brand"><div class="inv-logo">${svg('lotus')}</div>
          <div><div class="inv-shop">JavaXd Massage &amp; Spa</div>
          <div class="inv-meta">123/45 ถนนสุขุมวิท คลองเตย กรุงเทพฯ 10110<br>โทร. 02-123-4567 · เลขประจำตัวผู้เสียภาษี 0-1055-12345-67-8</div></div></div>
        <div class="inv-type">${d.full?'ใบกำกับภาษี/ใบเสร็จรับเงิน':'ใบเสร็จรับเงิน<br><span>(ใบกำกับภาษีอย่างย่อ)</span>'}</div>
      </div>
      <div class="inv-info">
        <div><span>เลขที่</span><b>${d.no||'INV-0000'}</b></div>
        <div><span>วันที่</span><b>${d.date||'-'}</b></div>
        <div><span>แคชเชียร์</span><b>${d.cashier||'บัว'}</b></div>
        <div><span>ลูกค้า</span><b>${d.customer||'ลูกค้าทั่วไป'}</b></div>
      </div>
      <table class="inv-tbl"><thead><tr><th>รายการ</th><th class="num">จำนวน</th><th class="num">ราคา</th><th class="num">รวม</th></tr></thead><tbody>${rows}</tbody></table>
      <div class="inv-sum">
        <div class="r"><span>มูลค่าก่อนภาษี</span><b>${BS.fmtTHB(net)}</b></div>
        ${disc?`<div class="r"><span>ส่วนลด${d.discount.label?` (${d.discount.label})`:''}</span><b class="t-red">-${BS.fmtTHB(disc)}</b></div>`:''}
        <div class="r"><span>ภาษีมูลค่าเพิ่ม 7%</span><b>${BS.fmtTHB(vat)}</b></div>
        <div class="r total"><span>ยอดสุทธิ</span><b>฿ ${BS.fmtTHB(total)}</b></div>
        <div class="r"><span>รับชำระโดย</span><b>${d.method||'เงินสด'}</b></div>
        <div class="r"><span>รับเงิน</span><b>${BS.fmtTHB(paid)}</b></div>
        ${change?`<div class="r"><span>เงินทอน</span><b>${BS.fmtTHB(change)}</b></div>`:''}
      </div>
      <div class="inv-foot">
        <div class="inv-qr">${svg('qr')}<span>สแกนรับใบเสร็จ<br>ดิจิทัล</span></div>
        <div class="inv-thanks">ขอบคุณที่ใช้บริการ 🙏<br><b>JavaXd Massage &amp; Spa</b><div class="inv-note">เอกสารออกโดยระบบ JavaXd POS</div></div>
      </div>
    </div>`;
    BS.modal({
      title:'ตัวอย่างใบเสร็จก่อนพิมพ์', sub:'ตรวจสอบรายการให้ถูกต้องก่อนพิมพ์หรือดาวน์โหลด', w:520, flush:true,
      body:`<div class="inv-wrap">${sheet}</div>`,
      foot:`<label class="inv-chk"><input type="checkbox" id="fullTax"> ออกใบกำกับภาษีเต็มรูปแบบ</label>
        <button class="btn btn-ghost" onclick="BS.closeModal()">ปิด</button>
        <button class="btn btn-ghost" onclick="BS.toast('ส่งใบเสร็จทาง Line แล้ว','line')">${svg('line')} ส่ง Line</button>
        <button class="btn btn-pri" onclick="BS.printInvoice()">${svg('print')} พิมพ์ / ดาวน์โหลด</button>`
    });
    setTimeout(()=>{const c=document.getElementById('fullTax');if(c)c.onchange=()=>{const dd=Object.assign({},BS.invoiceData,{full:c.checked});BS.invoice(dd);setTimeout(()=>{const n=document.getElementById('fullTax');if(n){n.checked=c.checked}},40)}},40);
  },
  printInvoice(){
    const s=document.getElementById('invSheet');
    if(!s)return;
    document.getElementById('printArea').innerHTML='<div class="invoice-sheet print">'+s.innerHTML+'</div>';
    BS.toast('กำลังเตรียมไฟล์สำหรับพิมพ์...');
    setTimeout(()=>window.print(),300);
  },
  /* ---------- การ์ดสถิติคลิกได้ (ใช้ซ้ำทุกหน้า) — ส่ง defs ตามลำดับการ์ด ---------- */
  statRow(l,v,c){return `<div class="flex ac jb" style="padding:8px 0;border-bottom:1px dashed var(--line-2)"><span style="font-size:13px;color:var(--ink-2)">${l}</span><b style="font-weight:600;${c?'color:'+c:''}">${v}</b></div>`},
  statDetails(defs){
    document.querySelectorAll('.stat-grid .stat').forEach((el,i)=>{
      const d=defs[i];if(!d||el.onclick)return;
      el.style.cursor='pointer';el.title='คลิกดูรายละเอียด';
      el.onclick=()=>BS.modal({title:d.title,sub:d.sub||'ข้อมูลตัวอย่าง · ข้อมูลจริงจะมาจาก API',w:d.w||430,
        body:d.body||(d.rows||[]).map(r=>BS.statRow(r[0],r[1],r[2])).join(''),
        foot:d.foot||`<button class="btn btn-pri" onclick="BS.closeModal()">ปิด</button>`});
    });
  },
  /* ---------- บัญชีผู้ใช้ (อวาตาร์มุมขวาบน / ล่างซ้าย sidebar) ---------- */
  accountPanel(){
    const B=window.BASE||'';
    const u=(window.API&&API.getUser&&API.getUser())||{};
    const nm=u.displayName||'ผู้ใช้';
    const role=roleThai((u.roles&&u.roles[0])||u.role);
    BS.modal({title:'บัญชีผู้ใช้',sub:'ผู้ที่ล็อกอินอยู่ขณะนี้',w:400,
      body:`<div class="flex ac g12" style="margin-bottom:16px">${av(nm,52,true,u.avatarUrl)}<div style="flex:1"><div style="font-weight:700;font-size:16px">${nm}</div><div class="sub" style="font-size:12.5px">${role}${u.username?' · @'+u.username:''}</div></div><span class="badge ${u.hasLine?'b-green':'b-gray'}">${u.hasLine?'✓ ผูก LINE แล้ว':'ยังไม่ผูก LINE'}</span></div>
        ${[].concat(
          ['แก้ไขโปรไฟล์ และรหัสผ่าน|edit|prof'],
          (u.hasLine?[]:['ผูก LINE ของฉัน (รับแจ้งเตือนคิว)|line|linkline']),
          ['สิทธิ์การใช้งานของฉัน|shield|perm','ประวัติการใช้งาน (Logs)|logs|logs'],
          ((u.roles&&u.roles[0])==='Owner'?['สำรองข้อมูลทั้งร้าน (ดาวน์โหลด)|down|backup']:[])
        ).map(x=>{const[t,ic,act]=x.split('|');const click=act==='logs'?`location.href='${B}pages/logs.html'`:act==='perm'?`BS.myPermissions()`:act==='linkline'?`BS.linkMyLine()`:act==='backup'?`BS.downloadBackup()`:`BS.editProfile()`;return `<div class="notif" style="cursor:pointer;align-items:center" onclick="${act==='linkline'||act==='perm'?'':'BS.closeModal();'}${click}"><span class="bi-ic" style="width:34px;height:34px;border-radius:10px;background:${act==='linkline'?'#06c75522':'#eef0f6'};color:${act==='linkline'?'#06c755':'var(--ink-2)'};display:grid;place-items:center">${svg(ic)}</span><div class="tx" style="margin-left:10px"><div style="font-weight:600">${t}</div></div><span style="margin-left:auto;color:var(--ink-3)">${svg('chevR')}</span></div>`}).join('')}`,
      foot:`<button class="btn btn-ghost" style="color:var(--red);border-color:#f4ccd0;margin-right:auto" onclick="BS.doLogout()">ออกจากระบบ</button><button class="btn btn-pri" onclick="BS.closeModal()">ปิด</button>`});
  },
  /* ---------- ผูก LINE ของตัวเอง (QR) ---------- */
  async linkMyLine(){
    const u=(window.API&&API.getUser&&API.getUser())||{};
    if(!u.id){BS.toast('ไม่พบบัญชีผู้ใช้','x');return;}
    BS.modal({title:'ผูก LINE ของฉัน',sub:'สแกน QR นี้เพื่อรับแจ้งเตือนคิวทาง LINE',w:420,body:'<div style="padding:30px;text-align:center;color:var(--ink-3)">กำลังสร้างลิงก์...</div>'});
    let res;try{res=await API.post('/auth/link-token',{userId:u.id});}catch(e){BS.toast('สร้างลิงก์ไม่สำเร็จ: '+e.message,'x');return;}
    const body=document.querySelector('#genCard .modal-b');
    body.innerHTML=`<div style="text-align:center"><div id="myQr" style="width:200px;height:200px;margin:6px auto 14px;display:grid;place-items:center;border:1px solid var(--line);border-radius:14px;background:#fff"></div>
      <div class="sub" style="font-size:12.5px">เปิดกล้องมือถือ/LINE สแกน → ล็อกอินด้วย LINE เพื่อผูกกับบัญชีของคุณ</div>
      <div style="margin-top:10px;font-size:11.5px;word-break:break-all"><a href="${res.liffUrl}" target="_blank" style="color:var(--brand-700)">${res.liffUrl}</a></div>
      <div id="myQrStatus" style="margin-top:10px;font-size:12.5px;color:var(--ink-3)">⏳ รอสแกน...</div></div>`;
    const draw=()=>{try{new QRCode(document.getElementById('myQr'),{text:res.liffUrl,width:188,height:188,correctLevel:QRCode.CorrectLevel.M});}catch(e){}};
    if(window.QRCode)draw();else{const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js';s.onload=draw;document.head.appendChild(s);}
    const poll=setInterval(async()=>{try{const st=await API.get('/auth/link-status/'+res.token);
      if(st.status==='linked'){clearInterval(poll);const el=document.getElementById('myQrStatus');if(el)el.innerHTML='<span style="color:#178a61;font-weight:600">✓ ผูก LINE สำเร็จ! ออกจากระบบแล้วเข้าใหม่เพื่ออัปเดต</span>';BS.toast('ผูก LINE สำเร็จ','check');}
      else if(st.status==='expired'){clearInterval(poll);}
    }catch(e){}},3000);
    const mo=new MutationObserver(()=>{if(!document.getElementById('genModal').classList.contains('show')){clearInterval(poll);mo.disconnect();}});mo.observe(document.getElementById('genModal'),{attributes:true});
  },
  /* ---------- สิทธิ์ของฉัน (อ่านอย่างเดียว) ---------- */
  async myPermissions(){
    const u=(window.API&&API.getUser&&API.getUser())||{};
    const role=(u.roles&&u.roles[0])||u.role||'';const COL={Owner:0,Manager:1,Reception:2,Therapist:3}[role];
    const MODN=['แดชบอร์ด','การจอง & คิว','จัดการลูกค้า','บริการ & คอร์ส','หมอนวด/พนักงาน','การเงิน & POS','แพ็กเกจ & โปรโมชัน','สต็อกสินค้า','รายงาน','ตั้งค่า & สิทธิ์'];
    const DEF=[[1,1,1,2],[1,1,1,2],[1,1,1,0],[1,1,2,0],[1,1,0,0],[1,1,2,0],[1,1,2,0],[1,1,1,0],[1,1,0,0],[1,0,0,0]];
    let M=DEF;try{const s=await API.get('/role/matrix');if(Array.isArray(s)&&s.length)M=s;}catch(e){}
    const lv=v=>v===1?['เข้าถึงได้','b-green']:v===2?['ดูอย่างเดียว','b-orange']:['ไม่มีสิทธิ์','b-gray'];
    const rows=MODN.map((n,i)=>{const v=COL==null?1:(M[i]&&M[i][COL]!=null?M[i][COL]:DEF[i][COL]);const t=lv(v);return `<div class="flex ac jb" style="padding:8px 0;border-bottom:1px solid var(--line);font-size:13px"><span>${n}</span><span class="badge ${t[1]}">${t[0]}</span></div>`}).join('');
    BS.modal({title:'สิทธิ์การใช้งานของฉัน',sub:roleThai(role),w:420,body:rows,foot:`<button class="btn btn-pri" onclick="BS.closeModal()">ปิด</button>`});
  },
  /* ---------- สำรองข้อมูลทั้งร้าน (Owner) — ดาวน์โหลดไฟล์ DB เก็บไว้ ---------- */
  async downloadBackup(){
    BS.toast('กำลังเตรียมไฟล์สำรองข้อมูล...');
    try{
      const res=await fetch(API.base+'/backup',{headers:{Authorization:'Bearer '+API.getToken()}});
      if(!res.ok){const d=await res.json().catch(()=>({}));throw new Error(d.detail||'HTTP '+res.status);}
      const blob=await res.blob();
      const a=document.createElement('a');a.href=URL.createObjectURL(blob);
      a.download='mms-backup-'+(d=>new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10))(new Date())+'.db';a.click();URL.revokeObjectURL(a.href);
      BS.toast('ดาวน์โหลดไฟล์สำรองแล้ว · เก็บไว้ที่ปลอดภัยนะ','check');
    }catch(e){BS.toast('สำรองไม่สำเร็จ: '+e.message,'x');}
  },
  doLogout(){
    BS.toast('ออกจากระบบ...');
    try{ sessionStorage.removeItem('lineLoginInit'); }catch(e){}
    try{ if(window.API&&API.logout)API.logout(); else { localStorage.removeItem('th_token');localStorage.removeItem('th_refresh');localStorage.removeItem('th_user');localStorage.removeItem('th_auth'); } }catch(e){}
    // เคลียร์ key สำรองให้หมด กัน guard ผ่าน
    ['th_token','th_refresh','refreshToken','th_user','th_auth','accessToken','mms-auth'].forEach(k=>{try{localStorage.removeItem(k)}catch(e){}});
    setTimeout(()=>location.href=(window.BASE||'')+'login.html',500);
  },
  /* ---------- แก้ไขโปรไฟล์ + รหัสผ่านตัวเอง ---------- */
  editProfile(){
    const u=(window.API&&API.getUser&&API.getUser())||{};
    BS.modal({title:'แก้ไขโปรไฟล์ของฉัน',sub:roleThai((u.roles&&u.roles[0])||u.role)+(u.username?' · @'+u.username:''),w:440,
      body:`<div class="grid2"><div class="field"><label>ชื่อที่แสดง</label><input id="meName" value="${(u.displayName||'').replace(/"/g,'&quot;')}"></div>
          <div class="field"><label>เบอร์โทร</label><input id="mePhone" value="${u.phone||''}" placeholder="08x-xxx-xxxx"></div></div>
        <div style="border-top:1px solid var(--line);margin:14px 0 4px;padding-top:14px"><b style="font-weight:600;font-size:13.5px">เปลี่ยนรหัสผ่าน</b> <span class="sub" style="font-size:12px">(เว้นว่างถ้าไม่เปลี่ยน)</span></div>
        ${u.hasPassword?`<div class="field"><label>รหัสผ่านเดิม</label><input id="meCur" type="password" placeholder="รหัสผ่านปัจจุบัน"></div>`:''}
        <div class="grid2"><div class="field"><label>รหัสผ่านใหม่</label><input id="meNew" type="password" placeholder="อย่างน้อย 6 ตัว"></div>
          <div class="field"><label>ยืนยันรหัสใหม่</label><input id="meNew2" type="password" placeholder="พิมพ์อีกครั้ง"></div></div>
        <div id="meErr" style="display:none;color:var(--red);font-size:12.5px"></div>`,
      foot:`<button class="btn btn-ghost" onclick="BS.closeModal()">ยกเลิก</button><button class="btn btn-pri" onclick="BS._saveProfile()">${svg('check')} บันทึก</button>`});
  },
  async _saveProfile(){
    const err=document.getElementById('meErr');const show=m=>{err.textContent=m;err.style.display='';};
    const name=document.getElementById('meName').value.trim();
    const phone=document.getElementById('mePhone').value.trim();
    const nw=document.getElementById('meNew').value, nw2=document.getElementById('meNew2').value;
    const cur=document.getElementById('meCur')?document.getElementById('meCur').value:'';
    // แตะช่องรหัสไหนก็ตาม (เดิม/ใหม่/ยืนยัน) = ตั้งใจเปลี่ยนรหัส → ต้องกรอกให้ครบ
    const wantPw=!!(nw||nw2||cur);
    const u0=API.getUser()||{};
    // ===== validate ทุกอย่างตอนกดยืนยัน แล้วค่อยบันทึก =====
    if(!name){show('กรุณากรอกชื่อที่แสดง');return;}
    if(wantPw){
      if(u0.hasPassword&&!cur){show('กรุณากรอกรหัสผ่านเดิม');return;}
      if(!nw){show('กรุณากรอกรหัสผ่านใหม่');return;}
      if(nw.length<6){show('รหัสผ่านใหม่ต้องยาวอย่างน้อย 6 ตัว');return;}
      if(!nw2){show('กรุณายืนยันรหัสผ่านใหม่อีกครั้ง');return;}
      if(nw!==nw2){show('รหัสผ่านใหม่กับช่องยืนยันไม่ตรงกัน');return;}
      if(cur&&cur===nw){show('รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสเดิม');return;}
    }
    try{
      // 1) เปลี่ยนรหัสผ่านก่อน (ถ้ารหัสเดิมผิด จะ error ก่อนแตะโปรไฟล์)
      if(wantPw){await API.post('/auth/change-password',{currentPassword:cur||null,newPassword:nw});}
      // 2) โปรไฟล์
      const r=await API.put('/auth/me',{displayName:name,phone:phone||null});
      try{const u=API.getUser()||{};u.displayName=r.displayName||name;u.phone=r.phone;localStorage.setItem('th_user',JSON.stringify(u));}catch(e){}
      BS.closeModal();BS.toast(wantPw?'บันทึกโปรไฟล์ + เปลี่ยนรหัสผ่านแล้ว':'บันทึกโปรไฟล์แล้ว','check');
      setTimeout(()=>location.reload(),700); // รีโหลดให้ชื่อ/role อัปเดตทุกที่
    }catch(e){show(e.message||'บันทึกไม่สำเร็จ');}
  },
  /* ---------- export modal (เลือกรูปแบบไฟล์ก่อนส่งออก) ---------- */
  exportModal(o){
    o=o||{};
    const fmts=o.formats||['Excel (.xlsx)','CSV (.csv)','PDF (.pdf)'];
    BS.modal({title:o.title||'ส่งออกข้อมูล',sub:o.sub||'เลือกรูปแบบไฟล์และช่วงข้อมูล',w:440,
      body:`<div class="field"><label>รูปแบบไฟล์</label>
          <div class="seg-full" id="expFmt">${fmts.map((f,i)=>`<button class="${i===0?'on':''}">${f}</button>`).join('')}</div></div>
        <div class="grid2"><div class="field"><label>ตั้งแต่วันที่</label><input type="date" value="2567-05-01"></div>
          <div class="field"><label>ถึงวันที่</label><input type="date" value="2567-05-17"></div></div>
        ${o.extra||''}`,
      foot:`<button class="btn btn-ghost" onclick="BS.closeModal()">ยกเลิก</button>
        <button class="btn btn-pri" onclick="BS.closeModal();BS.toast('กำลังสร้างไฟล์... ดาวน์โหลดอัตโนมัติเมื่อเสร็จ')">${svg('down')} ดาวน์โหลด</button>`});
    setTimeout(()=>document.querySelectorAll('#expFmt button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#expFmt button').forEach(x=>x.classList.remove('on'));b.classList.add('on')}),40);
  },
  /* ---------- global search ---------- */
  async gsearch(q){
    const drop=document.getElementById('gsdrop');
    q=q.trim();
    if(!q){drop.classList.remove('show');return}
    const B=window.BASE||'';
    const ql=q.toLowerCase();
    const hits=[];
    // เมนู (local)
    if(window.NAV)NAV.forEach(n=>{if(n.t.toLowerCase().includes(ql))hits.push({ic:n.ic,t:n.t,s:'เมนู',href:B+n.h})});
    // ลูกค้า + หมอนวด (จาก API จริง)
    const seq=++BS._gsSeq;
    try{
      const [cr,th]=await Promise.all([
        API.get('/customer?search='+encodeURIComponent(q)+'&pageSize=6').catch(()=>null),
        API.get('/therapist').catch(()=>null)
      ]);
      if(seq!==BS._gsSeq)return; // มีการพิมพ์ใหม่แล้ว
      ((cr&&cr.items)||[]).forEach(c=>hits.push({ic:'users',t:c.displayName,s:(c.phone||'')+' · ใช้บริการ '+(c.totalVisits||0)+' ครั้ง',href:B+'pages/customers.html'}));
      (th||[]).filter(t=>(t.displayName||'').toLowerCase().includes(ql)).forEach(t=>hits.push({ic:'badge',t:t.displayName,s:'หมอนวด'+(t.code?' · '+t.code:''),href:B+'pages/staff.html'}));
    }catch(e){}
    drop.innerHTML=hits.length
      ? hits.slice(0,8).map(h=>`<a class="gs-item" href="${h.href}"><span class="gi">${svg(h.ic)}</span><div><div class="gt">${h.t}</div><div class="gss">${h.s}</div></div></a>`).join('')
      : `<div class="gs-empty">ไม่พบ “${q}” ลองค้นชื่อลูกค้า หมอนวด หรือชื่อเมนู</div>`;
    drop.classList.add('show');
  },
  _gsSeq:0,
  /* ---------- notifications dropdown ---------- */
  async notifPanel(){
    const B=window.BASE||'';
    const iconColor=(et)=>{const t=et||'';if(t.includes('Booking'))return'#3b9bff';if(t.includes('WalkIn')||t.includes('Queue'))return'#f5a623';if(t.includes('Payment'))return'#22b07d';if(t.includes('Customer'))return'#8b5cf6';if(t.includes('Therapist'))return'#ec5f86';return'#6b7290';};
    BS.modal({title:'การแจ้งเตือน',sub:'กำลังโหลด...',w:420,body:'<div style="padding:24px;text-align:center;color:var(--ink-3)">กำลังโหลด...</div>'});
    let items=[];try{const r=await API.get('/timeline?pageSize=12');items=(r&&r.items)||[];}catch(e){}
    BS.modal({title:'การแจ้งเตือน',sub:items.length+' รายการล่าสุด',w:420,
      body:items.length?items.map(n=>{const actor=n.actorName||'ระบบ';return `<a class="notif" href="${B}pages/logs.html" style="display:flex;text-decoration:none;color:inherit"><span class="nd" style="background:${iconColor(n.entityType)}"></span><div class="tx"><div>${n.description||n.eventType||''} ${n.entityLabel?'<b>'+n.entityLabel+'</b>':''}</div><div class="tm">${actor} · ${API.fmtTime(n.createdAt)} ${API.fmtDate(n.createdAt)}</div></div></a>`}).join(''):'<div style="padding:20px;text-align:center;color:var(--ink-3);font-size:13px">ยังไม่มีการแจ้งเตือน</div>',
      foot:`<button class="btn btn-ghost" onclick="BS.closeModal();BS.toast('อ่านทั้งหมดแล้ว');var d=document.querySelector('#bellBtn .dot');if(d)d.style.display='none'">${svg('check')} อ่านทั้งหมด</button>
        <a class="btn btn-pri" href="${B}pages/logs.html" style="text-decoration:none">ดูประวัติทั้งหมด</a>`});
  },
  /* ---------- chat (Line OA) panel ---------- */
  chatPanel(){
    const chats=[['คุณเมย์ ลีลาวดี','ขอเลื่อนนัดพรุ่งนี้เป็น 14:00 ได้ไหมคะ','5 นาที',1],
      ['คุณวรพล ธนะวัฒน์','ถึงแล้วครับ รอหน้าร้าน','12 นาที',1],
      ['คุณดารา แสงทอง','ขอบคุณค่ะ บริการดีมาก','เมื่อวาน',0]];
    BS.modal({title:'ข้อความ Line OA',sub:'ตอบแชทลูกค้าจากหน้าร้าน',w:420,
      body:chats.map(c=>`<div class="notif" style="cursor:pointer" onclick="BS.toast('เปิดแชท ${c[0]} (เชื่อม Line OA จริงผ่าน API)','line')">${av(c[0],38)}<div class="tx" style="margin-left:10px"><div style="font-weight:600">${c[0]} ${c[3]?'<span class="badge b-green" style="margin-left:6px">ใหม่</span>':''}</div><div class="tm" style="color:var(--ink-2)">${c[1]}</div></div><span class="tm" style="margin-left:auto;align-self:flex-start">${c[2]}</span></div>`).join(''),
      foot:`<button class="btn btn-ghost" onclick="BS.closeModal()">ปิด</button><button class="btn btn-pri" onclick="BS.toast('เปิด Line Official Account Manager','line')">${svg('line')} เปิด Line OA</button>`});
  }
};
document.addEventListener('click',e=>{if(e.target.id==='bkModal')BS.closeBooking();if(e.target.id==='genModal')BS.closeModal();
  if(!e.target.closest('.search'))document.getElementById('gsdrop')&&document.getElementById('gsdrop').classList.remove('show');
  /* ทุก .seg สลับ active ได้อัตโนมัติ (ถ้าไม่มี handler เฉพาะ) */
  const sb=e.target.closest('.seg > button');
  if(sb&&!sb.onclick&&!sb.closest('#catseg')&&!sb.closest('#cycle')&&!sb.closest('#vseg')){
    sb.parentElement.querySelectorAll('button').forEach(x=>x.classList.remove('on'));sb.classList.add('on');
  }});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){BS.closeBooking();BS.closeModal()}});
setTimeout(()=>{const g=document.getElementById('gsearch');if(g)g.addEventListener('input',()=>BS.gsearch(g.value))},0);
// กันเลข mock ที่ฟิกใน HTML แวบขึ้นก่อนโหลด DB เสร็จ → ล้างเป็น placeholder ก่อน
try{
  document.querySelectorAll('.stat .val').forEach(el=>{el.dataset.ph='1';el.innerHTML='<span style="opacity:.2">—</span>';});
  document.querySelectorAll('.stat .trend').forEach(el=>el.remove());
  document.querySelectorAll('.stat .from').forEach(el=>{if(/[0-9]/.test(el.textContent))el.textContent='';});
}catch(e){}
/* แบนเนอร์โหมดเดโม่ — บัญชี demo เห็นชัดว่าข้อมูลจะถูกล้าง */
try{
  if(curUser().isDemo){
    const c=document.querySelector('.content');
    if(c)c.insertAdjacentHTML('afterbegin','<div style="background:linear-gradient(90deg,#fdf3e8,#fef9ec);border:1px solid #f0d9a8;color:#8a6d1a;border-radius:11px;padding:9px 14px;margin-bottom:14px;font-size:13px;font-weight:600">🧪 โหมดทดลองใช้ (Demo) — ข้อมูลที่คุณสร้างจะถูกล้างอัตโนมัติทุก 1 ชั่วโมง · ข้อมูลร้านจริงไม่ได้รับผลกระทบ</div>');
  }
}catch(e){}
if(window.PAGE_INIT)window.PAGE_INIT();

// ===== บังคับใช้สิทธิ์ตาม Role (ซ่อนเมนู + บล็อกหน้าที่ไม่มีสิทธิ์) =====
(async function enforcePermissions(){
  try{
    const u=(window.API&&API.getUser&&API.getUser())||{};
    const role=(u.roles&&u.roles[0])||u.role||'';
    if(role==='Owner')return; // เจ้าของร้านเข้าถึงทุกอย่าง
    const COL={Manager:1,Reception:2,Therapist:3,Cashier:4}[role];
    if(COL==null)return; // role ที่ไม่อยู่ใน matrix → ไม่จำกัด (กันล็อกตัวเองออก)
    // โมดูล → หน้า (ตรงกับตารางสิทธิ์ในหน้า roles · คอลัมน์ที่ASCII 5 = Cashier ใช้ DEF ฝั่ง client เท่านั้น)
    const MODS=[['index.html'],['bookings.html','schedule.html'],['customers.html'],['services.html'],
      ['staff.html'],['finance.html','pos.html'],['packages.html'],['inventory.html'],
      ['reports.html','logs.html'],['settings.html','roles.html','subscription.html']];
    const DEF=[[1,1,1,2,0],[1,1,1,2,2],[1,1,1,0,0],[1,1,2,0,0],[1,1,0,0,0],[1,1,2,0,1],[1,1,2,0,0],[1,1,1,0,0],[1,1,0,0,0],[1,0,0,0,0]];
    let M=DEF;
    try{const saved=await API.get('/role/matrix');if(Array.isArray(saved)&&saved.length)M=saved;}catch(e){}
    const lvl={};MODS.forEach((pages,i)=>{const v=(M[i]&&M[i][COL]!=null)?M[i][COL]:DEF[i][COL];pages.forEach(p=>lvl[p]=v);});
    // ซ่อนเมนูที่ไม่มีสิทธิ์ (level 0)
    document.querySelectorAll('.side .nav-item').forEach(a=>{
      const href=(a.getAttribute('href')||'').split('/').pop();
      if(href&&lvl[href]===0){a.style.display='none';const sub=a.nextElementSibling;if(sub&&sub.classList.contains('nav-sub'))sub.style.display='none';}
    });
    // ===== ซ่อนปุ่ม/ลิงก์ "ทุกที่" ที่พาไปหน้าซึ่ง role นี้ไม่มีสิทธิ์ — ไม่ใช่แค่เมนู =====
    // หลัก UX: ปุ่มที่กดแล้วเจอ "ไม่มีสิทธิ์" ไม่ควรมีให้เห็นตั้งแต่แรก
    const blockedTarget=(s)=>{const m=(s||'').match(/([a-z0-9-]+\.html)/i);return !!(m&&lvl[m[1]]===0);};
    const hideBlockedLinks=(root)=>{
      (root||document).querySelectorAll('a[href],[onclick]').forEach(el=>{
        if(el.closest('.side'))return; // เมนูจัดการไปแล้วด้านบน
        if(blockedTarget(el.getAttribute('href'))||blockedTarget(el.getAttribute('onclick')))el.style.display='none';
      });
    };
    hideBlockedLinks(document);
    // เนื้อหา/modal ที่ render ทีหลังจาก API ก็ต้องโดนกวาดด้วย (debounce กันถี่เกิน)
    let _hbTmr=null;
    new MutationObserver(()=>{clearTimeout(_hbTmr);_hbTmr=setTimeout(()=>hideBlockedLinks(document),120);})
      .observe(document.body,{childList:true,subtree:true});
    // หน้าปัจจุบัน — บล็อกถ้าไม่มีสิทธิ์
    const cur=(location.pathname.split('/').pop()||'index.html');
    if(lvl[cur]===0){
      document.querySelectorAll('.content').forEach(c=>c.innerHTML='<div style="text-align:center;padding:80px 20px;color:var(--ink-3)"><div style="font-size:46px;margin-bottom:10px">🔒</div><div style="font-size:18px;font-weight:700;color:var(--ink)">ไม่มีสิทธิ์เข้าถึงหน้านี้</div><div style="margin-top:6px;font-size:13.5px">บัญชีของคุณ ('+roleThai(role)+') ไม่ได้รับสิทธิ์เข้าหน้านี้ · กำลังพากลับแดชบอร์ด…</div></div>');
      BS.toast&&BS.toast('คุณไม่มีสิทธิ์เข้าถึงหน้านี้','x');
      setTimeout(()=>location.href=(window.BASE||'')+'index.html',1400);
    } else if(lvl[cur]===2){
      // ดูได้อย่างเดียว → แบนเนอร์ + ซ่อนปุ่ม action ทั้งหน้า "รวมถึงใน modal ที่เปิดทีหลัง"
      try{const c=document.querySelector('.content');if(c)c.insertAdjacentHTML('afterbegin','<div style="background:#fff8ec;border:1px solid #f0d9a8;color:#8a6d1a;border-radius:11px;padding:9px 14px;margin-bottom:14px;font-size:13px;font-weight:500">👁️ โหมดดูอย่างเดียว — บัญชี '+roleThai(role)+' ดูข้อมูลได้ แต่แก้ไขไม่ได้</div>');
        // คำ action แรง (ใช้กับปุ่มทุกชนิด) vs คำที่ใช้กับปุ่มหลักเท่านั้น (กันซ่อนปุ่ม "ยกเลิก/ปิด" ของ modal)
        const ACT_HARD=/เรียกคิว|ยกเลิกคิว|ลบ|อนุมัติ|จบงาน|เริ่มให้บริการ|เริ่มงาน|รับเข้า|เบิกออก|ขาย & ออกใบเสร็จ|มาแล้ว|ไม่มาตามนัด|เก็บเงิน|ไปชำระเงิน/;
        const ACT_MAIN=/สร้าง|เพิ่ม|บันทึก|แก้ไข|รับชำระ|ออกบิล|ยืนยัน|เริ่ม|ขาย|เช็คอิน|ใช้ตัวกรอง|โหลด.*เข้าบิล/;
        const hideActs=(root)=>{
          (root||document).querySelectorAll('button,.btn').forEach(b=>{
            const t=b.textContent||'';
            const isMain=b.classList.contains('btn-pri')||b.classList.contains('btn-soft')||b.classList.contains('btn-primary');
            if(ACT_HARD.test(t)||(isMain&&ACT_MAIN.test(t)))b.style.display='none';
          });
        };
        hideActs(document);
        let _vaTmr=null;
        new MutationObserver(()=>{clearTimeout(_vaTmr);_vaTmr=setTimeout(()=>hideActs(document),120);})
          .observe(document.body,{childList:true,subtree:true});
      }catch(e){}
    }
  }catch(e){console.warn('perm enforce',e);}
})();
})();
