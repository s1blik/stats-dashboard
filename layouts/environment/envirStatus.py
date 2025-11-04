from dash import html
from translation import translations   # ← import siit

def envirstatus_layout(lang="et"):

 return html.Div([
        html.H3(translations[lang]["envirstatus_header"]),

])
