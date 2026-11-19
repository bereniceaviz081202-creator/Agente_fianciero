# app.py - SISTEMA MULTIAGENTE REAL - 5 agentes autónomos
# Sin tokens, sin OpenAI, 100% gratis con Yahoo Finance
import os, json
from datetime import datetime
import yfinance as yf
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# ================= MEMORIA COMPARTIDA (BLACKBOARD) =================
class MemoriaCompartida:
    """Donde los agentes se dejan mensajes entre ellos"""
    def __init__(self):
        self.datos = {}
        self.historial = []
        self.ciclos = 0
    def escribir(self, agente, clave, valor):
        print(f"[{agente}] -> escribe {clave}: {str(valor)[:80]}")
        self.datos[clave] = valor
    def leer(self, clave):
        return self.datos.get(clave)

MEMORIA = MemoriaCompartida()

# ================= AGENTE 1: MONITOR YAHOO =================
class AgenteMonitorYahoo:
    """Agente 1: Solo se encarga de buscar en Yahoo Finance"""
    nombre = "AGENTE-MONITOR-YAHOO"
    def ejecutar(self, ticker, memoria):
        ticker = ticker.strip().upper()
        print(f"[{self.nombre}] Buscando {ticker}...")
        tk = yf.Ticker(ticker)
        info = tk.info
        balance = tk.balance_sheet
        resultados = tk.financials
        flujo = tk.cashflow
        def obtener(df,nombre):
            try:
                if isinstance(df, dict):
                    v = df.get(nombre, 0)
                    return float(v or 0)
                if isinstance(df, (tuple, list)):
                    return 0
                valor = df.loc[nombre]
                while hasattr(valor, "iloc"):
                    valor = valor.iloc[0]
                return float(valor)
            except:
                return 0
        def obtener_texto(df,nombre):
            try:
                if isinstance(df, dict):
                    return str(df.get(nombre, "") or "")
                return ""
            except:
                return ""
        datos = {
            "empresa":obtener(info,"longName"),
            "precio":obtener(info,"currentPrice"),
            "moneda":obtener(info,"currency"),
            "sector":obtener(info,"sector"),
            "activo_circulante":obtener(balance,"Total Current Assets"),
            "pasivo_circulante":obtener(balance,"Total Current Liabilities"),
            "activo_total":obtener(balance,"Total Assets"),
            "pasivo_total":obtener(balance,"Total Liabilities Net Minority Interest"),
            "patrimonio":obtener(balance,"Total Stockholder Equity"),
            "utilidades_retenidas":obtener(balance,"Retained Earnings"),
            "ventas":obtener(resultados,"Total Revenue"),
            "utilidad_neta":obtener(resultados,"Net Income"),
            "utilidad_operativa":obtener(resultados,"Operating Income"),
            "flujo_operativo":obtener(flujo,"Operating Cash Flow"),
        },
        memoria.escribir(self.nombre, "datos_crudos", datos)
        return datos

# ================= AGENTE 2: ANALISTA =================
class AgenteAnalista:
    """Agente 2: Solo calcula ratios, no decide nada"""
    nombre = "AGENTE-ANALISTA"
    def ejecutar(self, datos, memoria):
        def div(a,b): return a/b if b!=0 else 0
        cap = datos["activo_circulante"] - datos["pasivo_circulante"]
        ratios = {
            "capital_trabajo": cap,
            "liquidez": div(datos["activo_circulante"], datos["pasivo_circulante"]),
            "endeudamiento": div(datos["pasivo_total"], datos["activo_total"]),
            "roa": div(datos["utilidad_neta"], datos["activo_total"]),
            "roe": div(datos["utilidad_neta"], datos["patrimonio"]),
            "margen_neto": div(datos["utilidad_neta"], datos["ventas"]),
            "rotacion_activos": div(datos["ventas"], datos["activo_total"]),
            "cobertura_flujo": div(datos["flujo_operativo"], datos["pasivo_circulante"]),
        }
        memoria.escribir(self.nombre, "ratios", ratios)
        return ratios

# ================= AGENTE 3: PREDICTOR =================
class AgentePredictor:
    """Agente 3: Solo predice riesgo con Altman + Springate"""
    nombre = "AGENTE-PREDICTOR"
    def ejecutar(self, datos, ratios, memoria):
        def div(a,b): return a/b if b!=0 else 0
        X1 = div(ratios["capital_trabajo"], datos["activo_total"])
        X2 = div(datos["utilidades_retenidas"], datos["activo_total"])
        X3 = div(datos["utilidad_operativa"], datos["activo_total"])
        X4 = div(datos["patrimonio"], datos["pasivo_total"])
        X5 = ratios["rotacion_activos"]
        z_altman = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5
        z_springate = 1.03*X1 + 3.07*X3 + 0.66*div(datos["utilidad_neta"], datos["pasivo_circulante"]) + 0.4*X5
        if z_altman < 1.23: nivel, color, prob = "🔴 CRITICO", "red", 0.85
        elif z_altman < 2.90: nivel, color, prob = "🟡 ALERTA", "orange", 0.45
        else: nivel, color, prob = "🟢 SALUDABLE", "green", 0.10
        pred = {"z_altman": round(z_altman,2), "z_springate": round(z_springate,2),
                "nivel": nivel, "color": color, "prob_insolvencia": prob}
        memoria.escribir(self.nombre, "prediccion", pred)
        return pred

