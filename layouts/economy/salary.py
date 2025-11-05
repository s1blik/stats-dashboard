
import plotly.express as px
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.helpers import apply_common_legend, get_meta_options
from translation import translations   # ← import siit
from dash import Input, Output, html, dcc


def get_pa103_data(indicator=None, emtak="TOTAL", years=None, lang="et"):
    # Fetch table metadata first so we can use the language-specific variable codes
    meta_url = f"https://andmed.stat.ee/api/v1/{lang}/stat/PA103"
    meta = requests.get(meta_url).json()
    variables = [v["code"] for v in meta.get("variables", [])]

    # Build query using the variable codes from metadata (language-specific)
    query = []

    # Näitaja filter (first variable expected to be the indicator)
    if indicator:
        if isinstance(indicator, str):
            indicator = [indicator]
        code = variables[0] if len(variables) > 0 else "Näitaja"
        query.append({
            "code": code,
            "selection": {"filter": "item", "values": indicator}
        })

    # Tegevusala filter (second variable)
    if emtak:
        if isinstance(emtak, str):
            emtak = [emtak]
        code = variables[1] if len(variables) > 1 else "Tegevusala"
        query.append({
            "code": code,
            "selection": {"filter": "item", "values": emtak}
        })

    # Aastad (third variable)
    if years:
        if isinstance(years, (int, str)):
            years = [str(years)]
        else:
            years = [str(y) for y in years]
        code = variables[2] if len(variables) > 2 else "Vaatlusperiood"
        query.append({
            "code": code,
            "selection": {"filter": "item", "values": years}
        })

    payload = {"query": query, "response": {"format": "json"}}
    url = meta_url
    res = requests.post(url, json=payload)
    res.raise_for_status()
    rows = res.json()["data"]

    # Metaandmete põhjal dimensioonide järjekord
    opts = get_meta_options("PA103", lang)

    # DataFrame - build rows safely using variable codes coming from metadata
    records = []
    for row in rows:
        # Build mapping from variable code to value (zip will stop at shortest)
        mapping = dict(zip(variables, row.get("key", [])))

        # Safely extract by variable code with fallbacks to indexed access if present
        naitaja = mapping.get("Näitaja") or mapping.get("näitaja")
        if naitaja is None:
            naitaja = row.get("key", [None])[0] if len(row.get("key", [])) > 0 else None

        tegevusala = mapping.get("Tegevusala") or mapping.get("tegevusala")
        if tegevusala is None:
            tegevusala = row.get("key", [None, None])[1] if len(row.get("key", [])) > 1 else None

        aasta = mapping.get("Vaatlusperiood") or mapping.get("aasta")
        if aasta is None:
            aasta = row.get("key", [None, None, None])[2] if len(row.get("key", [])) > 2 else None

        raw_val = row.get("values", [None])[0]
        try:
            val = float(raw_val) if raw_val not in (None, "", ".", "..", ":") else None
        except (TypeError, ValueError):
            val = None

        records.append({
            "näitaja": naitaja,
            "tegevusala": tegevusala,
            "aasta": aasta,
            "väärtus": val
        })

    df = pd.DataFrame(records)

    # Lisa inimloetavad nimetused (kasuta metaandmetest saadud keele-spetsiifilisi koode)
    if len(variables) > 0:
        ind_code = variables[0]
    else:
        ind_code = "Näitaja"
    indicator_map = {opt["value"]: opt["label"] for opt in opts.get(ind_code, [])}
    df["näitaja_nimi"] = df["näitaja"].map(indicator_map)
    df["väärtus"] = pd.to_numeric(df["väärtus"], errors="coerce")

    return df


# Layout

