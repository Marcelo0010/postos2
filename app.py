import os
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import plotly.express as px
from streamlit.components.v1 import html
from shapely.geometry import Point
import geopandas as gpd

# --- Configuração geral do Streamlit (deve ser a primeira chamada) ---
st.set_page_config(
    page_title="Painel de Tancagem e Localização de Postos e Usinas na Paraíba",
    layout="wide"
)

# --- Custom CSS para fundo verde ---
st.markdown(
    """
    <style>
      .reportview-container, .main, header, footer {
        background-color: #e0f2e9;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Função de conversão DMS para Decimal ---
def dms_to_decimal(dms):
    try:
        if pd.isna(dms) or not isinstance(dms, str):
            return None
        txt = dms.strip().replace(",", ".").replace("\xa0", "").replace("\r", "").replace("\n", "")
        deg, minu, sec = [float(p) for p in txt.split(":")]
        return - (abs(deg) + minu/60 + sec/3600) if "-" in txt else abs(deg) + minu/60 + sec/3600
    except:
        return None

# --- Carrega e prepara os dados de postos ---
df = pd.read_excel("base1.xlsx", sheet_name="Folha1")
df["LATITUDE"]  = df["LATITUDE"].apply(dms_to_decimal)
df["LONGITUDE"] = df["LONGITUDE"].apply(dms_to_decimal)
df.rename(columns={"MUNICÍPIO": "Municipio"}, inplace=True)
df_map = df.dropna(subset=["LATITUDE", "LONGITUDE"])

# --- Define usinas ---
usinas = pd.DataFrame({
    "Nome": [
        "USINA GIASA", "Miriri Alimentos e Bioenergia S/A", "Japungu Agroindustrial LTDA",
        "Agro Industrial Tabu", "D'PADUA Destilação Produção Agroindústria e Comércio SA",
        "Usina Monte Alegre", "Usina Japungu Filial - Agroval"
    ],
    "Latitude": [-7.352506, -6.945139, -6.991104, -7.509135, -6.611784, -6.858823, -7.09078095333581],
    "Longitude": [-35.025719, -35.132694, -35.023097, -34.876716, -35.057232, -35.129743, -34.98264570629842]
})

# --- Métricas gerais ---
pos_tot = df.drop_duplicates("CNPJ").shape[0]
tanc_tot = int(df["Tancagem (m³)"].sum())
usa_tot = usinas.shape[0]

# --- Agregações para gráficos e tabelas ---
tanc_prod = df.groupby("Produto")["Tancagem (m³)"].sum().reset_index()
tanc_mun_prod = df.groupby(["Municipio", "Produto"])["Tancagem (m³)"].sum().reset_index()
tanc_med_post = (
    df.groupby("Municipio")["Tancagem (m³)"].sum() /
    df.groupby("Municipio")["CNPJ"].nunique()
).reset_index()
tanc_med_post.columns = ["Município", "Média Tancagem/Posto"]

# --- Funções para criação de mapas Folium ---
def criar_mapa_cluster(center=None, zoom=7):
    center = center or [df_map.LATITUDE.mean(), df_map.LONGITUDE.mean()]
    m = folium.Map(location=center, zoom_start=zoom)
    mc = MarkerCluster().add_to(m)
    for _, r in df_map.iterrows():
        folium.CircleMarker(
            [r.LATITUDE, r.LONGITUDE], radius=max(5, r["Tancagem (m³)"] / 500),
            color="blue", fill=True, fill_color="blue", fill_opacity=0.6,
            popup=f"<b>{r['Razão Social']}</b><br>Produto: {r['Produto']}<br>Tancagem: {r['Tancagem (m³)']} m³"
        ).add_to(mc)
    for _, u in usinas.iterrows():
        folium.Marker(
            [u.Latitude, u.Longitude],
            icon=folium.Icon(color="red", icon="industry", prefix="fa"),
            popup=f"<b>Usina:</b> {u.Nome}"
        ).add_to(m)
    return m


def criar_mapa_destaque(mun=None):
    center = [df_map.LATITUDE.mean(), df_map.LONGITUDE.mean()]
    zoom = 7
    m = folium.Map(location=center, zoom_start=zoom)
    for _, r in df_map.iterrows():
        clr = "green" if r.Municipio == mun else "gray"
        folium.CircleMarker(
            [r.LATITUDE, r.LONGITUDE], radius=max(5, r["Tancagem (m³)"] / 500),
            color=clr, fill=True, fill_color=clr, fill_opacity=0.8,
            popup=f"<b>{r['Razão Social']}</b><br>Produto: {r['Produto']}<br>Tancagem: {r['Tancagem (m³)']} m³"
        ).add_to(m)
        if r.Municipio == mun:
            center, zoom = [r.LATITUDE, r.LONGITUDE], 12
    for _, u in usinas.iterrows():
        folium.Marker(
            [u.Latitude, u.Longitude],
            icon=folium.Icon(color="red", icon="industry", prefix="fa"),
            popup=f"<b>Usina:</b> {u.Nome}"
        ).add_to(m)
    m.location, m.zoom_start = center, zoom
    return m

# --- Cabeçalho ---
with st.container():
    st.markdown(
        """
        <div style="background-color:#004d40;padding:20px;border-radius:8px">
          <h1 style="text-align:center;color:#ffffff;font-size:36px;margin:0">
            Painel de Tancagem e Localização de Postos e Usinas na Paraíba
          </h1>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown(
        """
        <p style="text-align:center;font-size:18px;margin-top:10px;">
        O Sindalcool disponibiliza o mapeamento interativo que mostra a distribuição dos tanques
        de combustível e postos do estado da Paraíba, incluindo estatísticas por produto e por município,
        bem como a localização exata dos estabelecimentos.
        </p>
        """, unsafe_allow_html=True
    )

# --- KPIs Principais ---
c1, c2, c3 = st.columns(3)
c1.metric("Postos Únicos", pos_tot)
c2.metric("Tancagem Total (m³)", f"{tanc_tot:,}".replace(",", "."))
c3.metric("Usinas Mapeadas", usa_tot)

# --- Seleção de Município ---
mun = st.selectbox(
    "🔎 Selecione o Município para Detalhes",
    [""] + sorted(df.Municipio.dropna().unique().tolist())
)

# --- Exibição de Mapas ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("📍 Mapa Cluster de Tanques")
    html(criar_mapa_cluster()._repr_html_(), height=500)
with col2:
    st.subheader("🎯 Mapa com Destaque")
    html(criar_mapa_destaque(mun if mun else None)._repr_html_(), height=500)

# --- Detalhamento por Município ---
if mun:
    st.markdown(f"### Detalhes para: **{mun}**")
    dmun = df[df.Municipio == mun]
    postos_mun = dmun.CNPJ.nunique()
    tanc_mun = int(dmun["Tancagem (m³)"].sum())
    st.write(f"- Total de Postos: **{postos_mun}**")
    st.write(f"- Tancagem Total: **{tanc_mun:,} m³**".replace(",", "."))
    fig = px.bar(
        dmun.groupby("Produto")["Tancagem (m³)"].sum().reset_index(),
        x="Produto", y="Tancagem (m³)", labels={"Tancagem (m³)":"m³"}, title="Tancagem por Produto"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Ranking de Média de Tancagem por Posto ---
st.subheader("🔢 Ranking: Média de Tancagem por Posto (por Município)")
st.dataframe(
    tanc_med_post.sort_values("Média Tancagem/Posto", ascending=False).reset_index(drop=True),
    use_container_width=True
)

# --- Gráficos Gerais ---
st.subheader("📊 Gráficos Gerais")
fig1 = px.bar(tanc_prod, x="Produto", y="Tancagem (m³)", labels={"Tancagem (m³)":"m³"}, title="Tancagem por Produto")
fig2 = px.bar(tanc_mun_prod, x="Municipio", y="Tancagem (m³)", color="Produto", labels={"Tancagem (m³)":"m³"}, title="Tancagem por Município e Produto")
st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)