# ================= AGENTE 4: ESTRATEGA =================
class AgenteEstratega:
    """Agente 4: Solo propone acciones, no calcula"""
    nombre = "AGENTE-ESTRATEGA"
    def ejecutar(self, datos, ratios, pred, memoria):
        acciones = []
        if ratios["liquidez"] < 1: acciones.append("Renegociar pasivo circulante a largo plazo")
        if ratios["endeudamiento"] > 0.6: acciones.append("No adquirir nueva deuda por 90 días")
        if ratios["roa"] < 0: acciones.append("Recorte de gastos operativos 15%")
        if ratios["capital_trabajo"] < 0: acciones.append(f"Inyección de capital por ${abs(ratios['capital_trabajo']):,.0f}")
        if not acciones: acciones.append("Mantener política actual - empresa saludable")
        memoria.escribir(self.nombre, "acciones", acciones)
        return acciones

# ================= AGENTE 5: SUPERVISOR =================
class AgenteSupervisor:
    """Agente 5: El jefe. Coordina a los otros 4 en orden"""
    nombre = "AGENTE-SUPERVISOR"
    def __init__(self):
        self.monitor = AgenteMonitorYahoo()
        self.analista = AgenteAnalista()
        self.predictor = AgentePredictor()
        self.estratega = AgenteEstratega()
    def ejecutar_flujo(self, ticker, memoria):
        print(f"\n[{self.nombre}] === INICIANDO FLUJO MULTIAGENTE PARA {ticker} ===")
        datos = self.monitor.ejecutar(ticker, memoria)
        ratios = self.analista.ejecutar(datos, memoria)
        pred = self.predictor.ejecutar(datos, ratios, memoria)
        acciones = self.estratega.ejecutar(datos, ratios, pred, memoria)
        reporte = {**datos, **ratios, **pred, "acciones": acciones, "fecha": str(datetime.now())}
        memoria.historial.insert(0, reporte)
        memoria.ciclos += 1
        print(f"[{self.nombre}] Flujo terminado. Resultado: {pred['nivel']}")
        return reporte

SUPERVISOR = AgenteSupervisor()

# ================= WEB =================
HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Multiagente Insolvencia</title>
<style>body{font-family:Arial;padding:20px;background:#f4f4f4;max-width:900px;margin:auto}
.card{background:white;padding:20px;border-radius:12px;margin:15px 0;box-shadow:0 2px 8px #ccc}
.red{border-left:8px solid red}.orange{border-left:8px solid orange}.green{border-left:8px solid green}
input{padding:12px;width:200px;font-size:16px} button{padding:12px 20px;background:#000;color:white;border:none;border-radius:8px;cursor:pointer}
.agentes{background:#000;color:#0f0;padding:10px;border-radius:8px;font-family:monospace;font-size:12px}</style></head><body>
<h1>🤖 Sistema Multiagente Autónomo - 5 Agentes</h1>
<div class="agentes">AGENTE-SUPERVISOR coordina → [MONITOR-YAHOO] → [ANALISTA] → [PREDICTOR] → [ESTRATEGA]</div><br>
<form action="/buscar" method="GET"><input name="ticker" placeholder="Ej: AAPL, AMXL.MX" required><button>🔍 Analizar</button></form>
<p>Prueba: AAPL, MSFT, AMXL.MX, WALMEX.MX, CEMEX.MX</p>
{% for r in datos %}
<div class="card {{r.color}}"><h2>{{r.empresa}}</h2>
<p><b>Precio:</b> {{r.precio}} {{r.moneda}} | <b>Sector:</b> {{r.sector}}</p>
<h3>{{r.nivel}} | Z-Altman: {{r.z_altman}} | Springate: {{r.z_springate}}</h3>
<p>Liquidez: {{r.liquidez|round(2)}} | Endeudamiento: {{r.endeudamiento|round(2)}} | ROA: {{r.roa|round(3)}}</p>
<b>Acciones del Agente Estratega:</b><ul>{% for a in r.acciones %}<li>{{a}}</li>{% endfor %}</ul>
<p><small>Procesado por 4 agentes + 1 supervisor. Ciclo #{{ciclos}}</small></p></div>
{% endfor %}
{% if error %}<div class="card red">{{error}}</div>{% endif %}
</body></html>
"""
@app.route("/")
def home(): return render_template_string(HTML, datos=MEMORIA.historial, ciclos=MEMORIA.ciclos, error=None)
@app.route("/buscar")
def buscar():
    ticker = request.args.get("ticker","").strip()
    try:
        SUPERVISOR.ejecutar_flujo(ticker, MEMORIA)
        return render_template_string(HTML, datos=MEMORIA.historial, ciclos=MEMORIA.ciclos, error=None)
    except Exception as e:
        return render_template_string(HTML, datos=MEMORIA.historial, ciclos=MEMORIA.ciclos, error=f"Ticker '{ticker}' no encontrado. Error: {str(e)[:120]}")
@app.route("/ping")
def ping(): return "OK"
@app.route("/api/ticker/<ticker>")
def api(ticker):
    return jsonify(SUPERVISOR.ejecutar_flujo(ticker, MEMORIA))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
