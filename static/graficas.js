function dibujarGraficas(rep){
  if(!rep.historial_precio || !rep.historial_precio.fechas){
    document.getElementById('colDer').style.display='none';
    return;
  }
  document.getElementById('colDer').style.display='block';
  if(window.miGraf1) window.miGraf1.destroy();
  if(window.miGraf2) window.miGraf2.destroy();
  window.miGraf1=new Chart(document.getElementById('grafPrecio'),{type:'line',data:{labels:rep.historial_precio.fechas,datasets:[{label:'Precio',data:rep.historial_precio.precios,borderColor:'black',fill:false}]},options:{responsive:true}});
  window.miGraf2=new Chart(document.getElementById('grafSalud'),{type:'bar',data:{labels:['Liquidez','Endeudamiento','ROA'],datasets:[{label:'Salud',data:[rep.liquidez||0,rep.endeudamiento||0,rep.roa||0],backgroundColor:['green','orange','blue']}]},options:{responsive:true}});
  let z=rep.z_altman||0; let color=z>2.99?'green':z>1.81?'orange':'red'; let texto=z>2.99?'Segura':z>1.81?'ALERTA':'PELIGRO';
  document.getElementById('barraZ').style.width=Math.min(z/4*100,100)+'%';
  document.getElementById('barraZ').style.background=color;
  document.getElementById('textoZ').innerText='Z = '+z+' - '+texto;
}
async function analizar(){
  let entrada=document.getElementById('ticker').value.trim();
  if(!entrada){alert('Escribe un nombre o ticker, ej: CEMEX, Apple'); return;}
  document.getElementById('resultado').innerHTML='<p>Buscando '+entrada+'...</p>';
  try{
  let rb=await fetch('/api/buscar_nombre?q='+encodeURIComponent(entrada));
  let db=await rb.json();
  let t=(db.ticker||entrada).toUpperCase();
  document.getElementById('resultado').innerHTML='<p>Analizando '+t+'...</p>';
  let r=await fetch('/api/ticker/'+t);
    let data=await r.json();
    if(data.error){alert(data.error); return;}
    let rep=data.reporte || data;
    let estado=rep.estado || (rep.prob_insolvencia!=null ? 'Prob. Insolvencia: '+rep.prob_insolvencia : '');
    let acciones=(rep.acciones||[]).map(a=>'<li>'+a+'</li>').join('');
    document.getElementById('resultado').innerHTML=`<div class="card"><h2>${rep.empresa||rep.ticker||t}</h2><p><b>Precio:</b> ${rep.precio} ${rep.moneda||''} | <b>Sector:</b> ${rep.sector||''}</p><p><b>${estado}</b> | <b>Z-Altman:</b> ${rep.z_altman}</p><p>Liquidez: ${rep.liquidez} | Endeudamiento: ${rep.endeudamiento} | ROA: ${rep.roa}</p><ul>${acciones}</ul></div>`;
    dibujarGraficas(rep);
  }catch(e){ alert('Error: '+e); }
}
const inputBuscar = document.getElementById('ticker');
const divSug = document.getElementById('sugerencias');
let timerSug;
inputBuscar.addEventListener('input', () => {
    clearTimeout(timerSug);
    timerSug = setTimeout(async () => {
    const q = inputBuscar.value.trim();
    if (q.length < 2) { divSug.style.display = 'none'; return; }
    const res = await fetch(`/api/sugerencias?q=${encodeURIComponent(q)}`);
    const lista = await res.json();
    if (!lista.length) { divSug.style.display = 'none'; return; }
    divSug.innerHTML = lista.map(item => `
        <div onclick="elegirTicker('${item.ticker}')"
             style="padding:10px; cursor:pointer; border-bottom:1px solid #eee;">
            <b>${item.ticker}</b> - ${item.nombre} <span style="color:#888; font-size:12px;">${item.bolsa} - ${item.moneda}</span>
        </div>
    `).join('');
    divSug.style.display = 'block';
    }, 500);
});


function elegirTicker(ticker) {
    divSug.style.display = 'none';
    inputBuscar.value = ticker;
    analizar();
}
