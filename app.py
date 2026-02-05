import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
from components.sidebar import sidebar_layout

from translation import translations
from layouts.economy.salary import register_salary_callbacks, salary_layout
from layouts.economy.salary_short import salary_short_layout
#from layouts.economy.salary_short import register_salary_short_callbacks, salary_short_layout
from layouts.environment.envirStatus import envirstatus_layout
from layouts.population.ive import ive_layout
from utils.helpers import ask_gpt, get_openai_client, set_openai_client
from pathlib import Path
from dotenv import load_dotenv
import os
import time


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)
client = get_openai_client()
set_openai_client(client)


app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Stats Dashboard"

# Renderi jaoks vajalik Flask serveri objekt
server = app.server


app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Input(id="input", type="text"),
    dcc.Loading(
        id="loading",
        type="circle",   # või "default", "dot"
        children=html.Div(id="output")
    ),

    # Globaalne keel, salvestatakse brauseri localStorage'i
    dcc.Store(id="language-store", data="et", storage_type="local"),  # ← globaalne keel
    
     # Keelevalik dropdown
    html.Div([
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
    
    html.Div([
        html.Div([
            html.Button("Küsi GPT-lt",
                         id="ask_button",
                         style={"backgroundColor":"#4CAF50","color":"white"}),
            dcc.Textarea(id="user_input", style={"border":"None","width": "400px", "height": "100px"})
            ], 
            style={
                "display":"none", 
                "margins": "10px",
                "alignSelf": "center",
                "border": "1px solid black",
                "flexDirection": "column",
                "alignItems": "center"
            }),
        
                
        dcc.Loading(
            type="circle",
            children=html.Div(id="gpt_response"), style={"alignItems": "center"}),
        dcc.Store(id="loading_state", data=False)  # False = not loading
    ], 
        style={            
            "display": "flex",
            "justifyContent": "flex-end",
            "marginLeft": "14%",
            "padding": "10px"
    }),

    # Siia renderdatakse lehe sisu  
    html.Div(
        id="page-content", style={"marginLeft": "14%", "padding": "20px", "border": "1px solid lightgrey"})
])

# 1 Clientside callback – kohe klikil: loading_state=True
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            return true;   // kohe klikil loading=True
        }
        return false;
    }
    """,
    Output("loading_state", "data"),
    Input("ask_button", "n_clicks"),
    prevent_initial_call=True
)

# 2 Server callback – teeb töö, tagastab ainult gpt_response.children
@app.callback(
    Output("gpt_response", "children"),
    Input("ask_button", "n_clicks"),
    State("user_input", "value"),
    prevent_initial_call=True
)
def fetch_response(n_clicks, user_text):
    time.sleep(2)  # simuleeri aeglast päringut

    result = ask_gpt(user_text)
    print("GPT vastus:", result)
    # NB: ei puuduta loading_state siin, ainult response
    return result

# 3 Mapping callback – seab disabled oleku loading_state põhjal
@app.callback(
    Output("ask_button", "disabled"),
    Output("user_input", "disabled"),
    Input("loading_state", "data"),
)
def set_disabled(is_loading):
    disabled = bool(is_loading)
    return disabled, disabled


#--------------------------------------------------------------------------------------

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
    elif pathname == "/economy/shortterm":
        content = salary_short_layout(lang)
    else:
        content = salary_layout(lang)  # default
    
    return html.Div([
        sidebar_layout(lang),
        html.Div(content, style={"marginLeft": "5%", "padding": "20px"})
    ])

register_salary_callbacks(app)
#register_salary_short_callbacks(app)


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
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
