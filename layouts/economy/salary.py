
import plotly.express as px
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.helpers import apply_common_legend
from utils.stat_api import get_pa103_data
from translation import translations   # ← import siit
from dash import Input, Output, html, dcc

# Abifunktsioon metaandmete jaoks

def get_meta_options(table="PA103", lang="et"):
    url = f"https://andmed.stat.ee/api/v1/{lang}/stat/{table}"
    meta = requests.get(url).json()

    opts = {}
    for v in meta["variables"]:
        code = v["code"]
        values = v["values"]
        labels = v["valueTexts"]
        opts[code] = [{"label": lbl, "value": val} for val, lbl in zip(values, labels)]
    return opts

def get_pa103_data(indicator=None, emtak="TOTAL", years=None, lang="et"):
    query = []

    # Näitaja filter
    if indicator:
        if isinstance(indicator, str):
            indicator = [indicator]
        query.append({
            "code": "Näitaja",
            "selection": {"filter": "item", "values": indicator}
        })

    # Tegevusala filter (kohustuslik)
    if emtak:
        if isinstance(emtak, str):
            emtak = [emtak]
        query.append({
            "code": "Tegevusala",
            "selection": {"filter": "item", "values": emtak}
        })

    # Aastad
    if years:
        if isinstance(years, (int, str)):
            years = [str(years)]
        else:
            years = [str(y) for y in years]
        query.append({
            "code": "Vaatlusperiood",
            "selection": {"filter": "item", "values": years}
        })

    payload = {"query": query, "response": {"format": "json"}}
    url = f"https://andmed.stat.ee/api/v1/{lang}/stat/PA103"
    res = requests.post(url, json=payload)
    res.raise_for_status()
    rows = res.json()["data"]

    # DataFrame
    df = pd.DataFrame([
        {
            "näitaja": row["key"][0],
            "tegevusala": row["key"][1],
            "aasta": row["key"][2],
            "väärtus": float(val) if val not in (None, "", ".", "..", ":") else None
        }
        for row in rows
        for val in [row["values"][0]]
    ])

    # Lisa inimloetavad nimetused
    opts = get_meta_options("PA103", lang)
    indicator_map = {opt["value"]: opt["label"] for opt in opts["Näitaja"]}
    df["näitaja_nimi"] = df["näitaja"].map(indicator_map)

    return df


# Layout

def salary_layout(lang="et"):

     # Esialgne demo-graafik (TOTAL, GR_W_AVG, kõik aastad)
    df = get_pa103_data(indicator="GR_W_AVG", emtak="TOTAL")

    fig = px.bar(
        df,
        x="aasta",
        y="väärtus",
        title=translations[lang]["salary.title"],
        labels={
            "väärtus": translations[lang]["salary.label"],
             "aasta": translations[lang]["year.label"]
            }
    )

    return html.Div([
        html.H3(translations[lang]["salary_header"]),
        html.Div([
            html.Label(translations[lang]["indicator.label"]),
            dcc.Dropdown(id="salary-indicator-dropdown")
        ], style={"width": "30%", "marginBottom": "10px"}),
        html.Div([
            html.Label(translations[lang]["sector.label"]),
            dcc.Dropdown(id="salary-emtak-dropdown", multi=True)
        ], style={"width": "30%", "marginBottom": "10px"}),

        html.Div([
            html.Label(translations[lang]["year.label"]),
            dcc.Dropdown(id="salary-year-dropdown")
        ], style={"width": "30%", "marginBottom": "10px"}),

        dcc.Graph(id="salary-graph", figure=fig)
    ])

# Callbackid

