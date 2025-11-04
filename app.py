import dash
from dash import html, dcc
from dash.dependencies import Input, Output
from components.sidebar import sidebar_layout
from translation import translations
from layouts.economy.salary import register_salary_callbacks, salary_layout
from layouts.environment.envirStatus import envirstatus_layout
from layouts.population.ive import ive_layout

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Stats Dashboard"
app.layout = html.Div([
    dcc.Location(id="url"),
    # Globaalne keel, salvestatakse brauseri localStorage'i
    dcc.Store(id="language-store", data="et", storage_type="local"),  # ← globaalne keel
    
     # Keelevalik dropdown
    html.Div([
        #html.Label("Language / Keel:", style= # "Language / Keel:"
        html.Div(id="language-label",
                  style={
                    "marginRight": "10px",
                    "alignSelf": "center"
                    }),
        dcc.Dropdown(
            id="language-dropdown",
            options=[
                {"label": "Eesti", "value": "et"},
                {"label": "English", "value": "en"}
            ],
            value="et",                 # first-time default
            clearable=False,
            persistence=True,           # persist selection
            persistence_type="local",    # across browser restarts

            style={"width": "200px"}
        ),    
    ], style={"display": "flex", "justifyContent": "flex-end", "padding": "10px"}),

    #sidebar,

    # Siia renderdatakse lehe sisu  
    html.Div(id="page-content", style={"marginLeft": "20%", "padding": "20px"})
])


@app.callback(
        Output("page-content", "children"),
        [Input("url", "pathname"),
         Input("language-store", "data")]   # ← lisa ka see Input
)
def display_page(pathname, lang):
    if not lang:
        lang = "et"

    if pathname == "/enviroment":
        content = envirstatus_layout(lang)
    elif pathname == "/population":
        content = ive_layout(lang)
    else:
        content = salary_layout(lang)  # default
    
    return html.Div([
        sidebar_layout(lang),
        html.Div(content, style={"marginLeft": "15%", "padding": "20px"})
    ])

register_salary_callbacks(app)

#Dropdown → Store
@app.callback(
    Output("language-store", "data"),
    Input("language-dropdown", "value")
)
def update_language_store(selected_lang):
    return selected_lang

@app.callback(
    Output("language-label", "children"),
    Input("language-store", "data")
)
def update_label(lang):
    if not lang:
        lang = "et"
    return translations[lang]["language.label"]



if __name__ == "__main__":
    app.run(debug=True)