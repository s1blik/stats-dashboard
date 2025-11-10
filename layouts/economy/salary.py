
import plotly.express as px
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from services.fetch_data import get_salary_data
from utils.helpers import apply_common_legend, get_meta_options
from translation import translations   # ← import siit
from dash import Input, Output, html, dcc
import traceback
import textwrap

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

    opts = get_meta_options("PA103", lang)
    #var_codes = list(opts.keys()

    #võtame kõik emtak väärtused
    emtak_values = [item["value"] for item in opts["Tegevusala"]]

    #eemaldame "TOTAL"    
    emtak_values = [v for v in emtak_values if v != "TOTAL"]
    indicator_values = ["GR_W_AVG", "GR_W_D5"]    

    latest_year = df["aasta"].max()

    df2 = get_pa103_data(
        indicator=indicator_values,
        emtak=emtak_values,
        years=latest_year,
        lang=lang)

    # Loo subplot kahe y-telje võimalusega
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])

    # Võta kõige värskem aasta
    latest_year = df2["aasta"].max()
    df2_latest = df2[df2["aasta"] == latest_year]

    # Sorteeri tegevusalad väärtuse järgi

    # Aggregate duplicates (if any), then pivot so each tegevusala has avg/med columns
    df2_agg = df2.groupby(["tegevusala", "näitaja"], as_index=False)["väärtus"].mean()

    df2_wide = df2_agg.pivot(
        index="tegevusala",
        columns="näitaja",
        values="väärtus"
    ).reset_index()

    #print(" 156 df2_wide", df2_wide)

    # Determine which indicator columns exist (avg vs med) and drop activities with no values for both
    indicator_cols = [c for c in ["GR_W_AVG", "GR_W_D5"] if c in df2_wide.columns]
    if indicator_cols:
        df2_wide = df2_wide.dropna(subset=indicator_cols, how="all")

    # Ensure numeric types for sorting and place missing values last
    for col in indicator_cols:
        df2_wide[col] = pd.to_numeric(df2_wide[col], errors="coerce")

    # Sort numerically by average (if available) and force NaNs to the end by filling them with +inf in the sort key
    if "GR_W_AVG" in df2_wide.columns:
        df2_wide_sorted = df2_wide.sort_values(
            by="GR_W_AVG",
            ascending=True,
            key=lambda col: pd.to_numeric(col, errors="coerce").fillna(float("inf"))
        )
    else:
        df2_wide_sorted = df2_wide

    # Map activity codes to human-readable labels using metadata (if available)
    activity_key = None
    try:
        # find which meta key contains the activity values
        for k, vlist in opts.items():
            values = {item.get("value") for item in vlist}
            if any(code in values for code in df2_wide_sorted["tegevusala"]):
                activity_key = k
                break
    except Exception:
        activity_key = None

    if activity_key:
        activity_map = {item["value"]: item["label"] for item in opts.get(activity_key, [])}
        # create a human-readable column and replace the kode values for plotting
        df2_wide_sorted["tegevusala"] = df2_wide_sorted["tegevusala"].map(activity_map).fillna(df2_wide_sorted["tegevusala"])
       
    # Wrap long activity names so they break into multiple lines in the chart.
    def wrap_label(s, width=50):
        try:
            # textwrap.fill will break at word boundaries and insert '\n'
            #return textwrap.fill(str(s), width=width)
            return "<br>".join(textwrap.wrap(str(s), width=width))
        except Exception:
            return s

    # Add a wrapped label column and use it for plotting and ordering
    df2_wide_sorted["tegevusala_wrapped"] = df2_wide_sorted["tegevusala"].apply(lambda s: wrap_label(s, width=50))
    order = df2_wide_sorted["tegevusala_wrapped"].tolist()
    #print("order 203",order)


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
    # Build fig2 with explicit traces so ordering is deterministic
    #avg_name = translations[lang].get("salary.avg.label", "Keskmine palk")
    avg_name = translations[lang]["salary.label"]
    med_name = translations[lang].get("salary.med.label", "Mediaan palk")
    #fig.update_yaxes(title_text=translations[lang]["salary.label"], range=[0, None], secondary_y=False)
    avg_trace = go.Bar(
        y=df2_wide_sorted["tegevusala_wrapped"],
        x=df2_wide_sorted.get("GR_W_AVG"),
        name=translations[lang]["salary.average.Label"],
        text = df2_wide_sorted.get("GR_W_AVG"),
        textfont=dict(color="white", size=12),
        orientation="h",
        offsetgroup="1",
        legendrank=1
    )
    print("235 wide sorted", df)
    med_trace = go.Bar(
        y=df2_wide_sorted["tegevusala_wrapped"],
        x=df2_wide_sorted.get("GR_W_D5"),
        name=translations[lang]["salary.median.Label"],
        text = df2_wide_sorted.get("GR_W_D5"),
        textposition="inside",
        textfont=dict(color="white", size=12),
        orientation="h",
        offsetgroup="2",
        legendrank=2
    )

    # Force visual ordering by applying small horizontal offsets: avg left of med
    # offsets are in plotly fraction units; adjust if needed for visual spacing
    try:
        # Use offsets so avg appears above/left of median depending on category ordering
        avg_trace.update(offset=0.18)
        med_trace.update(offset=-0.18)
    except Exception:
        # older plotly versions may not support offset; fallback to default order
        pass

    # Draw median first then average so average renders on top/foreground; legendrank keeps legend order
    fig2 = go.Figure(data=[med_trace, avg_trace])
    fig2.update_layout(barmode="group", legend=dict(traceorder="normal"), bargap=0.2)
    
    fig.update_layout(
        barmode="group",
        title=translations[lang].get("salary_avg_vs_median", "Keskmine vs Mediaan palk tegevusalade kaupa ({year})").format(year=latest_year),
        xaxis_title=translations[lang]["salary.label"],
        yaxis_title="Tegevusala"
    )

    # Adjust layout: reduce whitespace between plot and legend and give more
    # vertical room to the bars. We set explicit margins and a taller height,
    # and control legend placement afterwards.
    fig2.update_layout(
        barmode="group",
        title=translations[lang].get("salary_avg_vs_median", "Keskmine vs Mediaan palk tegevusalade kaupa ({year})").format(year=latest_year),
        xaxis_title=translations[lang]["salary.label"],
        # remove yaxis_title as requested and restore larger height
        height=3700,
        margin=dict(l=120, r=40, t=100, b=90),
        yaxis=dict(
            categoryorder="array",     # ära lase tähestikulisel järjekorral üle kirjutada
            categoryarray=order,
            automargin=True,
            tickfont=dict(size=12),
            ticklabelposition="outside top",
            ticklabelstandoff=10 
        )        
    )
    #print("order 278", order) 

    # Telgede sätted
    fig.update_yaxes(title_text=translations[lang]["salary.label"], range=[0, None], secondary_y=False)
    fig.update_yaxes(title_text=translations[lang]["salarychange"], range=[0, None], secondary_y=True)

    fig.update_yaxes(title_text=translations[lang]["salary.label"], range=[0, None], secondary_y=False)

    # Üldine layout
    fig.update_layout(
        title=translations[lang]["salary.title"],
        height=600
    )

    # Legend alla keskele
    # the plotting area without too much extra whitespace.
    fig2 = apply_common_legend(fig2, "h", -0.04, 0.5)

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

        dcc.Graph(id="salary-graph", figure=fig),
        dcc.Graph(id="salary-comparison", figure=fig2),
        html.P(translations[lang]["salaryNotice"])
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
        default_indicator = indicator_opts[0]["value"] if len(indicator_opts) > 1 else indicator_opts[0]["value"]

        # Default year value: first actual year option if available
        default_year = year_opts[0]["value"] if len(year_opts) > 1 else year_opts[0]["value"]

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
        try:
            # Kui kasutaja valib "ALL", siis lisa kõik väärtused
            indicators = None if indicator == "ALL" else indicator
            years = None if year == "ALL" else year

            df = get_pa103_data(indicator=indicators, emtak=emtak, years=years, lang=lang)

            # Kui mõlemad näitajad korraga
            if indicator is None or indicator == "ALL":

                fig = make_subplots(specs=[[{"secondary_y": True}]])

                avg_df = df[df["näitaja"] == "GR_W_AVG"]
                med_df = df[df["näitaja"] == "GR_W_D5"]
                dif_df = df[df["näitaja"] == "GR_W_AVG_SM"]

                # Avoid SettingWithCopyWarning by working on copies when we'll modify columns
                avg_df = avg_df.copy()
                med_df = med_df.copy()
                dif_df = dif_df.copy()

                # Helper to get a safe series name
                def safe_name(df_slice, default_label):
                    try:
                        return df_slice["näitaja_nimi"].iloc[0] if not df_slice.empty else default_label
                    except Exception:
                        return default_label

                avg_name = safe_name(avg_df, translations[lang].get("avg.label", "Average"))
                med_name = safe_name(med_df, translations[lang].get("med.label", "Median"))
                dif_name = safe_name(dif_df, translations[lang].get("diff.label", "Difference"))

                # Keskmine ja mediaan vasakule teljele
                fig.add_trace(
                    go.Bar(
                        x=avg_df["aasta"],
                        y=avg_df["väärtus"],
                        name=avg_name,
                        text=avg_df["väärtus"],
                        textposition="inside",
                        textfont=dict(color="white", size=12)
                    ),
                    secondary_y=False
                )

                fig.add_trace(
                    go.Bar(
                        x=med_df["aasta"],
                        y=med_df["väärtus"],
                        name=med_name,
                        text=med_df["väärtus"],
                        textposition="inside",
                        textfont=dict(color="white", size=12)
                    ),
                    secondary_y=False
                )

                # Muutus paremale teljele joonena
                dif_df["väärtus"] = pd.to_numeric(dif_df["väärtus"], errors="coerce")

                fig.add_trace(
                    go.Scatter(
                        x=dif_df["aasta"],
                        y=dif_df["väärtus"],
                        name=dif_name,
                        mode="lines+markers+text",
                        text=dif_df["väärtus"].round(1),
                        textposition="bottom center"
                    ),
                    secondary_y=True
                )

                # Telgede sildid
                fig.update_yaxes(title_text=translations[lang]["salary.label"], secondary_y=False)
                fig.update_yaxes(range=[0, None], title_text=translations[lang]["salarychange"], secondary_y=True)
                fig.update_layout(title=translations[lang]["salary.title"], height=600)
                fig = apply_common_legend(fig, "h", -0.3, 0.5)

            else:
                # Kui ainult üks näitaja
                fig = px.bar(
                    df,
                    x="aasta",
                    y="väärtus",
                    color="näitaja_nimi",
                    barmode="group",
                    text="väärtus",
                    labels={
                        "väärtus": translations[lang]["salary.label"],
                        "aasta": translations[lang]["year.label"],
                        "näitaja_nimi": translations[lang]["indicator.label"]
                    }
                )

                fig.update_yaxes(range=[0, None])

            # Legend alla keskele
            fig = apply_common_legend(fig, "h", -0.3, 0.5)
            return fig

        except Exception as e:
            # Log exception server-side and return a simple figure with the error so the client receives a response
            print("Error in update_salary_graph:", e)
            traceback.print_exc()
            err_fig = go.Figure()
            err_fig.update_layout(title=f"Error generating chart: {e}")
            return err_fig
        
    #@app.callback(
    #    Output("salary-comparison", "figure"),
     #   Input("language-dropdown", "value")
    #)
    """
    def update_salary_comparison(lang):
       
        opts = get_meta_options("PA103", lang)
        var_codes = list(opts.keys())

        emtak_code = var_codes[1]["values"]
         # Andmete päring (nt SQL või API)
        
        df2 = get_pa103_data(
            indicator=["GR_W_AVG","GR_W_D5"],
            emtak=None,
            years=None,
            lang=lang
            )
        
        latest_year = df2["aasta"].max()
        df2_latest = df2[df2["aasta"] == latest_year]

        # Arvuta keskmine ja mediaan tegevusalade kaupa
        grouped = df2.groupby("tegevusala")["palk"]
        keskmised = grouped.mean()
        mediaanid = grouped.median()

        fig = go.Figure()
        fig.add_bar(x=keskmised.index, y=keskmised.values, name="Keskmine palk")
        fig.add_bar(x=mediaanid.index, y=mediaanid.values, name="Mediaan palk")

        fig.update_layout(
            barmode="group",
            title=translations[lang]["salary.comparison.title"],
            xaxis_title=translations[lang]["salary.comparison.xaxis"],
            yaxis_title=translations[lang]["salary.comparison.yaxis"]
        )
        return fig
        """





