/* ============================================================
   JavaXd — Interactive Gantt (ใช้ร่วมกัน: แดชบอร์ด + ตารางงานหมอนวด)
   ความสามารถ: ลากย้ายคิว · คลิกช่องว่างเพิ่มคิว · คลิกบล็อกแก้ไขคิว
   · คลิกชื่อหมอนวดดูโปรไฟล์ · เส้นเวลาจริง · เลือกวันจากปฏิทิน

   TODO(Backend):
   - โหลดตารางจริง: GET /schedule?date=YYYY-MM-DD → แทน cfg.rows
   - ลากย้าย/แก้ไข: PATCH /bookings/{id} {start,end,therapist} + เช็ค overlap ฝั่ง server
   - เพิ่มคิว: POST /bookings → คืน id แล้ว broadcast (WebSocket) ให้ทุกเครื่อง
   - เส้นเวลา: ใช้เวลา server ตาม timezone ร้าน แทน new Date() ของเครื่องลูกค้า
   ============================================================ */
window.initGantt=function(cfg){
  const T0=cfg.T0!=null?cfg.T0:0,T1=cfg.T1!=null?cfg.T1:24,R=T1-T0;  // เต็ม 24 ชม. (เลื่อนซ้าย-ขวาได้)
  const SV=cfg.SV,rows=cfg.rows,B=cfg.base||'';
  const mount=document.getElementById(cfg.mount||'gantt');
  const nameW=cfg.nameW||'200px';
  const HW=cfg.hourW||78;                       // ความกว้างต่อชั่วโมง (px) → ใช้ทำ scroll
  const cols=`${nameW} repeat(${R},${HW}px)`;
  const fmtT=t=>String(Math.floor(t)).padStart(2,'0')+':'+(t%1?'30':'00');
  const SVC_KEYS=Object.keys(SV).filter(k=>k!=='rest');
  const isoOf=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  let curISO=isoOf(cfg.startDate?new Date(cfg.startDate):new Date());
  // โหลดข้อมูลของวันปัจจุบันใหม่ (หลังบันทึกย้ายคิว)
  async function reloadGantt(){ if(cfg.onDate){ try{ const nr=await cfg.onDate(curISO); rows.length=0;(nr||[]).forEach(r=>rows.push(r));render(); }catch(e){console.error('reload',e);} } }

  /* ---------- หาช่องเวลาว่างที่ใกล้ที่สุด (กันคิวซ้อนคิว) ----------
     คืนเวลาเริ่มที่ว่างจริงใกล้ start ที่สุด · null ถ้าทั้งวันเต็ม */
  function freeSlot(ri,start,dur,ignore){
    if(ignore==null)ignore=-1;
    start=Math.max(T0,Math.min(T1-dur,Math.round(start*2)/2));
    const busy=rows[ri].b.filter((_,i)=>i!==ignore);
    const ov=s=>{const e=s+dur;return busy.some(b=>s<b[1]-1e-9 && e>b[0]+1e-9);};
    if(!ov(start))return start;
    let fwd=null,bwd=null;
    for(let t=start;t<=T1-dur+1e-9;t+=0.5){if(!ov(t)){fwd=Math.round(t*2)/2;break;}}
    for(let t=start;t>=T0-1e-9;t-=0.5){if(!ov(t)){bwd=Math.round(t*2)/2;break;}}
    if(fwd==null&&bwd==null)return null;
    if(fwd==null)return bwd;
    if(bwd==null)return fwd;
    return (fwd-start)<=(start-bwd)?fwd:bwd;
  }

  /* ---------- render ---------- */
  function render(){
    let h='<div class="gantt-head" style="grid-template-columns:'+cols+'"><div class="g-name" style="border-bottom:none">หมอนวด</div>';
    for(let t=T0;t<T1;t++)h+=`<div class="g-time">${String(t).padStart(2,'0')}:00</div>`;
    h+='</div>';
    rows.forEach((r,ri)=>{
      h+='<div class="gantt-row" style="grid-template-columns:'+cols+'">';
      h+=`<div class="g-name" style="cursor:pointer" onclick="thProfile(${ri})" title="คลิกเพื่อดูโปรไฟล์">${av(r.n,38)}<div><div class="nm">${r.n}</div><div class="sv">${r.sv}</div><div class="${r.st}" style="margin-top:2px"><span class="d"></span>${r.st==='online'?'ออนไลน์':r.note||'ไม่ว่าง'}</div></div></div>`;
      h+=`<div class="g-cells" data-ri="${ri}" title="คลิกช่องว่างเพื่อเพิ่มคิว" style="grid-column:2 / span ${R}">`;
      r.b.forEach((b,bi)=>{
        const L=(b[0]-T0)/R*100,W=(b[1]-b[0])/R*100,col=SV[b[4]][1],rest=b[4]==='rest';
        h+=`<div class="g-block" data-ri="${ri}" data-bi="${bi}" onclick="ganttJob(${ri},${bi})" title="${rest?'ช่วงพัก':'คลิกแก้ไข · ลากเพื่อย้ายเวลา'}" style="cursor:${rest?'default':'grab'};left:${L}%;width:${W}%;background:${rest?'#eef0f4':col+'22'};border-left:3px solid ${col};${rest?'color:#7b8198':'color:'+col}">
          <b style="color:${rest?'#5a607a':'#2a2f44'}">${rest?'พัก':fmtT(b[0])+' - '+fmtT(b[1])}</b>
          <span>${rest?fmtT(b[0])+' - '+fmtT(b[1]):b[2]+' · '+b[3]}</span></div>`;
      });
      h+=`<div class="g-now"><span class="g-now-t"></span></div></div></div>`;
    });
    // ห่อใน inner ที่กว้างเต็ม 24 ชม. แล้วให้ mount (กว้าง 100% ของการ์ด) scroll ภายใน
    const totalW=parseInt(nameW)+R*HW;
    mount.style.width='100%';mount.style.maxWidth='100%';mount.style.overflowX='auto';mount.style.overflowY='hidden';
    mount.innerHTML='<div class="g-inner" style="min-width:'+totalW+'px">'+h+'</div>';
    if(!mount._scrolled){mount._scrolled=1;const now=new Date();const h0=Math.max(T0,Math.min(T1-1,now.getHours()-1));mount.scrollLeft=Math.max(0,(h0-T0)*HW-10);}
    attach();updateNow();
  }

  /* ---------- เส้นเวลาปัจจุบัน (เคลื่อนตามเวลาจริง ทุก 30 วิ) ---------- */
  function updateNow(){
    // เวลาไทย (UTC+7) ไม่พึ่ง timezone ของเครื่อง
    const d=new Date();const thai=new Date(d.getTime()+d.getTimezoneOffset()*60000+7*3600000);
    let t=thai.getHours()+thai.getMinutes()/60+thai.getSeconds()/3600;
    const hhmmss=String(thai.getHours()).padStart(2,'0')+':'+String(thai.getMinutes()).padStart(2,'0')+':'+String(thai.getSeconds()).padStart(2,'0');
    mount.querySelectorAll('.g-now').forEach(n=>{
      if(t<T0||t>T1){ n.style.display='none'; }            // นอกเวลาทำการ → ซ่อนเส้น
      else {
        n.style.display=''; n.style.left=((t-T0)/R*100)+'%';
        n.title='เวลาปัจจุบัน '+hhmmss;
        const lbl=n.querySelector('.g-now-t'); if(lbl)lbl.textContent=hhmmss;
      }
    });
  }
  // เดินทุก 1 วิ + อัปเดตทันทีเมื่อกลับมาที่แท็บ (กัน interval ซ้อนถ้า init ซ้ำ mount เดิม)
  if(mount._nowTimer)clearInterval(mount._nowTimer);
  mount._nowTimer=setInterval(updateNow,1000);
  if(!mount._nowVis){mount._nowVis=1;document.addEventListener('visibilitychange',()=>{if(!document.hidden)updateNow();});}

  /* ---------- ลากย้าย + คลิกช่องว่าง ---------- */
  function attach(){
    mount.querySelectorAll('.g-block').forEach(el=>{
      el.addEventListener('pointerdown',ev=>{
        const ri=+el.dataset.ri,bi=+el.dataset.bi,b=rows[ri].b[bi];
        if(b[4]==='rest')return;
        ev.preventDefault();
        const cells=el.parentElement,cw=cells.getBoundingClientRect().width;
        const startX=ev.clientX,origL=parseFloat(el.style.left);
        let moved=false,curL=origL,armed=false;
        // กันลากโดยไม่ตั้งใจ: ต้อง "คลิกค้าง 2 วินาที" ก่อนถึงจะลากได้ (คลิกสั้น = เปิดดู/แก้ไขตามปกติ)
        const holdT=setTimeout(()=>{armed=true;el.style.boxShadow='0 0 0 3px var(--brand),0 10px 24px rgba(0,0,0,.22)';el.style.cursor='grabbing';
          if(window.BS&&BS.toast)BS.toast('ปลดล็อกการลากแล้ว — ลากเพื่อย้ายเวลา','clock');},2000);
        const mm=e=>{const dx=e.clientX-startX;
          if(!armed){if(Math.abs(dx)>8)clearTimeout(holdT);return;}  // ยังไม่ครบ 2 วิ → ไม่ลาก (ขยับ = ยกเลิกการนับ)
          if(!moved&&Math.abs(dx)>6){moved=true;el.style.zIndex=9}
          if(moved){const W=(b[1]-b[0])/R*100;curL=Math.max(0,Math.min(100-W,origL+dx/cw*100));el.style.left=curL+'%'}};
        const mu=()=>{document.removeEventListener('pointermove',mm);document.removeEventListener('pointerup',mu);
          clearTimeout(holdT);el.style.boxShadow='';el.style.cursor='';
          if(moved){window.__noClick=true;setTimeout(()=>{window.__noClick=false},150);
            let ns=T0+curL/100*R;ns=Math.round(ns*2)/2;const dur=b[1]-b[0];
            const slot=freeSlot(ri,ns,dur,bi);
            if(slot==null){render();BS.toast('หมอนวด '+rows[ri].n+' ไม่มีช่วงเวลาว่างพอในวันนี้','x');return;}
            const bumped=Math.abs(slot-ns)>1e-9;
            b[0]=slot;b[1]=slot+dur;
            rows[ri].b.sort((a,c)=>a[0]-c[0]);render();
            const id=b[5],src=b[6];
            if(window.API && id && src){
              API.patch('/dashboard/schedule/reschedule',{source:src,itemId:id,startTime:fmtT(slot),therapistId:rows[ri].thId||null})
                .then(()=>{BS.toast((bumped?'มีคิวอยู่แล้ว · เลื่อนไป '+fmtT(slot)+' · ':'')+'ย้ายคิว '+b[2]+' ไป '+fmtT(slot)+' - '+fmtT(slot+dur)+' บันทึกแล้ว','check');reloadGantt();})
                .catch(e=>{BS.toast('ย้ายไม่สำเร็จ: '+e.message,'x');reloadGantt();});
            } else {
              BS.toast('ย้ายในมุมมองชั่วคราว ('+fmtT(slot)+') · คิวนี้ยังไม่มีในระบบ','clock');
            }}};
        document.addEventListener('pointermove',mm);document.addEventListener('pointerup',mu);
      });
    });
    mount.querySelectorAll('.g-cells').forEach(c=>{
      c.addEventListener('click',e=>{
        if(e.target!==c||window.__noClick)return;
        const r=c.getBoundingClientRect();
        let t=T0+(e.clientX-r.left)/r.width*R;t=Math.round(t*2)/2;
        quickAdd(+c.dataset.ri,t);
      });
    });
  }

  /* ---------- เพิ่มคิว (จากช่องว่าง / ปุ่ม) ---------- */
  window.quickAdd=function(ri,t){
    const r=rows[ri];
    BS.modal({title:'เพิ่มคิวให้ '+r.n,sub:'เริ่ม '+fmtT(t)+' น. · จากช่องว่างในตาราง',w:440,
      body:`<div class="field"><label>ลูกค้า</label><input id="qaCust" placeholder="ชื่อลูกค้า หรือเว้นว่าง = Walk-in"></div>
        <div class="grid2"><div class="field"><label>บริการ</label><select id="qaSvc">${SVC_KEYS.map(k=>`<option value="${k}">${SV[k][0]}</option>`).join('')}</select></div>
          <div class="field"><label>ระยะเวลา</label><select id="qaDur"><option value="1">60 นาที</option><option value="1.5">90 นาที</option><option value="0.75">45 นาที</option><option value="2">120 นาที</option></select></div></div>
        <div class="grid2"><div class="field"><label>เวลาเริ่ม</label><input id="qaT" type="time" value="${fmtT(t)}"></div>
          <div class="field"><label>หมอนวด</label><select id="qaTh">${rows.map((x,i)=>`<option value="${i}"${i===ri?' selected':''}>${x.n}</option>`).join('')}</select></div></div>`,
      foot:`<button class="btn btn-ghost" onclick="BS.closeModal()">ยกเลิก</button>
        <button class="btn btn-pri" onclick="confirmQuickAdd()">${svg('check')} เพิ่มคิว</button>`});
  };
  window.confirmQuickAdd=function(){
    const cust=document.getElementById('qaCust').value.trim()||'Walk-in';
    const k=document.getElementById('qaSvc').value;
    const dur=parseFloat(document.getElementById('qaDur').value);
    const ri=+document.getElementById('qaTh').value;
    const tv=document.getElementById('qaT').value.split(':');
    let t=(+tv[0])+((+tv[1])>=30?0.5:0);
    const slot=freeSlot(ri,t,dur,-1);
    if(slot==null){BS.toast('หมอนวด '+rows[ri].n+' ไม่มีช่วงเวลาว่างพอในวันนี้','x');return;}
    const bumped=Math.abs(slot-Math.max(T0,Math.min(T1-dur,Math.round(t*2)/2)))>1e-9;
    rows[ri].b.push([slot,slot+dur,SV[k][0],cust,k]);
    rows[ri].b.sort((a,b)=>a[0]-b[0]);
    BS.closeModal();render();
    BS.toast('เพิ่มคิวในมุมมองชั่วคราว ('+fmtT(slot)+' น.) · ยังไม่บันทึกถาวร — สร้างคิวจริงที่หน้า POS หรือ "การจอง"','clock');
  };

  /* ---------- คลิกบล็อก = แก้ไขคิวได้เลย ---------- */
  window.ganttJob=function(ri,bi){
    if(window.__noClick)return;
    const r=rows[ri],b=r.b[bi];
    if(b[4]==='rest'){BS.toast('ช่วงพักของ '+r.n+' · '+fmtT(b[0])+' - '+fmtT(b[1]));return}
    const dur=b[1]-b[0];
    window.__gjCustObj=null;
    BS.modal({title:'แก้ไขคิว · '+r.n+' '+fmtT(b[0])+' - '+fmtT(b[1]),sub:'แก้ไขได้ทันที หรือลากบล็อกในตารางเพื่อย้ายเวลา',w:480,
      body:`<div class="field"><label>ลูกค้า</label><input id="gjCust" value="${b[3]}"></div>
        <div id="gjCustMeta" style="margin:-6px 0 12px;font-size:12.5px;color:var(--ink-3);min-height:17px">กำลังค้นหาข้อมูลลูกค้า…</div>
        <div class="grid2"><div class="field"><label>บริการ</label><select id="gjSvc">${SVC_KEYS.map(k=>`<option value="${k}"${k===b[4]?' selected':''}>${SV[k][0]}</option>`).join('')}</select></div>
          <div class="field"><label>ระยะเวลา</label><select id="gjDur">${[[0.75,'45 นาที'],[1,'60 นาที'],[1.5,'90 นาที'],[2,'120 นาที']].map(d=>`<option value="${d[0]}"${d[0]===dur?' selected':''}>${d[1]}</option>`).join('')}</select></div></div>
        <div class="grid2"><div class="field"><label>เวลาเริ่ม</label><input id="gjT" type="time" value="${fmtT(b[0])}"></div>
          <div class="field"><label>หมอนวด</label><select id="gjTh">${rows.map((x,i)=>`<option value="${i}"${i===ri?' selected':''}>${x.n}</option>`).join('')}</select></div></div>
        <div class="field"><label>หมายเหตุลูกค้า <span style="font-weight:400;color:var(--ink-3);font-size:12px">· เช่น แพ้น้ำหอม, ชอบน้ำหนักเบา, ปวดหลัง</span></label>
          <textarea id="gjNotes" rows="2" placeholder="บันทึกข้อควรระวัง / ความชอบ เพื่อให้หมอนวดทราบ" style="resize:vertical"></textarea></div>`,
      foot:`<button class="btn btn-ghost" style="color:var(--red);border-color:#f4ccd0;margin-right:auto" onclick="gjDel(${ri},${bi})">${svg('trash')} ยกเลิกคิว</button>
        <a class="btn btn-ghost" href="${(cfg.posHref||B+'pages/pos.html')+(b[7]?'?walkin='+b[7]:'')}" style="text-decoration:none">${svg('wallet')} รับชำระ</a>
        <button class="btn btn-pri" onclick="gjSave(${ri},${bi})">${svg('check')} บันทึก</button>`});
    // ค้นหาข้อมูลลูกค้าจริงจาก DB → แสดงเบอร์/จำนวนครั้ง + ดึงหมายเหตุเดิม
    if(window.API && b[3] && b[3]!=='Walk-in'){
      API.get('/customer?search='+encodeURIComponent(b[3])+'&pageSize=5').then(res=>{
        const items=(res&&res.items)||[];
        const c=items.find(x=>(x.displayName||'').trim()===b[3].trim())||items[0];
        const meta=document.getElementById('gjCustMeta');const nt=document.getElementById('gjNotes');
        if(c){window.__gjCustObj=c;
          if(meta)meta.innerHTML=`${c.phone?'📞 '+c.phone:'ไม่มีเบอร์'} · มาแล้ว <b>${c.totalVisits||0}</b> ครั้ง${c.lastVisitAt&&API.fmtDate?' · ล่าสุด '+API.fmtDate(c.lastVisitAt):''}`;
          if(nt&&c.notes){nt.value=c.notes;if(/แพ้|allergy|ระวัง/i.test(c.notes)){nt.style.borderColor='#f0a52a';nt.style.background='#fff8ec';}}
        } else if(meta){meta.innerHTML='<span style="color:var(--ink-3)">ลูกค้าใหม่ / ยังไม่มีในระบบ</span>';}
      }).catch(()=>{const meta=document.getElementById('gjCustMeta');if(meta)meta.textContent='';});
    } else {const meta=document.getElementById('gjCustMeta');if(meta)meta.innerHTML='<span style="color:var(--ink-3)">ลูกค้า Walk-in (ไม่มีประวัติ)</span>';}
  };
  window.gjSave=function(ri,bi){
    const b=rows[ri].b[bi];
    const id=b[5],src=b[6];
    const cust=document.getElementById('gjCust').value.trim()||'Walk-in';
    const k=document.getElementById('gjSvc').value;
    const dur=parseFloat(document.getElementById('gjDur').value);
    const nri=+document.getElementById('gjTh').value;
    const tv=document.getElementById('gjT').value.split(':');
    let t=(+tv[0])+((+tv[1])>=30?0.5:0);
    // บันทึกหมายเหตุลูกค้าลง DB จริง (ถ้าพบลูกค้าในระบบ + หมายเหตุเปลี่ยน)
    const notesEl=document.getElementById('gjNotes');const c=window.__gjCustObj;
    if(window.API && c && c.id && notesEl && (notesEl.value||'').trim()!==(c.notes||'').trim()){
      API.put('/customer/'+c.id,{displayName:c.displayName,phone:c.phone||null,avatarUrl:c.avatarUrl||null,notes:notesEl.value.trim()||null,lineUserId:null,preferredTherapistId:c.preferredTherapistId||null})
        .then(()=>BS.toast('บันทึกหมายเหตุลูกค้า '+c.displayName+' แล้ว','check')).catch(()=>BS.toast('บันทึกหมายเหตุไม่สำเร็จ','x'));
    }
    rows[ri].b.splice(bi,1);   // เอาคิวเดิมออกก่อน แล้วค่อยหาช่องว่างของหมอที่เลือก
    const slot=freeSlot(nri,t,dur,-1);
    if(slot==null){rows[ri].b.push(b);rows[ri].b.sort((a,c)=>a[0]-c[0]);BS.toast('หมอนวด '+rows[nri].n+' ไม่มีช่วงเวลาว่างพอ','x');return;}
    rows[nri].b.push([slot,slot+dur,SV[k][0],cust,k,id,src,b[7]||null]);
    rows[nri].b.sort((a,c)=>a[0]-c[0]);
    BS.closeModal();render();
    if(window.API && id && src){
      API.patch('/dashboard/schedule/reschedule',{source:src,itemId:id,startTime:fmtT(slot),therapistId:rows[nri].thId||null})
        .then(()=>{BS.toast('บันทึกคิวของ '+cust+' → '+rows[nri].n+' '+fmtT(slot)+' น. แล้ว','check');reloadGantt();})
        .catch(e=>{BS.toast('บันทึกไม่สำเร็จ: '+e.message,'x');reloadGantt();});
    } else {
      BS.toast('แก้ในมุมมองชั่วคราว · คิวนี้ยังไม่มีในระบบ','clock');
    }
  };
  window.gjDel=function(ri,bi){
    const b=rows[ri].b[bi];
    rows[ri].b.splice(bi,1);
    BS.closeModal();render();
    BS.toast('ลบออกจากมุมมองชั่วคราว · ยังไม่บันทึกถาวร — ยกเลิกคิวจริงที่หน้า "การจอง"','clock');
  };

  /* ---------- โปรไฟล์หมอนวด (คลิกชื่อ/รูปในตาราง) ---------- */
  window.thProfile=function(ri){
    const r=rows[ri];const jobs=r.b.filter(b=>b[4]!=='rest');
    BS.modal({title:'โปรไฟล์หมอนวด · '+r.n,sub:'คิววันนี้ '+jobs.length+' งาน'+(r.util?' · อัตราใช้งาน '+r.util+'%':''),w:460,
      body:`<div class="flex ac g12" style="margin-bottom:14px">${av(r.n,52)}<div style="flex:1"><div style="font-weight:700;font-size:16px">${r.n}</div><div class="sub" style="font-size:12.5px">ถนัด: ${r.sv}</div></div><span class="badge ${r.st==='online'?'b-green':'b-orange'}">${r.st==='online'?'ออนไลน์':r.note||'ไม่ว่าง'}</span></div>
        <h3 style="font-size:13.5px;font-weight:600;margin-bottom:4px">คิววันนี้</h3>
        ${jobs.length?jobs.map(b=>`<div class="notif" style="cursor:pointer;align-items:center" onclick="BS.closeModal();ganttJob(${ri},${r.b.indexOf(b)})"><span class="nd" style="background:${SV[b[4]][1]}"></span><div class="tx"><div style="font-weight:600">${b[2]} · ${b[3]}</div><div class="tm">${fmtT(b[0])} - ${fmtT(b[1])} น.</div></div><span style="margin-left:auto;color:var(--ink-3)">${svg('chevR')}</span></div>`).join(''):'<div style="text-align:center;color:var(--ink-3);font-size:13px;padding:18px 0">วันนี้ยังไม่มีคิว</div>'}`,
      foot:`<a class="btn btn-ghost" href="${B}pages/staff.html" style="text-decoration:none;margin-right:auto">หน้าพนักงาน →</a>
        <button class="btn btn-pri" onclick="BS.closeModal();quickAdd(${ri},16)">${svg('plus')} เพิ่มคิวให้ ${r.n}</button>`});
  };

  /* ---------- ตั้ง rows ใหม่ (ใช้ตอนเปลี่ยนวัน) ---------- */
  function setRows(nr){rows.length=0;(nr||[]).forEach(r=>rows.push(r));render();}

  /* ---------- เลือกวัน: ปุ่ม < > + ปฏิทิน → โหลดข้อมูลจริงของวันนั้น ----------
     cfg.onDate(isoDate) → Promise<rows> : ผู้เรียกไปดึง GET /dashboard/schedule?date= */
  if(cfg.dateEl){
    const lbl=document.getElementById(cfg.dateEl);
    const THMONTH=['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'];
    const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
    const sameDay=(a,b)=>a.toDateString()===b.toDateString();
    let current=cfg.startDate?new Date(cfg.startDate):new Date();
    async function setDate(d){
      current=d;curISO=iso(d);
      lbl.textContent=d.getDate()+' '+THMONTH[d.getMonth()]+' '+(d.getFullYear()+543);
      if(cfg.todayBadge){const tb=document.getElementById(cfg.todayBadge);if(tb)tb.style.display=sameDay(d,new Date())?'':'none'}
      if(cfg.onDate){
        mount.style.opacity='.4';
        try{const nr=await cfg.onDate(iso(d));setRows(nr||[]);}catch(e){console.error('gantt onDate',e);BS.toast&&BS.toast('โหลดตารางของวันนี้ไม่สำเร็จ','x');}
        mount.style.opacity='1';
      }
    }
    // ตั้ง label เริ่มต้นให้ตรงวันจริง (ไม่ยิง onDate ซ้ำ เพราะ rows โหลดมาแล้ว)
    lbl.textContent=current.getDate()+' '+THMONTH[current.getMonth()]+' '+(current.getFullYear()+543);
    if(cfg.todayBadge){const tb=document.getElementById(cfg.todayBadge);if(tb)tb.style.display=sameDay(current,new Date())?'':'none';}
    window.shiftDay=delta=>{const n=new Date(current);n.setDate(n.getDate()+delta);setDate(n);};
    lbl.style.cursor='pointer';lbl.title='คลิกเพื่อเลือกวันจากปฏิทิน';
    lbl.addEventListener('click',()=>{
      const y=current.getFullYear(),mo=current.getMonth();
      const first=new Date(y,mo,1).getDay(),dim=new Date(y,mo+1,0).getDate();
      const dows=['อา','จ','อ','พ','พฤ','ศ','ส'];
      let mc='<div class="mcal" style="margin-top:0">'+dows.map(d=>`<div class="dow">${d}</div>`).join('');
      for(let i=0;i<first;i++)mc+='<div class="dy mut"></div>';
      const today=new Date();
      for(let d=1;d<=dim;d++){
        let cls='dy';if(d===current.getDate())cls+=' today';else if(y===today.getFullYear()&&mo===today.getMonth()&&d===today.getDate())cls+=' has';
        mc+=`<div class="${cls}" style="cursor:pointer" onclick="pickGDay(${d})">${d}</div>`;
      }
      mc+='</div>';
      BS.modal({title:'เลือกวันที่ · '+THMONTH[mo]+' '+(y+543),sub:'เลือกวันเพื่อดูตารางงานของวันนั้น',w:380,body:mc,
        foot:`<button class="btn btn-ghost" onclick="pickGDay(0)">วันนี้</button><button class="btn btn-pri" onclick="BS.closeModal()">ปิด</button>`});
    });
    window.pickGDay=function(d){BS.closeModal();if(d===0){setDate(new Date());}else{setDate(new Date(current.getFullYear(),current.getMonth(),d));}};
  }

  render();
  return {render,rows,setRows};
};
