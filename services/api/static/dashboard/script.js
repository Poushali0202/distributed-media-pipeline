async function fetchJSON(url){
  const r = await fetch(url); if(!r.ok) throw new Error(await r.text()); return await r.json();
}
function setText(id, v){ document.getElementById(id).textContent = v ?? "–"; }
async function refresh(){
  try{
    const stats = await fetchJSON('/stats');
    setText('queued', stats.counts?.queued || 0);
    setText('processing', stats.counts?.processing || 0);
    setText('done', stats.counts?.done || 0);
    setText('failed', stats.counts?.failed || 0);
    setText('p50', stats.p50_latency_s ? stats.p50_latency_s.toFixed(1) : '–');
    setText('p95', stats.p95_latency_s ? stats.p95_latency_s.toFixed(1) : '–');

    const jobs = await fetchJSON('/jobs?limit=50');
    const tbody = document.querySelector('#jobs tbody'); tbody.innerHTML = '';
    for(const j of jobs){
      const tr = document.createElement('tr');
      const shortId = j.id.slice(0,8);
      tr.innerHTML = `<td title="${j.id}">${shortId}</td><td>${j.status}</td><td>${j.media_id.slice(0,8)}...</td><td>${new Date(j.created_at).toLocaleString()}</td><td>${j.updated_at?new Date(j.updated_at).toLocaleString():'—'}</td>`;
      tbody.appendChild(tr);
    }
  }catch(e){
    console.error(e);
  }
}
refresh();
setInterval(refresh, 3000);
