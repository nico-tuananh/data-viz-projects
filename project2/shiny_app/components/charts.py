"""Presentation-grade Plotly chart builders for the Shiny dashboard."""

from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from wordcloud import WordCloud

from utils.constants import MEDIA_COLORS, MODEL_COLORS, PLOT_FONT, THEME_STYLES
from utils.transforms import gap_extremes, geo_points, timeline_peaks

# Color ramps matching main branch (darkest → lightest)
_WESTERN_RAMP = ["#1D3C5E", "#2B5190", "#3D6DA0", "#5A8FCA", "#7AAAD6", "#C1D8EE"]
_CHINESE_RAMP = ["#7A2828", "#A03434", "#C24848", "#D96B6B", "#E89595", "#F4C0C0"]


def _ramp_color_func(ramp: list[str]):
    """Return a wordcloud color_func that maps TF-IDF weight → ramp color."""
    def _hex(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    rgb_ramp = [_hex(c) for c in ramp]

    def color_func(word, font_size, position, orientation, font_path, random_state, **kwargs):
        idx = max(0, min(len(rgb_ramp) - 1, int((1 - font_size / 120) * len(rgb_ramp))))
        r, g, b = rgb_ramp[idx]
        return f"rgb({r},{g},{b})"

    return color_func


def word_cloud_chart(terms: pd.DataFrame, theme_mode: str = "dark") -> bytes:
    """
    Render side-by-side Western / Chinese word clouds.
    Returns PNG bytes suitable for ui.output_image / render.image.
    """
    if terms.empty:
        return b""

    bg = "#0f172a" if theme_mode == "dark" else "#ffffff"
    western = terms[terms["group"] == "Western"]
    chinese = terms[terms["group"] == "Chinese"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor=bg)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.04, wspace=0.06)

    for ax, group_df, ramp, label in [
        (axes[0], western, _WESTERN_RAMP, "Western Media"),
        (axes[1], chinese, _CHINESE_RAMP, "Chinese Media"),
    ]:
        ax.set_facecolor(bg)
        ax.axis("off")
        label_color = ramp[2]
        ax.set_title(label, color=label_color, fontsize=12, fontweight="bold", pad=6)

        if group_df.empty:
            ax.text(0.5, 0.5, "No terms available", ha="center", va="center",
                    color="#94a3b8", fontsize=11, transform=ax.transAxes)
            continue

        freq = dict(zip(group_df["term"], group_df["score"]))
        wc = WordCloud(
            width=680,
            height=420,
            background_color=bg,
            color_func=_ramp_color_func(ramp),
            prefer_horizontal=0.75,
            max_words=65,
            min_font_size=10,
            max_font_size=90,
            margin=6,
            random_state=42,
            collocations=False,
        ).generate_from_frequencies(freq)
        ax.imshow(wc, interpolation="bilinear")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    red, green, blue = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def _empty_figure(message: str, height: int = 420, theme_mode: str = "dark") -> go.Figure:
    fig = go.Figure()
    theme = THEME_STYLES[theme_mode]
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 16, "color": theme["font_color"]},
    )
    return apply_layout(fig, height=height, show_legend=False, theme_mode=theme_mode)


def apply_layout(
    fig: go.Figure,
    height: int = 460,
    show_legend: bool = True,
    hovermode: str = "x unified",
    bottom: int = 84,
    theme_mode: str = "dark",
) -> go.Figure:
    theme = THEME_STYLES[theme_mode]
    fig.update_layout(
        height=height,
        font=dict(family=PLOT_FONT, size=13, color=theme["font_color"]),
        paper_bgcolor=theme["paper_bg"],
        plot_bgcolor=theme["plot_bg"],
        margin=dict(l=58, r=30, t=28, b=bottom),
        hovermode=hovermode,
        hoverlabel=dict(
            bgcolor=theme["hover_bg"],
            bordercolor=theme["hover_border"],
            font=dict(color=theme["font_color"], size=13),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=theme["font_color"], size=12),
            itemwidth=30,
        ),
        showlegend=show_legend,
        modebar=dict(orientation="v"),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=theme["grid"],
        zeroline=False,
        linecolor=theme["line"],
        tickfont=dict(color=theme["font_color"], size=12),
        title_font=dict(color=theme["font_color"], size=13),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=theme["grid"],
        zeroline=False,
        linecolor=theme["line"],
        tickfont=dict(color=theme["font_color"], size=12),
        title_font=dict(color=theme["font_color"], size=13),
    )
    return fig


