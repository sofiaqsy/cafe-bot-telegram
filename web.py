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
        zonas_calc.append({"zona": z["zona"], "rendimiento": round(r * 100, 2), "precio_kg": precio_zona})
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
  <title>Precios del dia — CC Golden Coffee</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f2ede4; color: #2d2416; }

    /* TOP BAR */
    .topbar {
      background: #2a1204;
      border-bottom: 1px solid #1a0b02;
      padding: 10px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .topbar .brand { display: flex; align-items: center; gap: 12px; }
    .topbar .brand-icon {
      width: 36px; height: 36px;
      background: rgba(255,255,255,0.1);
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
    }
    .topbar .brand-icon svg { width: 20px; height: 20px; fill: #c8a96e; }
    .topbar .brand-name { font-size: 1rem; font-weight: 800; color: #f0e6d0; line-height: 1.1; }
    .topbar .brand-sub  { font-size: 0.75rem; color: rgba(255,255,255,0.45); }

    /* NAVBAR */
    nav {
      background: #3b1f06;
      padding: 0 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0;
      height: 52px;
    }
    .nav-inputs {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }
    .nav-inputs label {
      color: rgba(255,255,255,0.7);
      font-size: 0.78rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .nav-inputs input {
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.25);
      border-radius: 6px;
      color: #fff;
      font-size: 0.95rem;
      font-weight: 700;
      padding: 5px 10px;
      width: 90px;
      text-align: center;
    }
    .nav-inputs input:focus { outline: none; border-color: #c8a96e; background: rgba(255,255,255,0.2); }
    .nav-links { display: flex; align-items: center; gap: 4px; }
    .nav-links a {
      color: rgba(255,255,255,0.75);
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 500;
      padding: 0 14px;
      height: 52px;
      display: flex;
      align-items: center;
      border-bottom: 3px solid transparent;
      transition: color .15s, border-color .15s;
    }
    .nav-links a:hover, .nav-links a.active { color: #fff; border-bottom-color: #c8a96e; }

    /* LAYOUT */
    .container { max-width: 1100px; margin: 0 auto; padding: 28px 16px; }

    /* CALCULATOR */
    .main-grid { display: grid; grid-template-columns: 1fr 320px; gap: 20px; margin-bottom: 24px; }
    @media (max-width: 800px) { .main-grid { grid-template-columns: 1fr; } }

    .card {
      background: #fff;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 1px 8px rgba(0,0,0,0.07);
    }
    .card-title {
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: #3b1f06;
      margin-bottom: 20px;
    }

    .calc-fields { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 20px; }
    .field { flex: 1; min-width: 140px; }
    .field label {
      display: block;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: #888;
      margin-bottom: 6px;
    }
    .field select, .field input[type=number] {
      width: 100%;
      padding: 10px 12px;
      border: 1.5px solid #e0d5c5;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 600;
      color: #2d2416;
      background: #faf8f5;
      appearance: auto;
    }
    .field select:focus, .field input:focus { outline: none; border-color: #3b1f06; }
    .field-hint { font-size: 0.71rem; color: #bbb; margin-top: 4px; }

    .calc-result-bar {
      background: #3b1f06;
      border-radius: 10px;
      padding: 18px 22px;
    }
    .calc-result-bar .label { color: rgba(255,255,255,0.65); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
    .calc-result-bar .amount { color: #f5c842; font-size: 2rem; font-weight: 800; }
    .calc-result-bar .price-kg { color: rgba(255,255,255,0.55); font-size: 0.78rem; margin-top: 4px; }

    /* PROMO CARD */
    .promo-card {
      background: #3b1f06;
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .promo-card img { width: 100%; height: 180px; object-fit: cover; opacity: .85; }
    .promo-body { padding: 18px; flex: 1; }
    .promo-tag { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; color: #c8a96e; margin-bottom: 6px; }
    .promo-title { font-size: 1.1rem; font-weight: 800; color: #fff; line-height: 1.3; }
    .promo-sub { font-size: 0.8rem; color: rgba(255,255,255,0.6); margin-top: 6px; }

    /* INDICATORS */
    .indicators { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
    @media (max-width: 600px) { .indicators { grid-template-columns: 1fr; } }
    .ind-card {
      background: #fff;
      border-radius: 10px;
      padding: 18px 20px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.06);
      border-top: 3px solid #e0d5c5;
    }
    .ind-card.primary { border-top-color: #3b1f06; }
    .ind-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: #aaa; margin-bottom: 8px; }
    .ind-value { font-size: 1.55rem; font-weight: 800; color: #3b1f06; }
    .ind-unit  { font-size: 0.75rem; color: #bbb; margin-top: 3px; }

    /* ZONE TABLE */
    .zone-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 1px 8px rgba(0,0,0,0.07); }
    .zone-toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
    .zone-toolbar input[type=text] {
      flex: 1;
      min-width: 200px;
      padding: 9px 14px;
      border: 1.5px solid #e0d5c5;
      border-radius: 8px;
      font-size: 0.88rem;
      background: #faf8f5;
    }
    .zone-toolbar input:focus { outline: none; border-color: #3b1f06; }
    .sort-label { font-size: 0.78rem; color: #888; font-weight: 600; white-space: nowrap; }
    .zone-toolbar select {
      padding: 9px 12px;
      border: 1.5px solid #e0d5c5;
      border-radius: 8px;
      font-size: 0.85rem;
      background: #faf8f5;
      font-weight: 600;
    }
    .zone-toolbar select:focus { outline: none; border-color: #3b1f06; }

    table { width: 100%; border-collapse: collapse; }
    th {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: #aaa;
      padding: 8px 12px;
      border-bottom: 2px solid #f0ebe0;
      text-align: left;
    }
    th.right { text-align: right; }
    td { padding: 12px 12px; border-bottom: 1px solid #f5f0e8; vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #faf7f0; }

    td.zona-name { font-weight: 700; font-size: 0.9rem; }
    td.rend-cell { width: 220px; }
    .rend-wrap { display: flex; align-items: center; gap: 10px; }
    .rend-pct { font-size: 0.8rem; font-weight: 700; color: #6b3a1f; min-width: 44px; }
    .rend-bar-bg { flex: 1; height: 6px; background: #f0ebe0; border-radius: 3px; overflow: hidden; }
    .rend-bar    { height: 100%; background: #c8a96e; border-radius: 3px; }
    td.precio-cell { font-weight: 800; font-size: 1rem; color: #3b1f06; text-align: right; }
    td.action-cell { text-align: right; width: 90px; }
    .btn-ver {
      background: none;
      border: 1.5px solid #e0d5c5;
      border-radius: 6px;
      padding: 5px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      color: #6b3a1f;
      cursor: pointer;
      transition: all .15s;
    }
    .btn-ver:hover { background: #f5f0e8; border-color: #c8a96e; }

    /* detail row */
    .detail-row td { background: #faf7f0; font-size: 0.82rem; color: #666; padding: 8px 12px 12px 12px; }
    .detail-grid { display: flex; gap: 24px; flex-wrap: wrap; }
    .detail-item span { display: block; font-size: 0.7rem; text-transform: uppercase; letter-spacing: .05em; color: #aaa; font-weight: 700; margin-bottom: 2px; }
    .detail-item strong { font-size: 0.9rem; color: #3b1f06; }

    /* PAGINATION */
    .pagination { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-top: 16px; font-size: 0.82rem; color: #888; }
    .pg-info { margin-right: 8px; }
    .btn-pg {
      border: 1.5px solid #e0d5c5;
      background: #fff;
      border-radius: 6px;
      width: 32px; height: 32px;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer;
      font-size: 0.85rem;
      color: #3b1f06;
      font-weight: 700;
      transition: all .15s;
    }
    .btn-pg:hover:not(:disabled) { background: #f5f0e8; border-color: #c8a96e; }
    .btn-pg:disabled { opacity: 0.35; cursor: default; }

    footer { text-align: center; padding: 24px; font-size: 0.78rem; color: #bbb; }
  </style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <div class="brand">
    <div class="brand-icon">
      <svg viewBox="0 0 24 24"><path d="M2 21v-2h2V5h14v2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2v6h2v2H2zm4-2h8V7H6v12zm10-6h2V9h-2v4z"/></svg>
    </div>
    <div>
      <div class="brand-name">Finca Rosal</div>
      <div class="brand-sub">Nuestros cafes especiales — Precios del dia</div>
    </div>
  </div>
</div>

<!-- NAVBAR -->
<nav>
  <div class="nav-inputs">
    <label>Bolsa y Cambio</label>
    <input type="number" id="bolsa" value="162" step="0.01" min="0" placeholder="$"/>
    <input type="number" id="dolar" value="3.79" step="0.001" min="0" placeholder="S/."/>
  </div>
  <div class="nav-links">
    <a href="#inicio" class="active">Inicio</a>
    <a href="#mercado">Mercado</a>
    <a href="#zonas">Zonas</a>
  </div>
</nav>

<div class="container" id="inicio">

  <!-- CALCULATOR + PROMO -->
  <div class="main-grid">
    <div class="card">
      <div class="card-title">Calculadora de Pago</div>
      <div class="calc-fields">
        <div class="field">
          <label>Tipo de Cafe</label>
          <select id="calc-tipo">
            <option value="pergamino">Pergamino Seco</option>
            <option value="mote">Mote</option>
            <option value="cerezo">Cerezo</option>
            <option value="oro_verde">Oro Verde</option>
          </select>
        </div>
        <div class="field" id="zona-group">
          <label>Zona</label>
          <select id="calc-zona"></select>
          <div class="field-hint">Solo aplica para Pergamino Seco</div>
        </div>
        <div class="field">
          <label>Kg Netos</label>
          <input type="number" id="calc-kg" value="" step="0.1" min="0" placeholder="0.0"/>
        </div>
      </div>
      <div class="calc-result-bar">
        <div class="label">Total a pagar</div>
        <div class="amount" id="res-total">S/. 0.00</div>
        <div class="price-kg" id="res-kg-label"></div>
      </div>
    </div>

    <div class="promo-card">
      <img src="https://images.unsplash.com/photo-1447933601403-0c6688de566e?w=600&q=80" alt="Cafe"/>
      <div class="promo-body">
        <div class="promo-tag">Informacion</div>
        <div class="promo-title">Cooperativa Villa Rica Golden Coffee</div>
        <div class="promo-sub">Productores y Exportadores de cafe de origen — Villa Rica, Peru</div>
      </div>
    </div>
  </div>

  <!-- KEY INDICATORS -->
  <div id="mercado">
    <div class="card-title" style="margin-bottom:14px;">Indicadores Clave</div>
    <div class="indicators">
      <div class="ind-card primary">
        <div class="ind-label">Precio Bolsa</div>
        <div class="ind-value" id="ind-bolsa">S/. —</div>
        <div class="ind-unit">por quintal (60 kg)</div>
      </div>
      <div class="ind-card">
        <div class="ind-label">Pergamino Todo Costo</div>
        <div class="ind-value" id="ind-perg-costo">S/. —</div>
        <div class="ind-unit">por kg</div>
      </div>
      <div class="ind-card">
        <div class="ind-label">Oro Verde</div>
        <div class="ind-value" id="ind-oro">S/. —</div>
        <div class="ind-unit">por kg</div>
      </div>
    </div>
  </div>

  <!-- ZONE TABLE -->
  <div class="zone-card" id="zonas">
    <div class="card-title">Precio de Pergamino Seco por Zona</div>
    <div class="zone-toolbar">
      <input type="text" id="search" placeholder="Buscar zona..."/>
      <span class="sort-label">Ordenar por</span>
      <select id="sort-by">
        <option value="zona">Zona (A-Z)</option>
        <option value="rendimiento">Rendimiento</option>
        <option value="precio">Precio</option>
      </select>
    </div>
    <table>
      <thead>
        <tr>
          <th>Zona</th>
          <th>Rendimiento</th>
          <th class="right">Precio S/. / kg</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="zona-body"></tbody>
    </table>
    <div class="pagination">
      <span class="pg-info" id="pg-info"></span>
      <button class="btn-pg" id="pg-first" onclick="goPage(0)">&laquo;</button>
      <button class="btn-pg" id="pg-prev"  onclick="goPage(currentPage-1)">&lsaquo;</button>
      <button class="btn-pg" id="pg-next"  onclick="goPage(currentPage+1)">&rsaquo;</button>
      <button class="btn-pg" id="pg-last"  onclick="goPage(totalPages-1)">&raquo;</button>
    </div>
  </div>

</div>

<footer>
  Cooperativa Agroindustrial Villa Rica Golden Coffee Ltda. &nbsp;&middot;&nbsp; Precios referenciales calculados con formula CC Golden
</footer>

<script>
const ZONAS = {{ zonas_json | safe }};
const PAGE_SIZE = 10;
let currentPage = 0;
let totalPages  = 1;
let filteredZonas = [];

const TIPO_LABELS = { pergamino:'Pergamino Seco', mote:'Mote', cerezo:'Cerezo', oro_verde:'Oro Verde' };

function getPrecioKg(tipo, bolsa, dolar, zona) {
  const pb = bolsa * dolar, cc = 29 * dolar;
  if (tipo === 'pergamino') {
    const z = ZONAS.find(z => z.zona === zona);
    return z ? (pb - cc) * z.rendimiento / 46 : 0;
  }
  if (tipo === 'mote')      return ((pb - cc) / 60 * 7.3) - 3.5;
  if (tipo === 'cerezo')    return (pb / 60) / (280 / 55.2) - (41 / 280);
  if (tipo === 'oro_verde') return pb / 46;
  return 0;
}

function getZonaPrecios(bolsa, dolar) {
  const pb = bolsa * dolar, cc = 29 * dolar;
  return ZONAS.map(z => ({
    zona: z.zona,
    rendimiento: z.rendimiento,
    precio: (pb - cc) * z.rendimiento / 46,
  }));
}

function populateZonaSelect() {
  document.getElementById('calc-zona').innerHTML =
    ZONAS.map(z => `<option value="${z.zona}">${z.zona} (${(z.rendimiento*100).toFixed(2)}%)</option>`).join('');
}

function updateCalc() {
  const bolsa = parseFloat(document.getElementById('bolsa').value) || 0;
  const dolar = parseFloat(document.getElementById('dolar').value) || 0;
  const kg    = parseFloat(document.getElementById('calc-kg').value)  || 0;
  const tipo  = document.getElementById('calc-tipo').value;
  const zona  = document.getElementById('calc-zona').value;

  document.getElementById('zona-group').style.display = tipo === 'pergamino' ? '' : 'none';

  const precio_kg = getPrecioKg(tipo, bolsa, dolar, zona);
  document.getElementById('res-total').textContent = 'S/. ' + (precio_kg * kg).toLocaleString('es-PE', {minimumFractionDigits:2, maximumFractionDigits:2});
  document.getElementById('res-kg-label').textContent = kg > 0 ? `S/. ${precio_kg.toFixed(4)} por kg` : '';
}

function updateIndicators() {
  const bolsa = parseFloat(document.getElementById('bolsa').value) || 0;
  const dolar = parseFloat(document.getElementById('dolar').value) || 0;
  const pb  = bolsa * dolar;
  const cc  = 29 * dolar;
  document.getElementById('ind-bolsa').textContent      = 'S/. ' + pb.toFixed(2);
  document.getElementById('ind-perg-costo').textContent = 'S/. ' + (pb / 60).toFixed(4);
  document.getElementById('ind-oro').textContent        = 'S/. ' + (pb / 46).toFixed(4);
}

function buildFilteredList() {
  const bolsa  = parseFloat(document.getElementById('bolsa').value)  || 0;
  const dolar  = parseFloat(document.getElementById('dolar').value)  || 0;
  const filter = document.getElementById('search').value.toLowerCase();
  const sortBy = document.getElementById('sort-by').value;

  let list = getZonaPrecios(bolsa, dolar)
    .filter(z => z.zona.toLowerCase().includes(filter));

  if (sortBy === 'rendimiento') list.sort((a,b) => b.rendimiento - a.rendimiento);
  else if (sortBy === 'precio') list.sort((a,b) => b.precio - a.precio);
  else list.sort((a,b) => a.zona.localeCompare(b.zona));

  return list;
}

function renderZonas() {
  filteredZonas = buildFilteredList();
  totalPages    = Math.max(1, Math.ceil(filteredZonas.length / PAGE_SIZE));
  currentPage   = Math.min(currentPage, totalPages - 1);

  const start = currentPage * PAGE_SIZE;
  const page  = filteredZonas.slice(start, start + PAGE_SIZE);

  document.getElementById('pg-info').textContent =
    `${start + 1}-${Math.min(start + PAGE_SIZE, filteredZonas.length)} de ${filteredZonas.length}`;

  document.getElementById('pg-first').disabled = currentPage === 0;
  document.getElementById('pg-prev').disabled  = currentPage === 0;
  document.getElementById('pg-next').disabled  = currentPage >= totalPages - 1;
  document.getElementById('pg-last').disabled  = currentPage >= totalPages - 1;

  const MIN_REND = 0.62, MAX_REND = 0.80;
  document.getElementById('zona-body').innerHTML = page.map((z, i) => {
    const pct = ((z.rendimiento - MIN_REND) / (MAX_REND - MIN_REND) * 100).toFixed(1);
    const rowId = 'row-' + (start + i);
    return `
    <tr>
      <td class="zona-name">${z.zona}</td>
      <td class="rend-cell">
        <div class="rend-wrap">
          <span class="rend-pct">${(z.rendimiento*100).toFixed(2)}%</span>
          <div class="rend-bar-bg"><div class="rend-bar" style="width:${pct}%"></div></div>
        </div>
      </td>
      <td class="precio-cell">S/. ${z.precio.toFixed(4)}</td>
      <td class="action-cell">
        <button class="btn-ver" onclick="toggleDetail('${rowId}', '${z.zona}', ${z.rendimiento}, ${z.precio})">Ver mas</button>
      </td>
    </tr>
    <tr class="detail-row" id="${rowId}" style="display:none">
      <td colspan="4">
        <div class="detail-grid">
          <div class="detail-item"><span>Zona</span><strong>${z.zona}</strong></div>
          <div class="detail-item"><span>Rendimiento</span><strong>${(z.rendimiento*100).toFixed(2)}%</strong></div>
          <div class="detail-item"><span>Precio / kg</span><strong>S/. ${z.precio.toFixed(4)}</strong></div>
          <div class="detail-item"><span>Precio / QQ (46kg)</span><strong>S/. ${(z.precio*46).toFixed(2)}</strong></div>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function toggleDetail(rowId, zona, rend, precio) {
  const row = document.getElementById(rowId);
  row.style.display = row.style.display === 'none' ? '' : 'none';
}

function goPage(p) {
  currentPage = Math.max(0, Math.min(p, totalPages - 1));
  renderZonas();
}


function update() {
  updateIndicators();
  updateCalc();
  renderZonas();
}

['bolsa','dolar'].forEach(id => document.getElementById(id).addEventListener('input', update));
document.getElementById('calc-tipo').addEventListener('change', updateCalc);
document.getElementById('calc-zona').addEventListener('change', updateCalc);
document.getElementById('calc-kg').addEventListener('input', updateCalc);
document.getElementById('search').addEventListener('input', () => { currentPage = 0; renderZonas(); });
document.getElementById('sort-by').addEventListener('change', () => { currentPage = 0; renderZonas(); });

populateZonaSelect();
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
