import pandas as pd
import folium
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import dash_bootstrap_components as dbc
from folium.plugins import MarkerCluster
import os

os.makedirs("assets", exist_ok=True)

def dms_to_decimal(dms):
    try:
        if pd.isna(dms) or not isinstance(dms, str):
            return None
        dms = dms.strip().replace(",", ".").replace("\xa0", "").replace("\r", "").replace("\n", "")
        parts = dms.split(":")
        if len(parts) == 3:
            raw_deg = parts[0].strip()
            deg = abs(float(raw_deg))
            min = float(parts[1].strip()) / 60
            sec = float(parts[2].strip()) / 3600
            dec = deg + min + sec
            return -dec if "-" in raw_deg else dec
        return None
    except Exception as e:
        print(f"Erro ao converter '{dms}': {e}")
        return None


# Dados
df = pd.read_excel("base1.xlsx", sheet_name="Folha1")
df["LATITUDE"] = df["LATITUDE"].apply(dms_to_decimal)
df["LONGITUDE"] = df["LONGITUDE"].apply(dms_to_decimal)
df.rename(columns={"MUNICÍPIO": "Municipio"}, inplace=True)

postos_unicos = df.drop_duplicates(subset=["CNPJ"])
total_postos_unicos = len(postos_unicos)
tancagem_total_geral = df["Tancagem (m³)"].sum()
tancagem_por_produto = df.groupby("Produto")["Tancagem (m³)"].sum().reset_index()
tancagem_por_mun_prod = df.groupby(["Municipio", "Produto"])["Tancagem (m³)"].sum().reset_index()

df_map = df.dropna(subset=["LATITUDE", "LONGITUDE"])

graf_tancagem_produto = px.bar(tancagem_por_produto, x="Produto", y="Tancagem (m³)", title="Tancagem por Produto", height=400)
graf_tancagem_mun = px.bar(tancagem_por_mun_prod, x="Municipio", y="Tancagem (m³)", color="Produto",
                             title="Tancagem por Produto e Município", height=600)

# --- Função para salvar mapa simples (sem cluster) com destaque no município ---
def criar_mapa_destaque(municipio):
    m = folium.Map(location=[df_map["LATITUDE"].mean(), df_map["LONGITUDE"].mean()], zoom_start=7)
    destaque_coords = None

    for _, row in df_map.iterrows():
        cor = "green" if row["Municipio"] == municipio else "gray"
        popup = f"<b>{row['Razão Social']}</b><br>Produto: {row.get('Produto', 'N/A')}<br>Tanque: {row.get('Nome Tanque', 'Desconhecido')}<br>Tancagem: {row.get('Tancagem (m³)', 0)} m³"
        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=max(5, row["Tancagem (m³)"] / 500),
            popup=folium.Popup(popup, max_width=300),
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.8,
        ).add_to(m)
        if row["Municipio"] == municipio:
            destaque_coords = [row["LATITUDE"], row["LONGITUDE"]]

    if destaque_coords:
        m.location = destaque_coords
        m.zoom_start = 12

    caminho = "assets/mapa_destaque.html"
    m.save(caminho)
    return caminho

# --- Função para salvar mapa com cluster (fixo) ---
def criar_mapa_cluster():
    m = folium.Map(location=[df_map["LATITUDE"].mean(), df_map["LONGITUDE"].mean()], zoom_start=7)
    cluster = MarkerCluster().add_to(m)

    for _, row in df_map.iterrows():
        popup = f"<b>{row['Razão Social']}</b><br>Produto: {row.get('Produto', 'N/A')}<br>Tanque: {row.get('Nome Tanque', 'Desconhecido')}<br>Tancagem: {row.get('Tancagem (m³)', 0)} m³"
        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=max(5, row["Tancagem (m³)"] / 500),
            popup=folium.Popup(popup, max_width=300),
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.6,
        ).add_to(cluster)

    caminho = "assets/mapa_cluster.html"
    m.save(caminho)
    return caminho

