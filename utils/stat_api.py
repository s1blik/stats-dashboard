import requests

import pandas as pd

from utils.helpers import get_meta_options
from .fetch_data import fetch_data


def get_pa103_data(indicator=None, emtak="TOTAL", years=None, lang="et"):

    """
    PA103 tabeli wrapper, mis ehitab päringu ja tagastab DataFrame'i.
    """
    
    query = []

    # Näitaja filter ainult siis, kui indicator on antud
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

    # Metaandmed dimensioonide järjekorra jaoks
    meta = requests.get(url).json()
    variables = [v["code"] for v in meta["variables"]]

    #print("PA103 query:", query)

    df = pd.DataFrame([
            {
                "näitaja": mapping.get("Näitaja"),
                "tegevusala": mapping.get("Tegevusala"),
                "aasta": mapping.get("Vaatlusperiood"),
                "väärtus": float(val) if val not in (None, "", ".", "..", ":") else None
            }
            for row in rows
            for val in [row["values"][0]]
            for mapping in [dict(zip(variables, row["key"]))]
        ])

    # Lisa inimloetavad nimetused
    opts = get_meta_options("PA103", lang)
    indicator_map = {opt["value"]: opt["label"] for opt in opts["Näitaja"]}
    df["näitaja_nimi"] = df["näitaja"].map(indicator_map)

    # Kindlusta, et väärtus on numbriline
    df["väärtus"] = pd.to_numeric(df["väärtus"], errors="coerce")

    return df
