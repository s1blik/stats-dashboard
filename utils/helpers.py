import requests


def apply_common_legend(fig, orientation, y, x):
    """Lisa graafikule ühtne legendi paigutus (alla keskele)."""
    fig.update_layout(
        legend=dict(
            orientation= orientation,
            yanchor="bottom",
            y = y,
            xanchor="center",
            x = x
        )
    )
    return fig

# Abifunktsioon metaandmete jaoks

def get_meta_options(table="PA103", lang="et"):
    url = f"https://andmed.stat.ee/api/v1/{lang}/stat/{table}"
    meta = requests.get(url).json()

    opts = {}
    for v in meta["variables"]:
        code = v["code"]
        values = v["values"]
        labels = v["valueTexts"]
        opts[code] = [{"label": lbl, "value": val} for val, lbl in zip(values, labels)]
    return opts