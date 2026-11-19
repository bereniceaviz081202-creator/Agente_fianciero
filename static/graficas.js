function dibujarGraficas(rep){
  document.getElementById('colDer').style.display='block';
  if(window.miGraf1) window.miGraf1.destroy();
  if(window.miGraf2) window.miGraf2.destroy();
  window.miGraf1=new Chart(document.getElementById('grafPrecio'),{type:'line',data:{labels:rep.historial_precio.fechas,[STRIPPED]
  window.miGraf2=new Chart(document.getElementById('grafSalud'),{type:'bar',data:{labels:['Liquidez',[STRIPPED]
  let z=rep.z_altman; let color=z>2.99?'green':z>1.81?'orange':'red'; let texto=z>2.99?'Segura':z>1.81?'ALERTA':'PELIGRO';
  document.getElementById('barraZ').style.width=Math.min(z/4*100,100)+'%';
  document.getElementById('barraZ').style.background=color;
  document.getElementById('textoZ').innerText='Z = '+z+' - '+texto;
}
async function analizar(){
  let t=document.getElementById('ticker').value;
  let r=await fetch('/analizar?ticker='+t); let data=await r.json();
  if(data.error){alert(data.error); return;}
  let rep=data.reporte;
  document.getElementById('resultado').innerHTML=`<div class="card"><h2>${rep.empresa}</h2><p><b>Precio:</b> ${rep.precio} ${rep.moneda} | <b>Sector:</b> ${rep.sector}</p><p><b>${rep.estado}</b> | <b>Z-Altman:</b> ${rep.z_altman}</p><p>Liquidez: ${rep.liquidez} | Endeudamiento: ${rep.endeudamiento} | ROA: ${rep.roa}</p><ul>${rep.acciones.map(a=>'<li>'+a+'</li>').join('')}</ul></div>`;
  dibujarGraficas(rep);
}
