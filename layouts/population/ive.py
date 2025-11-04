from dash import html
from translation import translations   # ← import siit

ive_layout = html.Div([
    html.H3("Rahvastikustatistika – tulekul")
])

def ive_layout(lang="et"):

 return html.Div([
        html.H3(translations[lang]["ive_header"]),

])