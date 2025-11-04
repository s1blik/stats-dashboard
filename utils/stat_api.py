import requests
import inspect

import pandas as pd
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

        
    if emtak is not None:
        query.append({
            "code": "Tegevusala",
            "selection": {"filter": "item", "values": [emtak]}
        }) 

    if years:
        if isinstance(years, (int, str)):
            years = [str(years)]
        else:
            years = [str(y) for y in years]
        query.append({
            "code": "Vaatlusperiood",
            "selection": {"filter": "item", "values": years}
        })

    
    #print("PA103 query:", query)

    rows = fetch_data("PA103", query)  # peab tagastama res.json()["data"]
    
    # lahti kirjutad key’d arusaadavateks veergudeks
    return pd.DataFrame([{
        "näitaja": row["key"][0],
        "tegevusala": row["key"][1],
        "aasta": row["key"][2],
        "väärtus": float(row["values"][0]) if row["values"][0] not in (None, "", ".","..", ":") else None
    } for row in rows
      for val in [row["values"][0]]
])

