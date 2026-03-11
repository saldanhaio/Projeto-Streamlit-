import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Solar · Energia GD",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

  .main { background: #0d1117; }
  [data-testid="stAppViewContainer"] { background: #0d1117; }
  [data-testid="stSidebar"] { background: #111620 !important; border-right: 1px solid #1e2a3a; }
  [data-testid="stSidebar"] * { color: #c9d1d9 !important; }

  h1, h2, h3 { font-family: 'Syne', sans-serif !important; }

  .kpi-card {
    background: linear-gradient(135deg, #161d2b 0%, #0f1623 100%);
    border: 1px solid #1e2d42;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .kpi-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #00d4aa, #0099ff);
  }
  .kpi-label {
    font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase;
    color: #6e8094; font-family: 'DM Sans', sans-serif; margin-bottom: 8px;
  }
  .kpi-value {
    font-family: 'Syne', sans-serif; font-size: 28px; font-weight: 700;
    color: #e6edf3; line-height: 1;
  }
  .kpi-delta {
    font-size: 12px; margin-top: 6px; color: #6e8094;
  }
  .kpi-delta.positive { color: #00d4aa; }
  .kpi-delta.negative { color: #ff6b6b; }

  .section-title {
    font-family: 'Syne', sans-serif;
    font-size: 16px; font-weight: 700; color: #e6edf3;
    letter-spacing: 0.5px; margin-bottom: 4px;
  }
  .section-sub {
    font-size: 12px; color: #6e8094; margin-bottom: 16px;
  }

  .upload-area {
    background: #111620;
    border: 2px dashed #1e2d42;
    border-radius: 16px;
    padding: 60px 40px;
    text-align: center;
  }
  .upload-title {
    font-family: 'Syne', sans-serif;
    font-size: 32px; font-weight: 800; color: #e6edf3;
    margin-bottom: 8px;
  }
  .upload-sub { font-size: 15px; color: #6e8094; }
  .accent { color: #00d4aa; }

  [data-testid="stFileUploader"] {
    background: #161d2b !important;
    border-radius: 10px !important;
    border: 1px solid #1e2d42 !important;
    padding: 16px !important;
  }
  [data-testid="stFileUploader"] label { color: #c9d1d9 !important; }

  div[data-testid="metric-container"] { display: none; }
  .stPlotlyChart { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

COLORS = {
    "bg":       "#0d1117",
    "card":     "#161d2b",
    "border":   "#1e2d42",
    "teal":     "#00d4aa",
    "blue":     "#0099ff",
    "purple":   "#7c5cbf",
    "orange":   "#f4845f",
    "yellow":   "#f5c518",
    "red":      "#ff6b6b",
    "text":     "#e6edf3",
    "muted":    "#6e8094",
}

PLOTLY_BASE = dict(
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor=COLORS["card"],
    font=dict(family="DM Sans", color=COLORS["text"], size=12),
    margin=dict(l=16, r=16, t=40, b=16),
    xaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"], zerolinecolor=COLORS["border"]),
    yaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"], zerolinecolor=COLORS["border"]),
)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MES_MAP = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

def parse_mes(mes_str):
    if pd.isna(mes_str):
        return pd.NaT
    s = str(mes_str).strip().lower()
    if not s or s in ("nan", "none", "-", ""):
        return pd.NaT
    # formato: jan/25, jan/2025, janeiro/25
    parts = s.replace("-", "/").split("/")
    if len(parts) == 2:
        mes_raw = parts[0][:3]
        m = MES_MAP.get(mes_raw)
        if m is None:
            return pd.NaT
        try:
            y_raw = parts[1].strip()
            y = int("20" + y_raw) if len(y_raw) == 2 else int(y_raw)
            return pd.Timestamp(year=y, month=m, day=1)
        except:
            return pd.NaT
    # tenta pandas genérico como fallback
    try:
        return pd.to_datetime(mes_str, dayfirst=True)
    except:
        return pd.NaT

def clean_numeric(s):
    if pd.isna(s): return np.nan
    s = str(s).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
    try: return float(s)
    except: return np.nan

def fmt_brl(v):
    if pd.isna(v) or v == 0: return "R$ 0"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_kwh(v):
    if pd.isna(v): return "—"
    return f"{v:,.0f} kWh".replace(",", ".")

def fmt_pct(v):
    return f"{v:.1f}%"

def load_df(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, sep=None, engine="python")
    else:
        df = pd.read_excel(file)

    # Drop fully empty rows/cols
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]

    # Normalise column names — handle duplicate raw names first
    seen = {}
    new_cols = []
    for c in df.columns:
        if c in seen:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            new_cols.append(c)
    df.columns = new_cols

    rename = {}
    for c in df.columns:
        cl = c.lower()
        if ("mês" in cl or "mes" in cl) and "Mes" not in rename.values():
            rename[c] = "Mes"
        elif "cliente" in cl and "Cliente" not in rename.values():
            rename[c] = "Cliente"
        elif "faturamento" in cl and "Faturamento" not in rename.values():
            rename[c] = "Faturamento"
        elif "consumida" in cl and "EnergiaConsumida" not in rename.values():
            rename[c] = "EnergiaConsumida"
        elif "compensada" in cl and "EnergiaCompensada" not in rename.values():
            rename[c] = "EnergiaCompensada"
        elif "injetada" in cl and "EnergiaInjetada" not in rename.values():
            rename[c] = "EnergiaInjetada"
        elif "economia" in cl and "Economia" not in rename.values():
            rename[c] = "Economia"
        elif ("crédito" in cl or "credito" in cl) and "acum" in cl and "CreditoAcumulado" not in rename.values():
            rename[c] = "CreditoAcumulado"
        elif ("crédito" in cl or "credito" in cl) and "CreditoMes" not in rename.values():
            rename[c] = "CreditoMes"
    df = df.rename(columns=rename)

    num_cols = ["Faturamento","EnergiaConsumida","EnergiaCompensada",
                "EnergiaInjetada","Economia","CreditoMes","CreditoAcumulado"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)

    if "Mes" in df.columns:
        df["Data"] = df["Mes"].apply(parse_mes)
        df = df.dropna(subset=["Data"])
        df = df.sort_values("Data").reset_index(drop=True)

    return df

def kpi(label, value, delta=None, delta_positive=True):
    delta_html = ""
    if delta is not None:
        cls = "positive" if delta_positive else "negative"
        delta_html = f'<div class="kpi-delta {cls}">{delta}</div>'
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {delta_html}
    </div>"""

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<h2 style="font-family:Syne;font-size:22px;color:#e6edf3;margin-bottom:4px;">⚡ VOLTXS GD</h2>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:12px;color:#6e8094;margin-bottom:24px;">Dashboard de Geração Distribuída</p>', unsafe_allow_html=True)
    st.markdown("---")
    uploaded = st.file_uploader("📂 Importar planilha", type=["xlsx","xls","csv"])
    st.markdown("---")

# ── UPLOAD SCREEN ──────────────────────────────────────────────────────────────
if uploaded is None:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70vh;">
      <div style="font-family:Syne;font-size:52px;margin-bottom:12px;">⚡</div>
      <div class="upload-title">Dashboard <span class="accent">VOLTXS GD</span></div>
      <div class="upload-sub" style="max-width:420px;margin:0 auto 32px;">
        Importe sua planilha com dados de faturamento, energia consumida,
        compensada, injetada, economia e créditos.
      </div>
      <div class="upload-sub" style="font-size:13px;color:#3d5068;">
        ← Use o painel lateral para fazer o upload do arquivo .xlsx ou .csv
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── LOAD DATA ──────────────────────────────────────────────────────────────────
try:
    df = load_df(uploaded)
except Exception as e:
    st.error(f"Erro ao carregar arquivo: {e}")
    st.stop()

# ── FILTERS ────────────────────────────────────────────────────────────────────
with st.sidebar:
    clientes = sorted(df["Cliente"].dropna().unique().tolist()) if "Cliente" in df.columns else []
    sel_clientes = st.multiselect("👤 Cliente", clientes, default=clientes)

    if "Data" in df.columns:
        valid_dates = df["Data"].dropna()
        if len(valid_dates) > 0:
            min_d = valid_dates.min().to_pydatetime()
            max_d = valid_dates.max().to_pydatetime()
            sel_periodo = st.date_input("📅 Período", value=(min_d, max_d), min_value=min_d, max_value=max_d)
        else:
            st.warning("Nenhuma data válida encontrada na coluna Mês.")
            sel_periodo = None
    else:
        sel_periodo = None

    st.markdown("---")
    st.markdown('<p style="font-size:11px;color:#3d5068;">Dados carregados com sucesso ✓</p>', unsafe_allow_html=True)

# filter
dff = df.copy()
if sel_clientes:
    dff = dff[dff["Cliente"].isin(sel_clientes)]
if sel_periodo and len(sel_periodo) == 2:
    dff = dff[(dff["Data"] >= pd.Timestamp(sel_periodo[0])) & (dff["Data"] <= pd.Timestamp(sel_periodo[1]))]

if dff.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

# ── KPIs ────────────────────────────────────────────────────────────────────────
st.markdown('<h1 style="font-family:Syne;font-size:28px;color:#e6edf3;margin-bottom:2px;">Dashboard <span style="color:#00d4aa;">VOLTXS GD</span></h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#6e8094;font-size:13px;margin-bottom:24px;">{len(dff)} registros · {dff["Cliente"].nunique() if "Cliente" in dff.columns else "—"} clientes</p>', unsafe_allow_html=True)

fat_total   = dff["Faturamento"].sum()       if "Faturamento"       in dff.columns else 0
econ_total  = dff["Economia"].sum()          if "Economia"          in dff.columns else 0
cons_total  = dff["EnergiaConsumida"].sum()  if "EnergiaConsumida"  in dff.columns else 0
comp_total  = dff["EnergiaCompensada"].sum() if "EnergiaCompensada" in dff.columns else 0
inj_total   = dff["EnergiaInjetada"].sum()   if "EnergiaInjetada"   in dff.columns else 0
cred_acum   = dff["CreditoAcumulado"].max()  if "CreditoAcumulado"  in dff.columns else 0
taxa_comp   = (comp_total / cons_total * 100) if cons_total > 0 else 0

c1,c2,c3,c4 = st.columns(4)
c1.markdown(kpi("Faturamento Total",   fmt_brl(fat_total)),  unsafe_allow_html=True)
c2.markdown(kpi("Economia Total",      fmt_brl(econ_total),  f"{(econ_total/fat_total*100):.1f}% do faturamento" if fat_total else None), unsafe_allow_html=True)
c3.markdown(kpi("Energia Consumida",   fmt_kwh(cons_total)), unsafe_allow_html=True)
c4.markdown(kpi("Taxa de Compensação", fmt_pct(taxa_comp),   "energia compensada / consumida"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
c5,c6,c7,c8 = st.columns(4)
c5.markdown(kpi("Energia Compensada", fmt_kwh(comp_total)), unsafe_allow_html=True)
c6.markdown(kpi("Energia Injetada",   fmt_kwh(inj_total)),  unsafe_allow_html=True)
c7.markdown(kpi("Crédito Acumulado",  fmt_brl(cred_acum)),  unsafe_allow_html=True)
avg_fat = fat_total / len(dff) if len(dff) > 0 else 0
c8.markdown(kpi("Faturamento Médio/Mês", fmt_brl(avg_fat)), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── CHART HELPERS ─────────────────────────────────────────────────────────────
def apply_base(fig):
    fig.update_layout(**PLOTLY_BASE)
    fig.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"]))
    return fig

# ── ROW 1: Faturamento + Energia ao longo do tempo ────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-title">Faturamento por Mês</div><div class="section-sub">Evolução mensal por cliente</div>', unsafe_allow_html=True)
    grp = dff.groupby(["Data","Cliente"])["Faturamento"].sum().reset_index() if "Cliente" in dff.columns else dff.groupby("Data")["Faturamento"].sum().reset_index()
    color_col = "Cliente" if "Cliente" in grp.columns else None
    fig = px.line(grp, x="Data", y="Faturamento", color=color_col,
                  color_discrete_sequence=[COLORS["teal"],COLORS["blue"],COLORS["orange"],COLORS["yellow"],COLORS["purple"]],
                  markers=True)
    fig.update_traces(line_width=2.5, marker_size=6)
    apply_base(fig)
    fig.update_layout(yaxis_title="R$", xaxis_title="", height=320)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown('<div class="section-title">Energia: Consumida vs Compensada</div><div class="section-sub">Balanço mensal agregado</div>', unsafe_allow_html=True)
    grp2 = dff.groupby("Data")[["EnergiaConsumida","EnergiaCompensada","EnergiaInjetada"]].sum().reset_index()
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=grp2["Data"], y=grp2["EnergiaConsumida"],  name="Consumida",  marker_color=COLORS["blue"],   opacity=0.85))
    fig2.add_trace(go.Bar(x=grp2["Data"], y=grp2["EnergiaCompensada"], name="Compensada", marker_color=COLORS["teal"],   opacity=0.85))
    fig2.add_trace(go.Scatter(x=grp2["Data"], y=grp2["EnergiaInjetada"], name="Injetada",
                              mode="lines+markers", line=dict(color=COLORS["orange"], width=2), marker_size=5))
    apply_base(fig2)
    fig2.update_layout(barmode="group", yaxis_title="kWh", xaxis_title="", height=320)
    st.plotly_chart(fig2, use_container_width=True)

# ── ROW 2: Economia + Composição por cliente ─────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="section-title">Economia Mensal</div><div class="section-sub">Economia gerada em R$ por cliente</div>', unsafe_allow_html=True)
    grp3 = dff.groupby(["Data","Cliente"])["Economia"].sum().reset_index() if "Cliente" in dff.columns else dff.groupby("Data")["Economia"].sum().reset_index()
    color_col3 = "Cliente" if "Cliente" in grp3.columns else None
    fig3 = px.area(grp3, x="Data", y="Economia", color=color_col3,
                   color_discrete_sequence=[COLORS["teal"],COLORS["blue"],COLORS["orange"],COLORS["yellow"],COLORS["purple"]])
    fig3.update_traces(opacity=0.75)
    apply_base(fig3)
    fig3.update_layout(yaxis_title="R$", xaxis_title="", height=320)
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.markdown('<div class="section-title">Participação por Cliente</div><div class="section-sub">Faturamento total acumulado</div>', unsafe_allow_html=True)
    if "Cliente" in dff.columns:
        pie_data = dff.groupby("Cliente")["Faturamento"].sum().reset_index()
        fig4 = px.pie(pie_data, names="Cliente", values="Faturamento",
                      color_discrete_sequence=[COLORS["teal"],COLORS["blue"],COLORS["orange"],COLORS["yellow"],COLORS["purple"],COLORS["red"]])
        fig4.update_traces(textinfo="percent+label", hole=0.45,
                           marker=dict(line=dict(color=COLORS["bg"], width=2)))
        apply_base(fig4)
        fig4.update_layout(height=320, showlegend=True)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Coluna 'Cliente' não encontrada.")

# ── ROW 3: Crédito acumulado + Eficiência ────────────────────────────────────
col5, col6 = st.columns(2)

with col5:
    st.markdown('<div class="section-title">Crédito Acumulado</div><div class="section-sub">Evolução do saldo de créditos por cliente</div>', unsafe_allow_html=True)
    if "CreditoAcumulado" in dff.columns:
        grp5 = dff.dropna(subset=["CreditoAcumulado"]).groupby(["Data","Cliente"])["CreditoAcumulado"].max().reset_index() if "Cliente" in dff.columns else dff.dropna(subset=["CreditoAcumulado"]).groupby("Data")["CreditoAcumulado"].max().reset_index()
        color_col5 = "Cliente" if "Cliente" in grp5.columns else None
        fig5 = px.line(grp5, x="Data", y="CreditoAcumulado", color=color_col5,
                       color_discrete_sequence=[COLORS["yellow"],COLORS["orange"],COLORS["purple"],COLORS["teal"]],
                       markers=True)
        fig5.update_traces(line_width=2.5, marker_size=7)
        apply_base(fig5)
        fig5.update_layout(yaxis_title="R$", xaxis_title="", height=300)
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Coluna CreditoAcumulado não encontrada.")

with col6:
    st.markdown('<div class="section-title">Índice de Eficiência Energética</div><div class="section-sub">Energia compensada / consumida (%) por mês</div>', unsafe_allow_html=True)
    if "EnergiaConsumida" in dff.columns and "EnergiaCompensada" in dff.columns:
        grp6 = dff.groupby("Data")[["EnergiaConsumida","EnergiaCompensada"]].sum().reset_index()
        grp6["Eficiencia"] = (grp6["EnergiaCompensada"] / grp6["EnergiaConsumida"] * 100).clip(0, 100)
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            x=grp6["Data"], y=grp6["Eficiencia"], name="Eficiência %",
            marker=dict(
                color=grp6["Eficiencia"],
                colorscale=[[0, COLORS["blue"]], [0.5, COLORS["teal"]], [1, COLORS["yellow"]]],
                showscale=False
            )
        ))
        fig6.add_hline(y=80, line_dash="dot", line_color=COLORS["orange"], annotation_text="Meta 80%",
                       annotation_font_color=COLORS["orange"])
        apply_base(fig6)
        fig6.update_layout(yaxis_title="%", yaxis_range=[0,110], xaxis_title="", height=300)
        st.plotly_chart(fig6, use_container_width=True)

# ── ROW 4: Heatmap sazonalidade + Scatter economia x faturamento ──────────────
col7, col8 = st.columns(2)

with col7:
    st.markdown('<div class="section-title">Sazonalidade do Faturamento</div><div class="section-sub">Heatmap mês × cliente</div>', unsafe_allow_html=True)
    if "Cliente" in dff.columns and "Data" in dff.columns:
        _hdf = dff.copy()
        _hdf["MesNum"] = _hdf["Data"].dt.strftime("%Y-%m")
        heat = _hdf.groupby(["Cliente","MesNum"])["Faturamento"].sum().unstack(fill_value=0)
        heat.columns.name = None
        heat.index.name = None
        fig7 = px.imshow(heat,
                         color_continuous_scale=[[0,"#0d1117"],[0.3,COLORS["blue"]],[0.7,COLORS["teal"]],[1,COLORS["yellow"]]],
                         aspect="auto", text_auto=False)
        apply_base(fig7)
        fig7.update_layout(height=280, xaxis_title="", yaxis_title="", coloraxis_showscale=False)
        fig7.update_xaxes(tickangle=-45, tickfont_size=9)
        st.plotly_chart(fig7, use_container_width=True)

with col8:
    st.markdown('<div class="section-title">Economia vs. Faturamento</div><div class="section-sub">Correlação entre economia gerada e faturamento</div>', unsafe_allow_html=True)
    if "Economia" in dff.columns and "Faturamento" in dff.columns:
        fig8 = px.scatter(dff, x="Faturamento", y="Economia",
                          color="Cliente" if "Cliente" in dff.columns else None,
                          size="EnergiaConsumida" if "EnergiaConsumida" in dff.columns else None,
                          color_discrete_sequence=[COLORS["teal"],COLORS["blue"],COLORS["orange"],COLORS["yellow"],COLORS["purple"]],
                          hover_data=["Mes"] if "Mes" in dff.columns else None,
                          trendline="ols")
        apply_base(fig8)
        fig8.update_layout(xaxis_title="Faturamento (R$)", yaxis_title="Economia (R$)", height=280)
        st.plotly_chart(fig8, use_container_width=True)

# ── TABLE ──────────────────────────────────────────────────────────────────────
with st.expander("📋 Ver dados completos"):
    show_cols = [c for c in ["Mes","Cliente","Faturamento","EnergiaConsumida","EnergiaCompensada","EnergiaInjetada","Economia","CreditoMes","CreditoAcumulado"] if c in dff.columns]
    st.dataframe(
        dff[show_cols].style.format({
            "Faturamento":       lambda x: fmt_brl(x) if pd.notna(x) else "—",
            "Economia":          lambda x: fmt_brl(x) if pd.notna(x) else "—",
            "CreditoMes":        lambda x: fmt_brl(x) if pd.notna(x) else "—",
            "CreditoAcumulado":  lambda x: fmt_brl(x) if pd.notna(x) else "—",
            "EnergiaConsumida":  lambda x: fmt_kwh(x) if pd.notna(x) else "—",
            "EnergiaCompensada": lambda x: fmt_kwh(x) if pd.notna(x) else "—",
            "EnergiaInjetada":   lambda x: fmt_kwh(x) if pd.notna(x) else "—",
        }),
        use_container_width=True, height=400
    )

# ── FOOTER ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:40px;text-align:center;color:#3d5068;font-size:11px;border-top:1px solid #1e2d42;padding-top:16px;">
  VOLTXS GD Dashboard · Geração Distribuída · Dados importados via planilha
</div>
""", unsafe_allow_html=True)
