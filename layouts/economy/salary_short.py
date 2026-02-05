import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Input, Output, html, dcc
from translation import translations   # ← import siit
from utils.helpers import apply_common_legend, get_meta_options

def salary_short_layout(lang="et"):
 
    #opts = get_meta_options("PA117", lang)
    df = get_pa117_data(indicator="GR_W_AVG", county="EE", period=None, lang=lang)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df["vaatlusperiood"],
            y=df["väärtus"],
            name=df["näitaja_nimi"].iloc[0],
            text=df["väärtus"],
            textposition="inside",
            textfont=dict(color="white", size=12)
        ),
        secondary_y=False
    )
    
    return html.Div([
        html.H3(translations[lang]["salary_short_header"]),
        dcc.Graph(id="salary-graph-short", figure=fig),
        html.P(translations[lang]["salaryNotice"])         

])

def get_pa117_data(indicator=None, county="EE", period=None, lang="et"):
    meta_url = f"https://andmed.stat.ee/api/v1/{lang}/stat/PA117"
    meta = requests.get(meta_url).json()

    variables = [v["code"] for v in meta.get("variables", [])]
    query = []

    if indicator:
        if isinstance(indicator, str):
            indicator = [indicator]
        code = variables[0] if len(variables) > 0 else "Näitaja"
        query.append({
            "code": code,
            "selection": {"filter": "item", "values": indicator}
        })

    if county:
        if isinstance(county, str):
            county = [county]
        code = variables[1] if len(variables) > 1 else "Maakond"
        query.append({
            "code": code,
            "selection": {"filter": "item", "values": county}
        })

    #print("Variables:", variables[1])
    #print("Ja maakond code:", code)  
    #print("Period:", period)

    if period:
        if isinstance(period, (int, str)):
            period = [str(period)]
        else:
            period = [str(p) for p in period]
        code = variables[2] if len(variables) > 2 else "Vaatlusperiood"
        query.append({
        "code": code,
        "selection": {"filter": "item", "values": period}
    })
        
    #print("Ja periood code:", code)
    #print("Query:", query)

    payload = {"query": query, "response": {"format": "json"}}
    url = meta_url

    #print("Payload:", payload)
    res = requests.post(url, json=payload)
    res.raise_for_status()
    rows = res.json()["data"]
        
    # Metaandmete põhjal dimensioonide järjekord
    opts = get_meta_options("PA117", lang)
    records = []

    for row in rows:
        # Build mapping from variable code to value (zip will stop at shortest)
        mapping = dict(zip(variables, row.get("key", [])))

        # Safely extract by variable code with fallbacks to indexed access if present
        naitaja = mapping.get("Näitaja") or mapping.get("näitaja")
        if naitaja is None:
            naitaja = row.get("key", [None])[0] if len(row.get("key", [])) > 0 else None

        maakond = mapping.get("Maakond") or mapping.get("maakond")
        if maakond is None:
            maakond = row.get("key", [None, None])[1] if len(row.get("key", [])) > 1 else None

        periood = mapping.get("Vaatlusperiood") or mapping.get("vaatlusperiood")
        if periood is None:
            periood = row.get("key", [None, None, None])[2] if len(row.get("key", [])) > 2 else None

        raw_val = row.get("values", [None])[0]
        try:
            val = float(raw_val) if raw_val not in (None, "", ".", "..", ":") else None
        except (TypeError, ValueError):
            val = None

        records.append({
            "näitaja": naitaja,
            "maakond": maakond,
            "vaatlusperiood": periood,
            "väärtus": val
        })    

    df = pd.DataFrame(records)
    #print("Salary shortterm options:", variables)

    # Lisa inimloetavad nimetused (kasuta metaandmetest saadud keele-spetsiifilisi koode)
    if len(variables) > 0:
        ind_code = variables[0]
    else:
        ind_code = "Näitaja"

    indicator_map = {opt["value"]: opt["label"] for opt in opts.get(ind_code, [])}
    df["näitaja_nimi"] = df["näitaja"].map(indicator_map)
    df["väärtus"] = pd.to_numeric(df["väärtus"], errors="coerce")

    return df