# Salvar mapa cluster uma vez, fora do callback
mapa_cluster_path = criar_mapa_cluster()

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Painel de Tancagem - Paraíba"

app.layout = html.Div(style={"backgroundColor": "#e0f2e9", "padding": "20px"}, children=[
    html.H1("Painel de Tancagem e Localização de Postos na Paraíba", 
            style={"textAlign": "center", "color": "#004d40", "fontWeight": "bold", "fontSize": "36px"}),

    html.P("O Sindalcool disponibiliza o mapeamento interativo que mostra a distribuição dos tanques de combustível e postos do estado da Paraíba, incluindo estatísticas por produto e por município, bem como a localização exata dos estabelecimentos.",
           style={"textAlign": "center", "fontSize": "18px"}),

    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Total de Postos", className="card-title"),
                html.H2(f"{total_postos_unicos}", style={"color": "#f7fafa"})
            ])
        ], color="success", inverse=True), width=6),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Tancagem Total (m³)", className="card-title"),
                html.H2(f"{int(tancagem_total_geral):,}".replace(",", "."), style={"color": "#f7fafa"})
            ])
        ], color="success", inverse=True), width=6),
    ], className="mb-4"),

    html.H4("Selecione o Município para Detalhes", style={"marginTop": "20px"}),
    dcc.Dropdown(id="municipio-dropdown", options=[
    {"label": mun, "value": mun} for mun in sorted(df["Municipio"].dropna().astype(str).unique())
], placeholder="Escolha um município", style={"marginBottom": "20px"}),


    html.Div(id="info-municipio", style={"minHeight": "160px"}),

    html.H4("Mapa de Postos com Destaque", style={"marginTop": "20px"}),
    html.Iframe(id="mapa-destaque", width="100%", height="500", srcDoc="Carregando mapa..."),

    html.H4("Mapa de Cluster de Tanques", style={"marginTop": "40px"}),
    html.Iframe(id="mapa-cluster", width="100%", height="500", srcDoc=open(mapa_cluster_path, "r", encoding="utf-8").read()),

    html.H4("Gráficos Gerais", style={"marginTop": "40px"}),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=graf_tancagem_produto), width=12),
        dbc.Col(dcc.Graph(figure=graf_tancagem_mun), width=12),
    ])
])

@app.callback(
    Output("mapa-destaque", "srcDoc"),
    Output("info-municipio", "children"),
    Input("municipio-dropdown", "value")
)
def atualizar_mapa(municipio):
    if municipio is None:
        # Mapa padrão sem zoom ou destaque
        caminho = criar_mapa_destaque(None)
        return open(caminho, "r", encoding="utf-8").read(), ""

    # Mapa com destaque no município
    caminho = criar_mapa_destaque(municipio)

    total_postos = df[df["Municipio"] == municipio]["CNPJ"].nunique()
    tanc_total = df[df["Municipio"] == municipio]["Tancagem (m³)"].sum()
    tanc_produto = df[df["Municipio"] == municipio].groupby("Produto")["Tancagem (m³)"].sum().reset_index()

    fig_prod_mun = px.bar(tanc_produto, x="Produto", y="Tancagem (m³)",
                         title=f"Tancagem por Produto no Município de {municipio}",
                         height=300)

    info = dbc.Card([
        dbc.CardBody([
            html.H4(f"Município: {municipio}"),
            html.P(f"Total de Postos: {total_postos}"),
            html.P(f"Tancagem Total: {int(tanc_total):,}".replace(",", ".")),
            html.Ul([html.Li(f"{row['Produto']}: {int(row['Tancagem (m³)']):,}".replace(",", ".")) for _, row in tanc_produto.iterrows()]),
            dcc.Graph(figure=fig_prod_mun)
        ])
    ])

    return open(caminho, "r", encoding="utf-8").read(), info

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")