def daily_volume_chart(daily: pd.DataFrame, theme_mode: str = "dark") -> go.Figure:
    if daily.empty:
        return _empty_figure("No daily event data for the selected filters.", 500, theme_mode)
    daily = daily.sort_values("Date").copy()
    daily["Date"] = daily["Date"].dt.strftime("%Y-%m-%d")
    theme = THEME_STYLES[theme_mode]
    fig = go.Figure()
    for group, group_df in daily.groupby("MediaGroup"):
        color = MEDIA_COLORS.get(group, "#94a3b8")
        fig.add_trace(go.Scatter(
            x=group_df["Date"],
            y=group_df["TotalEvents"],
            mode="lines+markers",
            name=group,
            line=dict(color=color, width=3.4, shape="spline", smoothing=0.75),
            marker=dict(size=7, color=color, line=dict(color=theme["hover_border"], width=1)),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(color, 0.10),
            customdata=group_df[["TotalArticles", "AvgTone"]],
            hovertemplate=(
                "<b>%{x|%b %d}</b><br>"
                "Events: %{y:,}<br>"
                "Articles: %{customdata[0]:,}<br>"
                "Avg tone: %{customdata[1]:.2f}<extra></extra>"
            ),
        ))
    for _, row in timeline_peaks(daily, 3).iterrows():
        fig.add_annotation(
            x=row["Date"],
            y=row["TotalEvents"],
            text=f"{int(row['TotalEvents']):,}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.2,
            arrowcolor=theme["font_color"],
            ax=0,
            ay=-34,
            font=dict(color=theme["font_color"], size=12),
            bgcolor=theme["annotation_bg"],
            bordercolor=theme["annotation_border"],
            borderpad=4,
        )
    fig.update_layout(xaxis_title="", yaxis_title="Events")
    return apply_layout(fig, height=500, theme_mode=theme_mode)


def narrative_map(events: pd.DataFrame, theme_mode: str = "dark") -> go.Figure:
    geo = geo_points(events)
    required = {"ActionGeo_Lat", "ActionGeo_Long", "MediaGroup", "ActionCountry", "NumArticles", "AvgTone", "Events"}
    if geo.empty or not required.issubset(geo.columns):
        return _empty_figure("No geographic event data for the selected filters.", 560, theme_mode)
    theme = THEME_STYLES[theme_mode]
    geo["hover_label"] = geo["ActionGeo_FullName"].fillna(geo["ActionCountry"])
    geo["NumArticlesPlot"] = geo["NumArticles"].clip(lower=1)
    fig = go.Figure()

    # Render order: Global/Other beneath Western and Chinese so they don't bury signals
    group_order = ["Global/Other", "Chinese", "Western"]
    group_cfg = {
        # (log_scale_mult, size_min, size_max, opacity, stroke_alpha)
        "Western":      (4.2, 5.0, 30.0, 0.84, 0.70),
        "Chinese":      (4.2, 5.0, 30.0, 0.86, 0.70),
        "Global/Other": (2.0, 3.0, 11.0, 0.38, 0.20),
    }

    for group in group_order:
        group_df = geo[geo["MediaGroup"] == group].copy()
        if group_df.empty:
            continue
        color = MEDIA_COLORS.get(group, MEDIA_COLORS["Global/Other"])
        mult, sz_min, sz_max, opacity, stroke_a = group_cfg.get(
            group, group_cfg["Global/Other"]
        )
        sizes = (np.log1p(group_df["NumArticlesPlot"]) * mult).clip(sz_min, sz_max)

        fig.add_trace(go.Scattergeo(
            lon=group_df["ActionGeo_Long"],
            lat=group_df["ActionGeo_Lat"],
            text=group_df["hover_label"],
            customdata=group_df[["ActionCountry", "Events", "NumArticles", "AvgTone", "TopSource", "Directions"]],
            marker=dict(
                size=sizes,
                color=color,
                opacity=opacity,
                line=dict(color=f"rgba(255,255,255,{stroke_a})", width=0.7),
            ),
            name=group,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Country: %{customdata[0]}<br>"
                "Events: %{customdata[1]:,}<br>"
                "Articles: %{customdata[2]:,}<br>"
                "Avg tone: %{customdata[3]:.2f}<br>"
                "Top source: %{customdata[4]}<br>"
                "Directions: %{customdata[5]}<extra></extra>"
            ),
        ))

    geo_layout = dict(
        projection_type="orthographic",
        projection_rotation=dict(lat=15, lon=10, roll=0),
        projection_scale=1.05,
    )

    fig.update_geos(
        showland=True,
        landcolor=theme["land"],
        showcountries=True,
        countrycolor=theme["country"],
        showocean=True,
        oceancolor=theme["ocean"],
        showlakes=True,
        lakecolor=theme["ocean"],
        coastlinecolor=theme["coast"],
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
        **geo_layout,
    )

    # Tight margins so globe fills the card; legend sits just below
    fig.update_layout(
        height=560,
        font=dict(family=PLOT_FONT, size=13, color=theme["font_color"]),
        paper_bgcolor=theme["paper_bg"],
        margin=dict(l=4, r=4, t=16, b=52),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor=theme["hover_bg"],
            bordercolor=theme["hover_border"],
            font=dict(color=theme["font_color"], size=13),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.04,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=theme["font_color"], size=12),
            itemwidth=30,
        ),
        showlegend=True,
    )
    return fig


