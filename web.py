"""
Public price web for Cooperativa Agroindustrial Villa Rica Golden Coffee Ltda.
Serves a price calculator page based on the CC Golden Excel formulas.
"""
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Average rendimiento per zone (source: CC Golden 2019.xlsx - Perg Org Proc Indiv)
ZONAS = [
    {"zona": "AL TO YURINAKI", "rendimiento": 0.720},
    {"zona": "ALTO BOCAZ", "rendimiento": 0.719},
    {"zona": "ALTO CACAZU", "rendimiento": 0.7275},
    {"zona": "ALTO CHINARI", "rendimiento": 0.750},
    {"zona": "ALTO CHURUMAZU", "rendimiento": 0.725},
    {"zona": "ALTO ENTAZ", "rendimiento": 0.7159},
    {"zona": "ALTO LIMEÑA", "rendimiento": 0.7093},
    {"zona": "ALTO PUMPORIANI", "rendimiento": 0.660},
    {"zona": "ALTO SOGORMO", "rendimiento": 0.7172},
    {"zona": "ALTO UBIRIKI", "rendimiento": 0.7304},
    {"zona": "ALTO UBIRIKI SECTOR 71", "rendimiento": 0.720},
    {"zona": "ALTO UBIRIKI-LAS PALMAS", "rendimiento": 0.720},
    {"zona": "ALTO YURINAKI", "rendimiento": 0.7317},
    {"zona": "BAJO BOCAZ", "rendimiento": 0.7033},
    {"zona": "BAJO ENTAZ", "rendimiento": 0.7114},
    {"zona": "BAJO ENTAZ PTE PAUCARTAMBO", "rendimiento": 0.7029},
    {"zona": "BAJO SOGORMO", "rendimiento": 0.692},
    {"zona": "C.C.N.N. ÑAGAZU", "rendimiento": 0.7174},
    {"zona": "CAMONASHARI", "rendimiento": 0.6969},
    {"zona": "CANAL DE PIEDRA", "rendimiento": 0.7296},
    {"zona": "CC NN EL MILAGRO", "rendimiento": 0.725},
    {"zona": "CC NN VILLA MARIA", "rendimiento": 0.7167},
    {"zona": "CC.NN MILAGROS", "rendimiento": 0.738},
    {"zona": "CEDRO PAMPA", "rendimiento": 0.6425},
    {"zona": "CENTRO BOCAZ", "rendimiento": 0.730},
    {"zona": "ENEÑAS", "rendimiento": 0.7305},
    {"zona": "ENEÑAS KM. 7.5", "rendimiento": 0.7343},
    {"zona": "ENTAZ", "rendimiento": 0.7002},
    {"zona": "KM 12, ENEÑAS", "rendimiento": 0.738},
    {"zona": "KM 6-ALTO ENEÑAS", "rendimiento": 0.7293},
    {"zona": "KM.06- ALTO ENEÑAS", "rendimiento": 0.7192},
    {"zona": "LA LIMEÑA", "rendimiento": 0.7467},
    {"zona": "LAS PALMAS ALTO UBIRIKI", "rendimiento": 0.7277},
    {"zona": "LAS PALMAS UBIRIKI", "rendimiento": 0.7275},
    {"zona": "LOS ANGELES", "rendimiento": 0.6536},
    {"zona": "LOS MELLISOS", "rendimiento": 0.7197},
    {"zona": "MAYME", "rendimiento": 0.7067},
    {"zona": "MELLIZOS", "rendimiento": 0.7261},
    {"zona": "OCONAL", "rendimiento": 0.7347},
    {"zona": "PALMA BOCAZ", "rendimiento": 0.7233},
    {"zona": "PAMPA ENCANTADA", "rendimiento": 0.7367},
    {"zona": "PTE. PAUCARTAMBO", "rendimiento": 0.7175},
    {"zona": "RAMAZU", "rendimiento": 0.700},
    {"zona": "RIO LA SAL PTE. PAUCARTAMBO", "rendimiento": 0.730},
    {"zona": "SAN JUAN DE CACAZU", "rendimiento": 0.7421},
    {"zona": "SANCHIRIO PALOMAR", "rendimiento": 0.6811},
    {"zona": "SANTA ROSA DE CAMONASHARI", "rendimiento": 0.670},
    {"zona": "SATINAKI - UBIRIKI", "rendimiento": 0.6639},
    {"zona": "SECTOR 71 ALTO UBIRIKI", "rendimiento": 0.7311},
    {"zona": "STA. HERMINIA PALOMAR", "rendimiento": 0.715},
    {"zona": "TACTAZU", "rendimiento": 0.730},
    {"zona": "UBIRIKI", "rendimiento": 0.7109},
    {"zona": "VALLE BELEN", "rendimiento": 0.7356},
    {"zona": "VILLA RICA", "rendimiento": 0.7124},
    {"zona": "VILLA RICA EL MILAGRO", "rendimiento": 0.740},
    {"zona": "YEZU", "rendimiento": 0.7435},
    {"zona": "ZONA PATRIA", "rendimiento": 0.690},
    {"zona": "ÑAGAZU", "rendimiento": 0.7172},
]

