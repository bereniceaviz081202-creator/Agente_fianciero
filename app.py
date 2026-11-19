# app.py - SISTEMA MULTIAGENTE REAL - 5 agentes autónomos
# Sin tokens, sin OpenAI, 100% gratis con fuentes financieras confiables
import os, json, time
from datetime import datetime
import yfinance as yf
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Cache para no pegarle a Yahoo a cada rato
CACHE = {}

ARCHIVO_CACHE = "cache.json"

def cargar_cache():
    if os.path.exists(ARCHIVO_CACHE):
        try:
            with open(ARCHIVO_CACHE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def guardar_cache():
    try:
        with open(ARCHIVO_CACHE, "w") as f:
            json.dump(CACHE, f)
    except Exception as e:
        print(f"No se pudo guardar cache: {e}")

CACHE = cargar_cache()

def esta_en_cache(ticker):
    if ticker in CACHE:
        datos, cuando = CACHE[ticker]
        if time.time() - cuando < CACHE_TIEMPO:
            return datos
    return None

def guardar_en_cache(ticker, datos):
    CACHE[ticker] = (datos, time.time())

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

CACHE_TIEMPO = 7 * 24 * 3600

# ================= AGENTE 1: MONITOR YAHOO =================
class AgenteMonitorYahoo:
    """Agente 1: Solo se encarga de buscar en Yahoo Finance"""
    nombre = "AGENTE-MONITOR-YAHOO"
    def ejecutar(self, ticker, memoria):
        ticker = ticker.strip().upper()
    
        # 1. Buscar en lo guardado
        datos_cache = esta_en_cache(ticker)
        if datos_cache:
            print(f"[{self.nombre}] Usando CACHE para {ticker}")
            memoria.escribir(self.nombre, "datos_crudos", datos_cache)
            return datos_cache

        print(f"[{self.nombre}] Buscando {ticker}...")
        try:
            time.sleep(1)
            tk = yf.Ticker(ticker)
            info = tk.info
            time.sleep(1)
            balance = tk.balance_sheet
            resultados = tk.financials
            flujo = tk.cashflow
            datos = {"info": info, "balance": balance, "resultados": resultados, "flujo": flujo}
            CACHE[ticker] = (datos, time.time())
            guardar_cache()
            memoria.escribir(self.nombre, "datos_crudos", datos)
            return datos
        except Exception as e:
            print(f"[{self.nombre}] Yahoo saturado: {e}")
            if ticker in CACHE:
                print(f"[{self.nombre}] Usando datos del CACHE")
                return CACHE[ticker][0]
            return {"error": str(e)}
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
            "empresa":obtener_texto(info,"longName"),
            "precio":obtener(info,"currentPrice"),
            "moneda":obtener_texto(info,"currency"),
            "sector":obtener_texto(info,"sector"),
            "activo_circulante":obtener(balance,"Current Assets"),
            "pasivo_circulante":obtener(balance,"Current Liabilities"),
            "activo_total":obtener(balance,"Total Assets"),
            "pasivo_total":obtener(balance,"Total Liabilities Net Minority Interest"),
            "patrimonio":obtener(balance,"Total Stockholder Equity"),
            "utilidades_retenidas":obtener(balance,"Retained Earnings"),
            "ventas":obtener(resultados,"Total Revenue"),
            "utilidad_neta":obtener(resultados,"Net Income"),
            "utilidad_operativa":obtener(resultados,"Operating Income"),
            "flujo_operativo":obtener(flujo,"Operating Cash Flow"),
            "capitalizacion_mercado":obtener(info,"marketCap"),
            "acciones_en_circulacion":obtener(info,"sharesOutstanding"),
        }
        CACHE[ticker] = (time.time(), datos)
        memoria.escribir(self.nombre, "datos_crudos", datos)
        return datos