def register_salary_callbacks(app):
    @app.callback(
        [Output("salary-indicator-dropdown", "options"),
         Output("salary-indicator-dropdown", "value"),    #["GR_W_AVG", "GR_W_D5", "GR_W_AVG_SM"]
         Output("salary-emtak-dropdown", "options"),
         Output("salary-emtak-dropdown", "value"),
         Output("salary-year-dropdown", "options"),
         Output("salary-year-dropdown", "value")],
        [Input("salary-graph", "id"),
         Input("language-dropdown", "value")],   # ← lisatud
         prevent_initial_call=False
        )
    
    def update_salary_filters(pathname, lang):
        opts = get_meta_options("PA103", lang)
        #print("metandmed", opts)
        indicator_map = {opt["value"]: opt["label"] for opt in opts["Näitaja"]}
        #[{"label": translations[lang]["Allindicator.label"], "value": "ALL"}] + 
        indicator_opts = [{"label": translations[lang]["Allindicator.label"], "value": "ALL"}] + opts["Näitaja"]
        emtak_opts = opts["Tegevusala"]
        #[{"label": translations[lang]["Allindicator.label"], "value": "ALL"}] + 
        year_opts = [{"label": translations[lang]["Allindicator.label"], "value": "ALL"}] + opts["Vaatlusperiood"]

        return (
            indicator_opts, indicator_opts[1]["value"],  # vaikimisi esimene päris näitaja
            emtak_opts, "TOTAL",                        # vaikimisi TOTAL
            year_opts, year_opts[0]["value"]           # vaikimisi viimane aasta   

    )

    # Graafiku uuendamine

    @app.callback(
        Output("salary-graph", "figure"),
        [Input("salary-indicator-dropdown", "value"),
         Input("salary-emtak-dropdown", "value"),
         Input("salary-year-dropdown", "value"),
         Input("language-dropdown", "value")]   # ← lisatud

    )

    def update_salary_graph(indicator, emtak, year, lang):
        # Kui kasutaja valib "ALL", siis lisa kõik väärtused
        
        indicators = None if indicator == "ALL" else indicator
        years = None if year == "ALL" else year

        df = get_pa103_data(indicator=indicators, emtak=emtak, years=years, lang=lang)

        #print("indikaatorid" , indicators)

        # Kui mõlemad näitajad korraga
        #if isinstance(indicators, list) and "GR_W_AVG" in indicators and "GR_W_D5" in indicators:
        if indicator is None or indicator == "ALL":

            fig = make_subplots(specs=[[{"secondary_y": True}]])

            avg_df = df[df["näitaja"] == "GR_W_AVG"]
            med_df = df[df["näitaja"] == "GR_W_D5"]
            dif_df = df[df["näitaja"] == "GR_W_AVG_SM"]
            
            print(avg_df, med_df, dif_df)

            # Keskmine ja mediaan vasakule teljele
            fig.add_trace(
                go.Bar(x=avg_df["aasta"], y=avg_df["väärtus"], name=avg_df["näitaja_nimi"].iloc[0]),
                secondary_y=False
            )

            fig.add_trace(
                go.Bar(x=med_df["aasta"], y=med_df["väärtus"], name=med_df["näitaja_nimi"].iloc[0]),
                secondary_y=False
            )

            # Muutus paremale teljele joonena
            fig.add_trace(
                go.Scatter(x=dif_df["aasta"], y=dif_df["väärtus"],
                        name=dif_df["näitaja_nimi"].iloc[0], mode="lines+markers"),                        
                secondary_y=True
            )

        # Telgede sildid
            fig.update_yaxes(title_text=translations[lang]["salary.label"], secondary_y=False)
            #title_text="Palga muutus (%)",
            fig.update_yaxes(title_text="Palga muutus (%)",secondary_y=True)
            
            fig.update_layout(title=translations[lang]["salary.title"])
           
            #legendi paigutus alla keskele
            fig = apply_common_legend(fig, "h", -0.3, 0.5) 

        # Kui ainult üks näitaja
        else:
            fig = px.bar(
                  df,
                  x="aasta",
                  y="väärtus",
                  color="näitaja_nimi",
                  barmode="group",
                  labels={
                    "väärtus": translations[lang]["salary.label"],
                    "aasta": translations[lang]["year.label"],
                    "näitaja_nimi": translations[lang]["indicator.label"]
                }
            )
        # Legend alla keskele
        fig = apply_common_legend(fig, "h", -0.3, 0.5)  
        return fig





