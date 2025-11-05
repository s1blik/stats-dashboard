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