def calcular_precios(bolsa, dolar):
    """
    Formulas from CC Golden 2019.xlsx - Precio sheet:
      Precio Bolsa         = bolsa × dólar
      Costos proceso (cc)  = 29 × dólar
      Pergamino seco       = (Precio Bolsa - cc) / 60      [fixed, international bag]
      Oro verde            = Precio Bolsa / 46             [local QQ = 46 kg]
      Pergamino todo costo = Precio Bolsa / 60
      Lata (mote)          = pergamino_seco × 7.3
      Mote                 = lata - 3.5
      Cerezo               = (Precio Bolsa / 60) / (280/55.2) - (41/280)

    Per-zone pergamino price uses actual rendimiento:
      Pergamino zona = (Precio Bolsa - cc) × rendimiento / 46
    """
    precio_bolsa = bolsa * dolar
    cc = 29 * dolar
    pergamino_seco = (precio_bolsa - cc) / 60
    oro_verde = precio_bolsa / 46
    pergamino_todo_costo = precio_bolsa / 60
    lata = pergamino_seco * 7.3
    mote = lata - 3.5
    cerezo = (precio_bolsa / 60) / (280 / 55.2) - (41 / 280)

    zonas_calc = []
    for z in ZONAS:
        r = z["rendimiento"]
        precio_zona = round((precio_bolsa - cc) * r / 46, 4)
        zonas_calc.append({
            "zona": z["zona"],
            "rendimiento": round(r * 100, 2),
            "precio_kg": precio_zona,
        })

    return {
        "precio_bolsa": round(precio_bolsa, 2),
        "cc": round(cc, 2),
        "pergamino_seco": round(pergamino_seco, 4),
        "oro_verde": round(oro_verde, 4),
        "pergamino_todo_costo": round(pergamino_todo_costo, 4),
        "lata": round(lata, 4),
        "mote": round(mote, 4),
        "cerezo": round(cerezo, 4),
        "zonas": zonas_calc,
    }


HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Precios Café — CC Golden</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f4f1eb;
      color: #2d2416;
      min-height: 100vh;
    }

    header {
      background: linear-gradient(135deg, #3b1f06 0%, #6b3a1f 100%);
      color: #fff;
      padding: 24px 32px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    header .logo { font-size: 2rem; }
    header h1 { font-size: 1.3rem; font-weight: 700; line-height: 1.3; }
    header p { font-size: 0.85rem; opacity: 0.8; margin-top: 2px; }

    .container { max-width: 960px; margin: 0 auto; padding: 32px 16px; }

    /* Inputs */
    .inputs-card {
      background: #fff;
      border-radius: 12px;
      padding: 28px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      margin-bottom: 28px;
    }
    .inputs-card h2 { font-size: 1rem; color: #6b3a1f; margin-bottom: 20px; text-transform: uppercase; letter-spacing: .05em; }
    .inputs-row { display: flex; gap: 20px; flex-wrap: wrap; }
    .input-group { flex: 1; min-width: 180px; }
    .input-group label { display: block; font-size: 0.82rem; font-weight: 600; color: #6b3a1f; margin-bottom: 6px; text-transform: uppercase; }
    .input-group input {
      width: 100%;
      padding: 12px 14px;
      border: 2px solid #e0d5c5;
      border-radius: 8px;
      font-size: 1.2rem;
      font-weight: 700;
      color: #2d2416;
      background: #faf8f5;
      transition: border-color .2s;
    }
    .input-group input:focus { outline: none; border-color: #6b3a1f; }
    .input-hint { font-size: 0.75rem; color: #999; margin-top: 4px; }

    /* Summary prices */
    .prices-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .price-card {
      background: #fff;
      border-radius: 12px;
      padding: 20px 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      text-align: center;
      border-top: 4px solid #c8a96e;
    }
    .price-card.highlight { border-top-color: #3b1f06; }
    .price-card .label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: #999; letter-spacing: .04em; margin-bottom: 8px; }
    .price-card .value { font-size: 1.6rem; font-weight: 800; color: #3b1f06; }
    .price-card .unit { font-size: 0.78rem; color: #aaa; margin-top: 2px; }

    /* Zone table */
    .table-card {
      background: #fff;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    .table-card h2 { font-size: 1rem; color: #6b3a1f; margin-bottom: 16px; text-transform: uppercase; letter-spacing: .05em; }

    .search-box {
      width: 100%;
      padding: 10px 14px;
      border: 2px solid #e0d5c5;
      border-radius: 8px;
      font-size: 0.9rem;
      margin-bottom: 16px;
      background: #faf8f5;
    }
    .search-box:focus { outline: none; border-color: #6b3a1f; }

    table { width: 100%; border-collapse: collapse; }
    th {
      text-align: left;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: #999;
      padding: 8px 12px;
      border-bottom: 2px solid #f0ebe0;
    }
    td { padding: 11px 12px; border-bottom: 1px solid #f0ebe0; font-size: 0.92rem; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #faf7f0; }
    td.zona-name { font-weight: 600; }
    td.rendimiento { color: #888; font-size: 0.85rem; }
    td.precio { font-weight: 800; color: #3b1f06; font-size: 1.05rem; text-align: right; }
    th:last-child { text-align: right; }

    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 700;
      background: #f0ebe0;
      color: #6b3a1f;
    }

    footer {
      text-align: center;
      padding: 24px;
      font-size: 0.8rem;
      color: #bbb;
      margin-top: 16px;
    }
  </style>
</head>
<body>

<header>
  <div class="logo">☕</div>
  <div>
    <h1>Cooperativa Agroindustrial Villa Rica Golden Coffee Ltda.</h1>
    <p>Productores &amp; Exportadores de café de origen — Precios del día</p>
  </div>
</header>

<div class="container">

  <div class="inputs-card">
    <h2>Parámetros del día</h2>
    <div class="inputs-row">
      <div class="input-group">
        <label>Bolsa ($ / QQ)</label>
        <input type="number" id="bolsa" value="162" step="0.01" min="0"/>
        <div class="input-hint">Precio bolsa internacional en dólares por quintal</div>
      </div>
      <div class="input-group">
        <label>Tipo de cambio (S/. / $)</label>
        <input type="number" id="dolar" value="3.79" step="0.001" min="0"/>
        <div class="input-hint">Tipo de cambio del día</div>
      </div>
    </div>
  </div>

  <div class="prices-grid" id="prices-grid">
    <!-- filled by JS -->
  </div>

  <div class="table-card">
    <h2>Precio de pergamino seco por zona</h2>
    <input class="search-box" type="text" id="search" placeholder="Buscar zona..."/>
    <table id="zona-table">
      <thead>
        <tr>
          <th>Zona</th>
          <th>Rendimiento</th>
          <th>Precio S/. / kg</th>
        </tr>
      </thead>
      <tbody id="zona-body"></tbody>
    </table>
  </div>

</div>

<footer>
  Cooperativa Agroindustrial Villa Rica Golden Coffee Ltda. · Precios referenciales calculados con fórmula CC Golden
</footer>

<script>
const ZONAS = {{ zonas_json | safe }};

function fmt(n, dec=4) {
  return parseFloat(n).toFixed(dec);
}

function calcular(bolsa, dolar) {
  const precio_bolsa = bolsa * dolar;
  const cc = 29 * dolar;
  const pergamino_seco = (precio_bolsa - cc) / 60;
  const oro_verde = precio_bolsa / 46;
  const pergamino_todo_costo = precio_bolsa / 60;
  const lata = pergamino_seco * 7.3;
  const mote = lata - 3.5;
  const cerezo = (precio_bolsa / 60) / (280 / 55.2) - (41 / 280);

  return { precio_bolsa, cc, pergamino_seco, oro_verde, pergamino_todo_costo, lata, mote, cerezo };
}

function renderPrices(bolsa, dolar) {
  const p = calcular(bolsa, dolar);
  const grid = document.getElementById('prices-grid');
  grid.innerHTML = `
    <div class="price-card highlight">
      <div class="label">Precio Bolsa</div>
      <div class="value">S/. ${fmt(p.precio_bolsa, 2)}</div>
      <div class="unit">por quintal (60 kg)</div>
    </div>
    <div class="price-card highlight">
      <div class="label">Pergamino Seco</div>
      <div class="value">S/. ${fmt(p.pergamino_seco, 4)}</div>
      <div class="unit">por kg</div>
    </div>
    <div class="price-card">
      <div class="label">Pergamino Todo Costo</div>
      <div class="value">S/. ${fmt(p.pergamino_todo_costo, 4)}</div>
      <div class="unit">por kg</div>
    </div>
    <div class="price-card">
      <div class="label">Oro Verde</div>
      <div class="value">S/. ${fmt(p.oro_verde, 4)}</div>
      <div class="unit">por kg</div>
    </div>
    <div class="price-card">
      <div class="label">Mote</div>
      <div class="value">S/. ${fmt(p.mote, 4)}</div>
      <div class="unit">por kg</div>
    </div>
    <div class="price-card">
      <div class="label">Lata (mote limpio)</div>
      <div class="value">S/. ${fmt(p.lata, 4)}</div>
      <div class="unit">por lata</div>
    </div>
    <div class="price-card">
      <div class="label">Cerezo</div>
      <div class="value">S/. ${fmt(p.cerezo, 4)}</div>
      <div class="unit">por kg</div>
    </div>
    <div class="price-card">
      <div class="label">Costos de Proceso</div>
      <div class="value">S/. ${fmt(p.cc, 2)}</div>
      <div class="unit">por quintal</div>
    </div>
  `;
}

function renderZonas(bolsa, dolar, filter='') {
  const precio_bolsa = bolsa * dolar;
  const cc = 29 * dolar;
  const body = document.getElementById('zona-body');
  const rows = ZONAS
    .filter(z => z.zona.toLowerCase().includes(filter.toLowerCase()))
    .map(z => {
      const precio = ((precio_bolsa - cc) * z.rendimiento / 46).toFixed(4);
      return `<tr>
        <td class="zona-name">${z.zona}</td>
        <td class="rendimiento"><span class="badge">${(z.rendimiento*100).toFixed(2)}%</span></td>
        <td class="precio">S/. ${precio}</td>
      </tr>`;
    });
  body.innerHTML = rows.join('');
}

function update() {
  const bolsa = parseFloat(document.getElementById('bolsa').value) || 0;
  const dolar = parseFloat(document.getElementById('dolar').value) || 0;
  const filter = document.getElementById('search').value;
  renderPrices(bolsa, dolar);
  renderZonas(bolsa, dolar, filter);
}

document.getElementById('bolsa').addEventListener('input', update);
document.getElementById('dolar').addEventListener('input', update);
document.getElementById('search').addEventListener('input', update);

update();
</script>
</body>
</html>"""


@app.route("/")
def index():
    import json
    zonas_json = json.dumps(ZONAS, ensure_ascii=False)
    return render_template_string(HTML, zonas_json=zonas_json)


@app.route("/api/precios")
def api_precios():
    bolsa = float(request.args.get("bolsa", 162))
    dolar = float(request.args.get("dolar", 3.79))
    return jsonify(calcular_precios(bolsa, dolar))


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