def salary_layout(lang="et"):

    # Esialgne demo-graafik (TOTAL, GR_W_AVG, kõik aastad)
    df = get_pa103_data(indicator="GR_W_AVG", emtak="TOTAL", lang=lang)

    # Loo subplot kahe y-telje võimalusega
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Lisa keskmise palga tulbad vasakule teljele
    fig.add_trace(
        go.Bar(
            x=df["aasta"],
            y=df["väärtus"],
            name=df["näitaja_nimi"].iloc[0],
            text=df["väärtus"],
            textposition="inside",
            textfont=dict(color="white", size=12)
        ),
        secondary_y=False
    )

    # Telgede sätted
    fig.update_yaxes(title_text=translations[lang]["salary.label"], range=[0, None], secondary_y=False)
    fig.update_yaxes(title_text=translations[lang]["salarychange"], range=[0, None], secondary_y=True)

    # Üldine layout
    fig.update_layout(
        title=translations[lang]["salary.title"],
        height=600
    )

    # Legend alla keskele
    fig = apply_common_legend(fig, "h", -0.3, 0.5)

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
        # Determine language-specific variable codes from opts keys (order preserved)
        var_codes = list(opts.keys())
        ind_code = var_codes[0] if len(var_codes) > 0 else "Näitaja"
        emtak_code = var_codes[1] if len(var_codes) > 1 else "Tegevusala"
        year_code = var_codes[2] if len(var_codes) > 2 else "Vaatlusperiood"

        indicator_map = {opt["value"]: opt["label"] for opt in opts.get(ind_code, [])}
        indicator_opts = [{"label": translations[lang]["Allindicator.label"], "value": "ALL"}] + opts.get(ind_code, [])

        # Add an "All" option that maps to the API's TOTAL code for all sectors
        emtak_opts = [{"label": translations[lang]["Allemtak.label"], "value": "TOTAL"}] + sorted(opts.get(emtak_code, []), key=lambda x: x.get("label", ""))

        year_opts = [{"label": translations[lang]["Allperiod.label"], "value": "ALL"}] + opts.get(year_code, [])

        # Default indicator value: first real option if available
        default_indicator = indicator_opts[1]["value"] if len(indicator_opts) > 1 else indicator_opts[0]["value"]

        # Default year value: first actual year option if available
        default_year = year_opts[1]["value"] if len(year_opts) > 1 else year_opts[0]["value"]

        return (
            indicator_opts, default_indicator,
            emtak_opts, "TOTAL",
            year_opts, default_year
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
            
            #print(avg_df, med_df, dif_df)

            # Keskmine ja mediaan vasakule teljele
            fig.add_trace(
                go.Bar(
                    x=avg_df["aasta"],
                    y=avg_df["väärtus"],
                    name=avg_df["näitaja_nimi"].iloc[0],
                    text=avg_df["väärtus"],
                    textposition="inside",
                    textfont=dict(color="white", size=12)  # ← teksti värv ja suurus
                    ),
                secondary_y=False
            )

            fig.add_trace(
                go.Bar(x=med_df["aasta"],
                       y=med_df["väärtus"],
                       name=med_df["näitaja_nimi"].iloc[0],
                       text=med_df["väärtus"],
                       textposition="inside",
                       textfont=dict(color="white", size=12)  # ← teksti värv ja suurus
                       ),
                secondary_y=False
            )

            # Muutus paremale teljele joonena
            dif_df["väärtus"] = pd.to_numeric(dif_df["väärtus"], errors="coerce")

            fig.add_trace(
                go.Scatter(
                    x=dif_df["aasta"],
                    y=dif_df["väärtus"],
                    name=dif_df["näitaja_nimi"].iloc[0],
                    mode="lines+markers+text",
                    text=dif_df["väärtus"].round(1),
                    textposition="bottom center"
                    ),                        
                secondary_y=True
            )

        # Telgede sildid
            fig.update_yaxes(title_text=translations[lang]["salary.label"], secondary_y=False)
            #title_text="Palga muutus (%)",
            fig.update_yaxes(range=[0, None], title_text=translations[lang]["salarychange"], secondary_y=True)
            
            fig.update_layout(title=translations[lang]["salary.title"], height=600)
           
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
                  text="väärtus",   # ← veeru nimi stringina
                  labels={
                    "väärtus": translations[lang]["salary.label"],
                    "aasta": translations[lang]["year.label"],
                    "näitaja_nimi": translations[lang]["indicator.label"]
                }
            )

            fig.update_yaxes(
                range=[0, None]
            )

        # Legend alla keskele
        fig = apply_common_legend(fig, "h", -0.3, 0.5)  
        return fig