def narrative_flat_map(events: pd.DataFrame, theme_mode: str = "dark") -> go.Figure:
    """Full-world natural-earth flat map — global spread overview."""
    geo = geo_points(events)
    required = {"ActionGeo_Lat", "ActionGeo_Long", "MediaGroup", "ActionCountry", "NumArticles", "AvgTone", "Events"}
    if geo.empty or not required.issubset(geo.columns):
        return _empty_figure("No geographic event data for the selected filters.", 500, theme_mode)
    theme = THEME_STYLES[theme_mode]
    geo["hover_label"] = geo["ActionGeo_FullName"].fillna(geo["ActionCountry"])
    geo["NumArticlesPlot"] = geo["NumArticles"].clip(lower=1)
    fig = go.Figure()

    # Same render order as globe: Global/Other first so Western/Chinese render on top
    group_order = ["Global/Other", "Chinese", "Western"]

    # Per-group config: (color, log_scale_mult, size_min, size_max, opacity, stroke_alpha)
    # Global/Other uses a darker medium-gray (#6e7f93) at 0.60 opacity so it's clearly
    # visible without competing with the blue/red primary signals.
    group_cfg = {
        "Western":      (MEDIA_COLORS["Western"], 3.6, 4.0, 20.0, 0.82, 0.65),
        "Chinese":      (MEDIA_COLORS["Chinese"], 3.6, 4.0, 20.0, 0.84, 0.65),
        "Global/Other": ("#6e7f93",               1.7, 2.5,  9.0, 0.60, 0.35),
    }

    for group in group_order:
        group_df = geo[geo["MediaGroup"] == group].copy()
        if group_df.empty:
            continue
        color, mult, sz_min, sz_max, opacity, stroke_a = group_cfg.get(
            group, group_cfg["Global/Other"]
        )
        sizes = (np.log1p(group_df["NumArticlesPlot"]) * mult).clip(sz_min, sz_max)

        fig.add_trace(go.Scattergeo(
            lon=group_df["ActionGeo_Long"],
            lat=group_df["ActionGeo_Lat"],
            text=group_df["hover_label"],
            customdata=group_df[["ActionCountry", "Events", "NumArticles", "AvgTone", "TopSource", "Directions"]],
            marker=dict(
                size=sizes,
                color=color,
                opacity=opacity,
                line=dict(color=f"rgba(255,255,255,{stroke_a})", width=0.6),
            ),
            name=group,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Country: %{customdata[0]}<br>"
                "Events: %{customdata[1]:,}<br>"
                "Articles: %{customdata[2]:,}<br>"
                "Avg tone: %{customdata[3]:.2f}<br>"
                "Top source: %{customdata[4]}<br>"
                "Directions: %{customdata[5]}<extra></extra>"
            ),
        ))

    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor=theme["land"],
        showcountries=True,
        countrycolor=theme["country"],
        showocean=True,
        oceancolor=theme["ocean"],
        showlakes=False,
        coastlinecolor=theme["coast"],
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
        lataxis_range=[-65, 85],
        lonaxis_range=[-180, 180],
    )

    fig.update_layout(
        # geo.domain [0,1]×[0,1] tells Plotly the map subplot fills the entire
        # figure area; combined with zero left/right margins this eliminates the
        # wide empty bands on both sides of the natural-earth projection.
        geo=dict(domain=dict(x=[0, 1], y=[0, 1])),
        height=480,
        autosize=True,
        font=dict(family=PLOT_FONT, size=13, color=theme["font_color"]),
        paper_bgcolor=theme["paper_bg"],
        margin=dict(l=0, r=0, t=0, b=58),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor=theme["hover_bg"],
            bordercolor=theme["hover_border"],
            font=dict(color=theme["font_color"], size=13),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.06,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=theme["font_color"], size=12),
            itemwidth=30,
        ),
        showlegend=True,
    )
    return fig