# ================= AGENTE 2: ANALISTA =================
class AgenteAnalista:
    """Agente 2: Solo calcula ratios, no decide nada"""
    nombre = "AGENTE-ANALISTA"
    def ejecutar(self, datos, memoria):
        def div(a,b): return a/b if b!=0 else 0
        cap = datos.get("activo_circulante", 0) - datos.get("pasivo_circulante", 0)
        ratios = {
            "capital_trabajo": cap,
            "liquidez": div(datos.get("activo_circulante", 0), datos.get("pasivo_circulante", 0)),
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
        X5 = ratios["rotacion_activos"]
        cap_mercado = datos.get("capitalizacion_mercado", 0) or 0
        if cap_mercado > 0:
            X4 = div(cap_mercado, datos["pasivo_total"])
            z_altman = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
            modelo_z = "Z Altman Original (publica - usa mercado)"
        else:
            X4 = div(datos["patrimonio"], datos["pasivo_total"])
            z_altman = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5
            modelo_z = "Z' Altman (privada - valor en libros)"
        z_springate = 1.03*X1 + 3.07*X3 + 0.66*div(datos["utilidad_neta"], datos["pasivo_circulante"]) + 0.4*X5
        if z_altman < 1.23: nivel, color, prob = "🔴 CRITICO", "red", 0.85
        elif z_altman < 2.90: nivel, color, prob = "🟡 ALERTA", "orange", 0.45
        else: nivel, color, prob = "🟢 SALUDABLE", "green", 0.10
        if prob < 0.30:
            etiqueta_riesgo = "Riesgo Bajo"
        elif prob < 0.60:
            etiqueta_riesgo = "Riesgo Moderado - Zona Gris"
        else:
            etiqueta_riesgo = "Riesgo Alto"
        pred = {"z_altman": round(z_altman,2), "z_springate": round(z_springate,2),
                "nivel": nivel, "color": color, "prob_insolvencia": prob,
                "modelo_z": modelo_z, "etiqueta_riesgo": etiqueta_riesgo}
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

# ===== WEB =====
@app.route("/")
def inicio():
    return render_template("index.html", datos=MEMORIA.historial, ciclos=MEMORIA.ciclos, error=None)

@app.route("/buscar")
def buscar():
    ticker = request.args.get("ticker","").strip().upper()
    if not ticker:
        return jsonify({"error":"Escribe un ticker"}), 400

    # Si ya esta en memoria, no le pedimos a Yahoo
    for item in MEMORIA.historial:
        if item.get("ticker") == ticker:
            return jsonify(item)

    try:
        # AQUI VA TU CODIGO QUE YA TIENES PARA PEDIRLE A YAHOO
        # ... no lo borres, dejalo tal cual ...
        pass
    except Exception as e:
        if "429" in str(e) or "Too Many" in str(e) or "Rate" in str(e):
            return jsonify({"error":"Yahoo esta saturado ahorita, espera 15 min y prueba con AAPL que ya esta guardado"}), 429
        return jsonify({"error":"Yahoo esta saturado por tantas consultas, espera 20 min y prueba con AAPL que ya esta guardado"}), 429
        
    ticker = request.args.get("ticker","").strip()
    try:
        resultado = SUPERVISOR.ejecutar_flujo(ticker, MEMORIA)
        if resultado and resultado not in MEMORIA.historial:
            MEMORIA.historial.insert(0, resultado)
        return render_template("index.html", datos=MEMORIA.historial, ciclos=MEMORIA.ciclos, error=None)
    except Exception as e:
        return render_template("index.html", datos=MEMORIA.historial, ciclos=MEMORIA.ciclos, error=f"Ticker '{ticker}' no encontrado. Error: {str(e)[:120]}")
        return render_template("index.html", datos=MEMORIA.historial, ciclos=MEMORIA.ciclos, error=f"Ticker '{ticker}' no encontrado. Error: {str(e)[:120]}")
@app.route("/ping")
def ping():return "Aceptar"

@app.route("/acerca")
def acerca():return render_template("acerca.html")
    
@app.route("/api/ticker/<ticker>")
def api_ticker(ticker):
    try:
        cacheado = esta_en_cache(ticker)
        if cacheado:
            return jsonify(cacheado)
        time.sleep(1)        
        resultado = SUPERVISOR.ejecutar_flujo(ticker, MEMORIA)
        # Agregar historial 6 meses para las gráficas
        try:
            import yfinance as yf
            h = yf.Ticker(ticker).history(period="6mo")
            if not h.empty:
                fechas = [str(d.date()) for d in h.index]
                precios = [round(float(x), 2) for x in h['Close'].tolist()]
                resultado["historial_precio"] = {"fechas": fechas, "precios": precios}
        except Exception as e:
            print("Error historial:", e)
        # Limpiar NaN / Inf para que el JSON sea válido
        import math
        def limpiar(o):
            if isinstance(o, dict):
                return {k: limpiar(v) for k, v in o.items()}
            if isinstance(o, list):
                return [limpiar(v) for v in o]
            if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
                return None
            return o            
        resultado = limpiar(resultado)
        guardar_en_cache(ticker, resultado)        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/api/buscar_nombre")
def buscar_nombre():
    from flask import request
    import requests, re
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Escribe un nombre"}), 400
    mapa = {
        "CEMEX": "CEMEXCPO.MX",
        "CEMEX.MX": "CEMEXCPO.MX",
        "WALMART": "WALMEX.MX",
        "AMERICA MOVIL": "AMXB.MX",
        "AMXL": "AMXB.MX",
        "CEMEX": "CEMEXCPO.MX",
        "CEMEX.MX": "CEMEXCPO.MX",
        "WALMART": "WALMEX.MX",
        "AMERICA MOVIL": "AMXB.MX",
        "AMXL": "AMXB.MX",
        "MELI": "MELI",
        "MERCADO LIBRE": "MELI",
        "MERCADOLIBRE": "MELI",
        "MELIA": "MEL.MC",
        "MELIA HOTELS": "MEL.MC",
        "LIVERPOOL": "LIVEPOLC-1.MX",
        "LIVERPOOL MEXICO": "LIVEPOLC-1.MX",
        "EL PUERTO DE LIVERPOOL": "LIVEPOLC-1.MX",
        "LIVEPOL": "LIVEPOLC-1.MX",
    }
    clave = q.upper().strip()
    if clave in mapa:
        return jsonify({"ticker": mapa[clave], "nombre": q})
    def buscar_yahoo(termino):
        try:
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            r = requests.get(url, params={"q": termino, "quotesCount": 10, "newsCount": 0}, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            data = r.json()
            quotes = data.get("quotes", [])
            acciones = [x for x in quotes if x.get("quoteType") == "EQUITY" and x.get("symbol")]
            if not acciones:
                acciones = quotes
            if acciones:
                for x in acciones:
                    nombre = (x.get("shortname","") + " " + x.get("longname","")).lower()
                    if termino.lower() in nombre or nombre in termino.lower():
                        return x["symbol"]
                return acciones[0]["symbol"]
        except Exception as e:
            print("Error buscar_yahoo:", e)
        return None
    ticker = buscar_yahoo(q)
    if not ticker:
        ticker = buscar_yahoo(q + " Mexico")
    if not ticker:
        ticker = q.upper()
    return jsonify({"ticker": ticker, "nombre": q})

@app.route("/api/sugerencias")
def sugerencias():
    from flask import request
    import requests
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        r = requests.get(url, params={"q": q, "quotesCount": 15, "newsCount": 0}, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        data = r.json()
        lista = []
        for x in data.get("quotes", []):
            if x.get("quoteType") != "EQUITY" or not x.get("symbol"):
                continue
            lista.append({
                "ticker": x.get("symbol"),
                "nombre": x.get("shortname") or x.get("longname") or x.get("symbol"),
                "bolsa": x.get("exchDisp") or x.get("exchange") or "",
                "moneda": x.get("currency") or ""
            })
        return jsonify(lista)
    except Exception as e:
        print("Error sugerencias:", e)
        return jsonify([])

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
