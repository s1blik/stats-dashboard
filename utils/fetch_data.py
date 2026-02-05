import pandas as pd
import requests


def fetch_data(table: str, query: list, lang: str = "et"): #-> pd.DataFrame:
    """
    Üldine andmete tõmbamise funktsioon Statistikaameti API-st.
    
    :param table: tabeli kood (nt "PA103")
    :param query: päringu filterite list (API formaadis)
    :param lang: "et" või "en" – API keeleversioon
    :return: pandas DataFrame toorandmetega
    """
    #print("PA103 query:", query)

    url = f"https://andmed.stat.ee/api/v1/{lang}/stat/{table}"
    payload = {
        "query": query,
        "response": {"format": "json"}
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()
    return res.json()["data"]