def tone_gap_chart(tone_gap: pd.DataFrame, theme_mode: str = "dark") -> go.Figure:
    if tone_gap.empty or "ToneGap" not in tone_gap:
        return _empty_figure("ToneGap data is unavailable for this date range.", 500, theme_mode)
    gap = tone_gap.sort_values("Date").copy()
    gap["Date"] = gap["Date"].dt.strftime("%Y-%m-%d")
    theme = THEME_STYLES[theme_mode]
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=max(gap["ToneGap"].max(skipna=True), 0), fillcolor=theme["subtle_positive"], line_width=0)
    fig.add_hrect(y0=min(gap["ToneGap"].min(skipna=True), 0), y1=0, fillcolor=theme["subtle_negative"], line_width=0)
    fig.add_trace(go.Scatter(
        x=gap["Date"],
        y=gap["ToneGap"],
        mode="lines+markers",
        line=dict(color=MEDIA_COLORS["ToneGap"], width=3.6, shape="spline", smoothing=0.65),
        marker=dict(size=7, color=MEDIA_COLORS["ToneGap"], line=dict(color="#fff7ed", width=1)),
        name="ToneGap",
        customdata=gap[["WesternTone", "ChineseTone"]].apply(
            lambda col: col.map(lambda v: f"{v:.2f}" if pd.notna(v) else "n/a")
        ),
        hovertemplate=(
            "<b>%{x|%b %d}</b><br>"
            "ToneGap: %{y:.2f}<br>"
            "Western tone: %{customdata[0]}<br>"
            "Chinese tone: %{customdata[1]}<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=theme["baseline"])
    max_gap, min_gap = gap_extremes(gap)
    for row, label, ay in [(max_gap, "largest positive", -42), (min_gap, "largest negative", 42)]:
        if row is None:
            continue
        fig.add_annotation(
            x=row["Date"],
            y=row["ToneGap"],
            text=f"{label}: {row['ToneGap']:.2f}",
            showarrow=True,
            arrowcolor=theme["font_color"],
            arrowwidth=1,
            ax=0,
            ay=ay,
            font=dict(color=theme["font_color"], size=12),
            bgcolor=theme["annotation_bg"],
            bordercolor=theme["annotation_border"],
            borderpad=4,
        )
    note_color = "rgba(219,234,254,0.52)" if theme_mode == "dark" else "rgba(15,23,42,0.42)"
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0, y=-0.13,
        text="Note: Line breaks mark dates where ToneGap could not be computed because one media side had no valid tone records.",
        showarrow=False,
        font=dict(size=13, color=note_color),
        xanchor="left",
        yanchor="top",
    )
    fig.update_layout(xaxis_title="", yaxis_title="Western tone - Chinese tone", margin=dict(b=70))
    return apply_layout(fig, height=500, theme_mode=theme_mode)


def tone_distribution_chart(events: pd.DataFrame, theme_mode: str = "dark") -> go.Figure:
    if events.empty:
        return _empty_figure("No event-level tone data for the selected filters.", 440, theme_mode)
    fig = go.Figure()
    for group, group_df in events.groupby("MediaGroup"):
        fig.add_trace(go.Violin(
            x=[group] * len(group_df),
            y=group_df["AvgTone"],
            name=group,
            box_visible=True,
            meanline_visible=True,
            line_color=MEDIA_COLORS.get(group, MEDIA_COLORS["Global/Other"]),
            fillcolor=_hex_to_rgba(MEDIA_COLORS.get(group, MEDIA_COLORS["Global/Other"]), 0.28),
            opacity=0.78,
            points=False,
            hovertemplate=f"{group}<br>Avg tone: %{{y:.2f}}<extra></extra>",
        ))
    fig.update_layout(xaxis_title="", yaxis_title="Average tone")
    return apply_layout(fig, height=440, show_legend=False, hovermode="closest", bottom=55, theme_mode=theme_mode)


def tone_intensity_chart(daily: pd.DataFrame, theme_mode: str = "dark") -> go.Figure:
    if daily.empty:
        return _empty_figure("No coverage intensity data for the selected filters.", 460, theme_mode)
    theme = THEME_STYLES[theme_mode]
    fig = go.Figure()
    for group, group_df in daily.groupby("MediaGroup"):
        color = MEDIA_COLORS.get(group, MEDIA_COLORS["Global/Other"])
        fig.add_trace(go.Scatter(
            x=group_df["TotalArticles"],
            y=group_df["AvgTone"],
            mode="markers",
            name=group,
            marker=dict(
                size=(group_df["TotalEvents"] ** 0.5) * 3.7,
                color=color,
                opacity=0.58,
                line=dict(width=0.8, color=theme["hover_border"]),
            ),
            customdata=group_df[["Date", "TotalEvents"]].assign(
                Date=group_df["Date"].dt.strftime("%b %d")
            ),
            hovertemplate=(
                f"{group}<br>"
                "Date: %{customdata[0]}<br>"
                "Articles: %{x:,}<br>"
                "Events: %{customdata[1]:,}<br>"
                "Avg tone: %{y:.2f}<extra></extra>"
            ),
        ))
    fig.add_hline(y=0, line_dash="dot", line_color=theme["baseline"])
    fig.update_layout(xaxis_title="Article volume", yaxis_title="Average tone")
    return apply_layout(fig, height=460, hovermode="closest", theme_mode=theme_mode)


def keyword_chart(keywords: pd.DataFrame, top_n: int, theme_mode: str = "dark") -> go.Figure:
    if keywords.empty:
        return _empty_figure("No distinctive headline terms available for the selected filters.", 480, theme_mode)
    western = keywords[keywords["group"] == "Western"].nlargest(top_n, "score")
    chinese = keywords[keywords["group"] == "Chinese"].nlargest(top_n, "score")
    plot_df = pd.concat([western, chinese], ignore_index=True)
    plot_df["display_score"] = plot_df["signed_score"]
    plot_df = plot_df.sort_values("display_score")
    colors = [MEDIA_COLORS.get(group, "#94a3b8") for group in plot_df["group"]]
    fig = go.Figure(go.Bar(
        x=plot_df["display_score"],
        y=plot_df["term"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(255,255,255,0.22)", width=0.6)),
        customdata=plot_df[["group", "score", "count", "doc_count"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Media group: %{customdata[0]}<br>"
            "Distinctiveness: %{customdata[1]:.4f}<br>"
            "Mentions: %{customdata[2]:,}<br>"
            "Documents: %{customdata[3]:,}<extra></extra>"
        ),
    ))
    theme = THEME_STYLES[theme_mode]
    fig.add_vline(x=0, line_color=theme["baseline"], line_width=1.2)
    fig.add_annotation(x=0.98, y=1.05, xref="paper", yref="paper", text="Western distinctive", showarrow=False, font=dict(color=MEDIA_COLORS["Western"], size=12))
    fig.add_annotation(x=0.02, y=1.05, xref="paper", yref="paper", text="Chinese distinctive", showarrow=False, font=dict(color=MEDIA_COLORS["Chinese"], size=12))
    chart_height = min(620, max(430, 11 * len(plot_df) + 150))
    fig.update_layout(
        xaxis_title="Contrastive TF-IDF score",
        yaxis_title="",
        height=chart_height,
    )
    fig.update_xaxes(tickformat=".3f")
    return apply_layout(fig, height=chart_height, show_legend=False, hovermode="closest", bottom=68, theme_mode=theme_mode)


def forecast_chart(predictions: pd.DataFrame, models: list[str], best_model: str | None = None, theme_mode: str = "dark") -> go.Figure:
    if predictions.empty:
        return _empty_figure("Forecast predictions unavailable. Regenerate model output first.", 500, theme_mode)
    selected = predictions[predictions["Model"].isin(models)].copy() if models else predictions.iloc[0:0].copy()
    if selected.empty:
        return _empty_figure("Select at least one forecast model in the sidebar.", 500, theme_mode)
    # Convert datetime64 to string so Plotly renders readable dates instead of nanosecond ints
    if pd.api.types.is_datetime64_any_dtype(selected["Date"]):
        selected["Date"] = selected["Date"].dt.strftime("%Y-%m-%d")
    actual = selected[["Date", "Actual"]].drop_duplicates("Date").sort_values("Date")
    theme = THEME_STYLES[theme_mode]
    fig = go.Figure()

    # Predicted model lines first (so actual sits on top visually)
    for model in models:
        model_df = selected[selected["Model"] == model].sort_values("Date")
        if model_df.empty:
            continue
        color = MODEL_COLORS.get(model, "#94a3b8")
        is_best = best_model is not None and model == best_model
        fig.add_trace(go.Scatter(
            x=model_df["Date"],
            y=model_df["Predicted"],
            mode="lines",
            line=dict(
                color=color,
                width=2.6 if is_best else 1.5,
                dash="solid" if is_best else "dash",
                shape="spline",
                smoothing=0.5,
            ),
            opacity=1 if is_best else 0.60,
            name=f"{model} (Best MAE)" if is_best else model,
            hovertemplate=f"<b>{model}</b><br>%{{x|%b %d}}<br>Predicted: %{{y:.2f}}<extra></extra>",
        ))

    # Actual ToneGap — dominant thick bright line on top
    actual_color = "#ffffff" if theme_mode == "dark" else "#0f172a"
    fig.add_trace(go.Scatter(
        x=actual["Date"],
        y=actual["Actual"],
        mode="lines+markers",
        line=dict(color=actual_color, width=4.8),
        marker=dict(size=7, color=actual_color, line=dict(color=theme["hover_border"], width=1)),
        name="Observed ToneGap",
        hovertemplate="<b>%{x|%b %d}</b><br>Observed ToneGap: %{y:.2f}<extra></extra>",
    ))

    if not actual.empty:
        split_date = actual["Date"].min()
        fig.add_shape(
            type="line",
            x0=split_date, x1=split_date, y0=0, y1=1, yref="paper",
            line=dict(color=MEDIA_COLORS["ToneGap"], width=1.6, dash="dot"),
        )
        fig.add_annotation(
            x=split_date, y=1.06, yref="paper",
            text="← Holdout window begins",
            showarrow=False,
            font=dict(color=MEDIA_COLORS["ToneGap"], size=11),
            bgcolor=theme["annotation_bg"],
            bordercolor=theme["annotation_border"],
            borderpad=4,
            xanchor="left",
        )

    fig.add_hline(y=0, line_dash="dot", line_color=theme["baseline"], line_width=0.8)
    fig.update_layout(xaxis_title="Date", yaxis_title="ToneGap (Western − Chinese)")
    fig.update_xaxes(type="date", tickformat="%b %d")
    return apply_layout(fig, height=500, theme_mode=theme_mode, bottom=90)
