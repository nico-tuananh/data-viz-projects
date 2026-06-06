from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pandas as pd
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly, render_widget

from components.charts import (
    daily_volume_chart,
    forecast_chart,
    keyword_chart,
    narrative_flat_map,
    narrative_map,
    tone_distribution_chart,
    tone_gap_chart,
    tone_intensity_chart,
    word_cloud_chart,
)
from components.chatbot import chatbot_panel
from components.layout import chart_card, insight_card, kpi_card, story_section, ui_card
from utils.dashboard_context import build_context
from utils.data import available_media, date_bounds, filter_by_controls, load_dashboard_data, top_sources
from utils.deepseek_client import (
    SYSTEM_PROMPT,
    call_deepseek,
    format_message,
    get_local_answer,
)
from utils.text import framing_dataframe, word_cloud_terms
from utils.transforms import event_daily, forecast_metric_cards as forecast_metric_rows


APP_DIR = Path(__file__).parent
DATA = load_dashboard_data()
DATE_MIN, DATE_MAX = date_bounds(DATA.events)
MEDIA_CHOICES = available_media(DATA.events)
DEFAULT_KEYWORDS = framing_dataframe(DATA.events, 30) if not DATA.events.empty else pd.DataFrame()
DEFAULT_CLOUD_TERMS = word_cloud_terms(DATA.events, 100) if not DATA.events.empty else pd.DataFrame()
FORECAST_MODELS = (
    sorted(DATA.forecast_predictions["Model"].dropna().unique().tolist())
    if not DATA.forecast_predictions.empty and "Model" in DATA.forecast_predictions
    else []
)


def story_nav():
    links = [
        ("01", "Timeline", "#timeline"),
        ("02", "Spread", "#spread"),
        ("03", "Divergence", "#divergence"),
        ("04", "Framing", "#framing"),
        ("05", "Forecast", "#forecast"),
    ]
    return ui.div(
        ui.div("Storyline", class_="story-nav-label"),
        ui.div(
            *[
                ui.a(ui.span(num), label, href=href, class_="story-nav-link")
                for num, label, href in links
            ],
            class_="story-nav-links",
        ),
        class_="story-nav",
    )


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.div(
            ui.div("Control room", class_="sidebar-eyebrow"),
            ui.h3("Live filters"),
            ui.p(
                "Every chart updates from the same precomputed GDELT sample.",
                class_="sidebar-copy",
            ),
            class_="sidebar-head",
        ),
        ui.input_date_range(
            "date_range",
            "Date range",
            start=DATE_MIN.date(),
            end=DATE_MAX.date(),
            min=DATE_MIN.date(),
            max=DATE_MAX.date(),
        ),
        ui.input_checkbox_group(
            "media_groups",
            "Media groups",
            choices=MEDIA_CHOICES,
            selected=MEDIA_CHOICES,
        ),
        ui.input_radio_buttons(
            "theme_mode",
            "Theme",
            choices={"dark": "Dark", "light": "Light"},
            selected="dark",
            inline=True,
        ),
        width=300,
        class_="sidebar-shell",
    ),

    # ── Head: fonts, theme sync, CSS ─────────────────────────────────────────
    ui.tags.head(
        ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1"),
        ui.tags.link(rel="preconnect", href="https://fonts.googleapis.com"),
        ui.tags.link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        ui.tags.link(
            rel="stylesheet",
            href=(
                "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700"
                "&family=Source+Serif+4:wght@600;700;800&display=swap"
            ),
        ),
        ui.tags.script(
            """
            (function() {
              function syncTheme() {
                var sel = document.querySelector('input[name="theme_mode"]:checked');
                document.documentElement.dataset.theme = sel ? sel.value : "dark";
              }
              document.addEventListener("change", function(e) {
                if (e.target && e.target.name === "theme_mode") syncTheme();
              });
              document.addEventListener("DOMContentLoaded", function() {
                setTimeout(syncTheme, 0);
              });
              document.addEventListener("shiny:connected", function() {
                setTimeout(syncTheme, 0);
              });
            })();
            """
        ),
        # link_files so CSS can serve sibling static assets (images) correctly
        ui.include_css(APP_DIR / "static" / "styles.css", method="link_files"),
        ui.tags.script(
            """
            (function() {
              var SECTION_IDS = ['timeline', 'spread', 'divergence', 'framing', 'forecast'];

              function initStoryNav() {
                var links = document.querySelectorAll('.story-nav-link');
                if (!links.length) { return; }

                function setActive(id) {
                  links.forEach(function(l) {
                    var match = l.getAttribute('href') === '#' + id;
                    l.classList.toggle('active', match);
                  });
                }

                // Click → activate immediately (before scroll settles)
                links.forEach(function(link) {
                  link.addEventListener('click', function() {
                    var href = link.getAttribute('href');
                    if (href && href.startsWith('#')) {
                      setActive(href.slice(1));
                    }
                  });
                });

                // IntersectionObserver → activate on scroll
                // rootMargin keeps the detection zone between the sticky nav
                // bottom (~48px) and the middle of the viewport.
                var visible = new Set();
                var observer = new IntersectionObserver(function(entries) {
                  entries.forEach(function(e) {
                    if (e.isIntersecting) { visible.add(e.target.id); }
                    else                  { visible.delete(e.target.id); }
                  });
                  // Pick the topmost visible section in document order
                  for (var i = 0; i < SECTION_IDS.length; i++) {
                    if (visible.has(SECTION_IDS[i])) {
                      setActive(SECTION_IDS[i]);
                      return;
                    }
                  }
                }, { rootMargin: '-48px 0px -48% 0px', threshold: 0 });

                SECTION_IDS.forEach(function(id) {
                  var el = document.getElementById(id);
                  if (el) { observer.observe(el); }
                });
              }

              document.addEventListener('DOMContentLoaded', function() { setTimeout(initStoryNav, 150); });
              document.addEventListener('shiny:connected',   function() { setTimeout(initStoryNav, 150); });
            })();
            """
        ),
    ),

    # ── Hero ─────────────────────────────────────────────────────────────────
    ui.div(
        # Explicit <img> element — most reliable way to show image regardless of
        # CSS url() path resolution. Positioned to fill the rounded card area.
        ui.tags.img(
            src="US-China-trade-war-web2.jpg",
            class_="hero-photo",
            alt="US and China shipping containers colliding, symbolising the tariff conflict",
        ),
        ui.div(
            ui.div(
                ui.div(
                    "Interactive media-intelligence dashboard · Feb 1 – Apr 30, 2025",
                    class_="hero-eyebrow",
                ),
                ui.h1("Tariff Tensions, Narrative Divides"),
                ui.p(
                    "An interactive media-intelligence dashboard tracing when tariff-war coverage "
                    "intensified, where the story travelled, how emotional tone diverged, and which "
                    "words shaped the frame.",
                    class_="hero-subtitle",
                ),
                ui.div(
                    ui.span("Western", class_="legend-chip western"),
                    ui.span("Chinese", class_="legend-chip chinese"),
                    ui.span("Global / Other", class_="legend-chip global"),
                    ui.span("ToneGap", class_="legend-chip tonegap"),
                    class_="hero-legend",
                ),
                class_="hero-copy",
            ),
            ui.div(
                ui.div("Research question", class_="side-label"),
                ui.p(
                    "Do media systems merely report tariff escalation, or do they construct "
                    "different emotional narratives around the same conflict?",
                    class_="hero-question",
                ),
                ui.div("Dataset window: Feb 1 – Apr 30, 2025", class_="hero-date"),
                class_="hero-brief",
            ),
            class_="hero-grid",
        ),
        ui.div(
            kpi_card("Events", "kpi_events", "GDELT event records", "kpi-gray"),
            kpi_card("Articles", "kpi_articles", "Total article mentions", "kpi-gray"),
            kpi_card("Unique sources", "kpi_sources", "News domains", "kpi-gray"),
            kpi_card("Western tone", "kpi_western", "Mean event tone", "kpi-blue"),
            kpi_card("Chinese tone", "kpi_chinese", "Mean event tone", "kpi-red"),
            class_="kpi-grid",
        ),
        ui.output_ui("warning_banner"),
        class_="hero",
    ),

    story_nav(),

    # ── Section 1 — Conflict Timeline ────────────────────────────────────────
    story_section(
        "timeline",
        "01",
        "Conflict Timeline",
        "When did tariff-war coverage intensify?",
        "Daily event volume by media group from Feb–Apr 2025. Use the date range and media-group "
        "filters to isolate any sub-period.",
        "Look for synchronized spikes versus moments where one bloc drives the surge alone. Peak "
        "labels mark the three largest filtered days.",
        ui.div(
            insight_card(
                "Signal",
                "Peak labels mark the three largest filtered daily event spikes.",
                "accent-blue",
            ),
            insight_card(
                "Interaction",
                "Hover any line to compare events, article references, and tone for that date.",
                "accent-amber",
            ),
            class_="insight-row",
        ),
        chart_card(
            "Media-intensity timeline",
            "Daily event volume by media group",
            "daily_volume",
            "500px",
            "feature-card",
            tip="Hover for details · drag to zoom · double-click to reset · click legend to toggle groups",
        ),
    ),

    # ── Section 2 — Narrative Spread ─────────────────────────────────────────
    story_section(
        "spread",
        "02",
        "Narrative Spread",
        "Where did the story travel?",
        "Toggle between the Pacific-centred 3-D globe and a full-world flat map. "
        "Both views use the same filtered event data.",
        "Blue = Western outlets · Red/coral = Chinese · Gray = Global/Other (muted). "
        "Hover any marker for country, tone, and top source.",
        # ── Custom map card with in-header view switcher ──────────────────
        ui.div(
            ui.div(
                ui.div(
                    ui.div(
                        "Interactive event geography · up to 1,200 sampled locations",
                        class_="chart-kicker",
                    ),
                    ui.h3("Geopolitical coverage map"),
                    class_="map-card-title",
                ),
                ui.div(
                    ui.input_radio_buttons(
                        "map_style",
                        None,
                        choices={
                            "globe": "  🌏 Globe",
                            "flat":  "  🗺 Flat World Map",
                        },
                        selected="globe",
                        inline=True,
                    ),
                    class_="map-style-switcher",
                ),
                class_="chart-card-header map-card-header",
            ),
            ui.output_ui("map_tip"),
            ui.div(output_widget("spread_map", height="560px"), class_="chart-stage"),
            class_="chart-card map-card",
        ),
        # Dynamic insight card — text updates when view switches
        ui.output_ui("spread_insight"),
        ui.div(
            ui.div(
                ui.input_select(
                    "source_top_n",
                    "Top N sources",
                    choices={"5": "Top 5", "10": "Top 10", "15": "Top 15", "20": "Top 20", "9999": "All"},
                    selected="10",
                ),
                class_="source-control",
            ),
            ui.div(
                ui.input_text(
                    "source_search",
                    "Search source",
                    placeholder="reuters.com, scmp.com…",
                ),
                class_="source-control",
            ),
            ui.div(
                ui.input_select(
                    "source_sort",
                    "Sort by",
                    choices={"Events": "Events", "Articles": "Articles", "AvgTone": "Avg tone"},
                    selected="Events",
                ),
                class_="source-control",
            ),
            class_="source-controls",
        ),
        ui_card(
            "Source domains",
            "Outlets most represented in the current filter",
            "source_table",
            "source-card",
        ),
    ),

    # ── Section 3 — Emotional Divergence ─────────────────────────────────────
    story_section(
        "divergence",
        "03",
        "Emotional Divergence",
        "How did emotional tone split across media groups?",
        "ToneGap = Western weighted tone − Chinese weighted tone. Positive values mean Western "
        "coverage is warmer than Chinese coverage on the same day. "
        "Note: ToneGap is precomputed from all Western and Chinese events — "
        "the media-group filter does not apply to this chart.",
        "Watch zero-line crossings, extreme gaps, and whether tone shifts coincide with high-volume "
        "days. The shaded region shows which bloc is more positive at any moment.",
        ui.div(
            ui.div(
                ui.div(
                    "Western weighted tone minus Chinese weighted tone · amber line = ToneGap",
                    class_="chart-kicker",
                ),
                ui.h3("ToneGap over time"),
                class_="chart-card-header",
            ),
            ui.p(
                "Hover for daily Western/Chinese tone breakdown · drag to zoom · double-click to reset",
                class_="chart-tip",
            ),
            ui.p(
                "The media-group filter does not apply to this chart — ToneGap is precomputed from Western and Chinese media together.",
                class_="chart-tip",
            ),
            ui.div(output_widget("tone_gap", height="500px"), class_="chart-stage"),
            class_="chart-card feature-card",
        ),
        ui.layout_columns(
            chart_card(
                "Tone distribution by group",
                "Violin/box: median, spread, and outliers per media group",
                "tone_distribution",
                "440px",
                tip="Hover for group stats · drag to zoom · double-click to reset",
            ),
            chart_card(
                "Tone vs coverage intensity",
                "Each point = one media-group/day · x = article volume · y = avg tone · size = event volume",
                "tone_intensity",
                "460px",
                tip="Hover for date detail · drag to zoom · double-click to reset",
            ),
            col_widths=[5, 7],
        ),
    ),

    # ── Section 4 — Keyword Framing ───────────────────────────────────────────
    story_section(
        "framing",
        "04",
        "Keyword Framing",
        "Which words made each narrative distinctive?",
        "Contrastive TF-IDF scores terms that are overrepresented in one media group compared "
        "with the other.",
        "Larger, darker terms in the cloud are more distinctive to that group. The ranked bar "
        "chart shows exact scores — left = Chinese-distinctive, right = Western-distinctive.",
        # Word cloud as primary visual
        ui.div(
            ui.div(
                ui.div("Phrase word cloud", class_="chart-kicker"),
                ui.h3("Contrastive TF-IDF · phrase-level framing"),
                class_="chart-card-header",
            ),
            ui.div(
                ui.output_image("word_cloud", width="100%", height="auto"),
                class_="word-cloud-wrap",
            ),
            class_="chart-card feature-card",
        ),
        # Ranked bar chart — top-k control lives in the card header
        ui.div(
            ui.div(
                ui.div(
                    ui.div("Ranked bar chart", class_="chart-kicker"),
                    ui.h3("Ranked TF-IDF framing terms"),
                    class_="topk-card-title",
                ),
                ui.div(
                    ui.input_select(
                        "keyword_top_n",
                        "Top-k terms",
                        choices=[10, 12, 15, 20, 30],
                        selected=10,
                    ),
                    class_="topk-control",
                ),
                class_="chart-card-header topk-card-header",
            ),
            ui.div(
                ui.p(
                    "Higher score = more distinctive to that group vs the other side",
                    class_="chart-tip",
                ),
            ),
            ui.p(
                "Hover bars for exact scores and mention counts · drag to zoom · double-click to reset",
                class_="chart-tip",
            ),
            ui.div(output_widget("keyword_framing", height="520px"), class_="chart-stage"),
            class_="chart-card feature-card",
        ),
    ),

    # ── Section 5 — Narrative Gap Forecasting ─────────────────────────────────
    story_section(
        "forecast",
        "05",
        "Narrative Gap Forecasting",
        "Does narrative divergence have short-term predictable structure?",
        "ARIMA, Holt-Winters, Prophet, and TimesFM outputs are evaluated on a 14-day holdout "
        "window. Toggle models directly on the chart to compare.",
        "MAE measures the average forecast error; RMSE penalises larger misses more strongly. "
        "ARIMA achieves the lowest MAE (best average accuracy); TimesFM achieves the lowest RMSE "
        "(best at avoiding large spikes). The Best MAE badge highlights ARIMA. "
        "The thick line is the observed ToneGap — forecasts try to match it.",
        ui.output_ui("forecast_metric_cards"),
        # Forecast chart — model selector lives inside the card
        ui.div(
            ui.div(
                ui.div(
                    "14-day holdout evaluation · thick line = observed · dashed = forecast",
                    class_="chart-kicker",
                ),
                ui.h3("Actual vs predicted ToneGap"),
                class_="chart-card-header",
            ),
            ui.div(
                ui.span("Compare models", class_="model-selector-label"),
                ui.input_checkbox_group(
                    "forecast_models",
                    None,
                    choices=FORECAST_MODELS,
                    selected=FORECAST_MODELS,
                    inline=True,
                ),
                class_="model-selector",
            ),
            ui.p(
                "Checkboxes above add/remove models · click legend items to hide individual lines · hover for values · drag to zoom · double-click to reset",
                class_="chart-tip",
            ),
            ui.div(output_widget("forecast_plot", height="500px"), class_="chart-stage"),
            class_="chart-card feature-card",
        ),
        ui.div(
            insight_card(
                "Interpretation",
                "Forecasting is a predictive layer for narrative divergence, not a precise "
                "political prediction. Use it to understand whether divergence has short-term "
                "structure, not to predict future media behaviour with certainty.",
                "accent-amber",
            ),
            class_="insight-row single",
        ),
    ),

    # ── Floating chatbot overlay (fixed-positioned, always present) ──────────
    chatbot_panel(),

    fillable=False,
)


# ── Server ────────────────────────────────────────────────────────────────────

def server(input, output, session):

    @reactive.Calc
    def selected_dates() -> tuple[pd.Timestamp, pd.Timestamp]:
        start, end = input.date_range()
        return pd.Timestamp(start), pd.Timestamp(end)

    @reactive.Calc
    def selected_media() -> list[str]:
        return list(input.media_groups() or [])

    @reactive.Calc
    def current_theme() -> str:
        return input.theme_mode() or "dark"

    @reactive.Calc
    def filtered_events() -> pd.DataFrame:
        start, end = selected_dates()
        return filter_by_controls(
            DATA.events,
            start,
            end,
            selected_media(),
        )

    @reactive.Calc
    def filtered_daily() -> pd.DataFrame:
        return event_daily(filtered_events())

    @reactive.Calc
    def filtered_tone_gap() -> pd.DataFrame:
        start, end = selected_dates()
        if DATA.tone_gap.empty:
            return DATA.tone_gap
        return DATA.tone_gap[
            (DATA.tone_gap["Date"] >= start) & (DATA.tone_gap["Date"] <= end)
        ].copy()

    @reactive.Calc
    def keyword_terms() -> pd.DataFrame:
        start, end = selected_dates()
        if (
            start == DATE_MIN
            and end == DATE_MAX
            and set(selected_media()) == set(MEDIA_CHOICES)
        ):
            return DEFAULT_KEYWORDS
        return framing_dataframe(filtered_events(), int(input.keyword_top_n()))

    @reactive.Calc
    def cloud_terms() -> pd.DataFrame:
        start, end = selected_dates()
        if (
            start == DATE_MIN
            and end == DATE_MAX
            and set(selected_media()) == set(MEDIA_CHOICES)
        ):
            return DEFAULT_CLOUD_TERMS
        return word_cloud_terms(filtered_events(), 80)

    # Fixed per-process path avoids accumulating temp files on every filter change.
    _wc_path = Path(tempfile.gettempdir()) / f"shiny_wordcloud_{os.getpid()}.png"

    @render.image
    def word_cloud():
        png = word_cloud_chart(cloud_terms(), current_theme())
        if not png:
            return None
        _wc_path.write_bytes(png)
        return {"src": str(_wc_path), "alt": "Contrastive TF-IDF word cloud"}

    @reactive.Calc
    def best_model_name() -> str | None:
        if DATA.forecast_metrics.empty or "mae" not in DATA.forecast_metrics:
            return None
        return str(DATA.forecast_metrics.sort_values("mae").iloc[0]["model"])

    # ── KPI outputs ───────────────────────────────────────────────────────────

    @render.text
    def kpi_events():
        events = filtered_events()
        return f"{len(events):,}"

    @render.text
    def kpi_articles():
        events = filtered_events()
        return f"{int(events['NumArticles'].sum()):,}" if "NumArticles" in events and not events.empty else "0"

    @render.text
    def kpi_sources():
        events = filtered_events()
        if events.empty or "SourceDomain" not in events:
            return "0"
        return f"{events['SourceDomain'].nunique():,}"

    @render.text
    def kpi_western():
        events = filtered_events()
        value = (
            events.loc[events["MediaGroup"] == "Western", "AvgTone"].mean()
            if not events.empty else float("nan")
        )
        return "n/a" if pd.isna(value) else f"{value:.2f}"

    @render.text
    def kpi_chinese():
        events = filtered_events()
        value = (
            events.loc[events["MediaGroup"] == "Chinese", "AvgTone"].mean()
            if not events.empty else float("nan")
        )
        return "n/a" if pd.isna(value) else f"{value:.2f}"

    @render.ui
    def warning_banner():
        if not DATA.warnings:
            return None
        return ui.div(
            ui.strong("Data notice: "), " ".join(DATA.warnings), class_="warning-banner"
        )

    @render.ui
    def forecast_metric_cards():
        cards = forecast_metric_cards_ui(DATA.forecast_metrics)
        return ui.div(*cards, class_="forecast-metric-grid")

    # ── Chart outputs ─────────────────────────────────────────────────────────

    @render_widget
    def daily_volume():
        return daily_volume_chart(filtered_daily(), current_theme())

    @render_widget
    def spread_map():
        if (input.map_style() or "globe") == "flat":
            return narrative_flat_map(filtered_events(), current_theme())
        return narrative_map(filtered_events(), current_theme())

    @render.ui
    def spread_insight():
        style = input.map_style() or "globe"
        if style == "flat":
            label = "What to notice — Flat World Map"
            body = (
                "This full-world frame reveals the story's global reach at a glance. "
                "Western (blue) coverage dominates North America and Western Europe; "
                "Chinese (red) anchors in East Asia and the Pacific Rim. "
                "Secondary clusters across South Asia, Africa, and Latin America show "
                "how the tariff conflict spilled into third-party media ecosystems. "
                "Compare with the Globe view for the US–China bilateral focus."
            )
        else:
            label = "What to notice — Globe"
            body = (
                "The globe view shows the full geographic spread of tariff-war coverage. "
                "Western (blue) coverage concentrates in North America and Western Europe; "
                "Chinese (red) anchors in East Asia and the Pacific Rim. "
                "Look for the density difference between the two blocs — where they overlap, "
                "the same events are being narrated with measurably different tone. "
                "Switch to Flat World Map for a full-world overview."
            )
        return ui.div(
            ui.div(
                ui.div(label, class_="insight-label"),
                ui.p(body, class_="insight-body"),
                class_="map-insight-inner",
            ),
            class_="map-insight-card",
        )

    @render.ui
    def map_tip():
        style = input.map_style() or "globe"
        if style == "flat":
            text = "Hover markers for detail · drag to zoom · double-click to reset"
        else:
            text = "Drag to rotate the globe · scroll to zoom · double-click to reset · hover markers for detail"
        return ui.p(text, class_="chart-tip")

    @render_plotly
    def tone_gap():
        return tone_gap_chart(filtered_tone_gap(), current_theme())

    @render_widget
    def tone_distribution():
        return tone_distribution_chart(filtered_events(), current_theme())

    @render_widget
    def tone_intensity():
        return tone_intensity_chart(filtered_daily(), current_theme())

    @render_widget
    def keyword_framing():
        return keyword_chart(keyword_terms(), int(input.keyword_top_n()), current_theme())

    @render_widget
    def forecast_plot():
        return forecast_chart(
            DATA.forecast_predictions,
            list(input.forecast_models() or []),
            best_model_name(),
            current_theme(),
        )

    # ── Source table ──────────────────────────────────────────────────────────

    @render.ui
    def source_table():
        sources = top_sources(filtered_events(), 9999)
        search = (input.source_search() or "").strip().lower()
        if search:
            sources = sources[
                sources["SourceDomain"].str.lower().str.contains(search, na=False)
            ]
        sort_col = input.source_sort() or "Events"
        ascending = sort_col == "AvgTone"
        if sort_col in sources.columns:
            sources = sources.sort_values(sort_col, ascending=ascending)
        limit = int(input.source_top_n())
        if limit < len(sources):
            sources = sources.head(limit)
        if sources.empty:
            return ui.div("No source found in the current filter.", class_="empty-note")

        rows = [
            ui.div(
                ui.div("Source", class_="source-cell source-head"),
                ui.div("Events", class_="source-cell source-head numeric"),
                ui.div("Articles", class_="source-cell source-head numeric"),
                ui.div("Avg tone", class_="source-cell source-head numeric"),
                class_="source-row source-row-header",
            )
        ]
        for _, row in sources.iterrows():
            rows.append(
                ui.div(
                    ui.div(str(row["SourceDomain"]), class_="source-cell domain"),
                    ui.div(f"{int(row['Events']):,}", class_="source-cell numeric"),
                    ui.div(f"{int(row['Articles']):,}", class_="source-cell numeric"),
                    ui.div(f"{row['AvgTone']:.2f}", class_="source-cell numeric"),
                    class_="source-row",
                )
            )
        return ui.div(*rows, class_="source-table")

    # ── Narrative Assistant chatbot ───────────────────────────────────────────

    chat_history: reactive.Value[list[dict]] = reactive.Value([])
    is_loading:   reactive.Value[bool]       = reactive.Value(False)

    @render.ui
    def chat_messages():
        msgs    = chat_history.get()
        loading = is_loading.get()
        elements: list = []

        if not msgs:
            elements.append(
                ui.p(
                    "Ask a question to get started.",
                    class_="chat-empty-hint",
                )
            )
        else:
            for msg in msgs:
                cls = "chat-msg-user" if msg["role"] == "user" else "chat-msg-assistant"
                elements.append(
                    ui.div(
                        ui.HTML(format_message(msg["content"])),
                        class_=f"chat-msg {cls}",
                    )
                )

        if loading:
            elements.append(
                ui.div(
                    ui.HTML("<em>Thinking…</em>"),
                    class_="chat-msg chat-msg-assistant chat-msg-thinking",
                )
            )

        return ui.div(*elements, class_="chat-messages-inner")

    @reactive.Effect
    @reactive.event(input.chat_send)
    async def _handle_chat():
        question = (input.chat_input() or "").strip()
        if not question:
            return

        msgs = list(chat_history.get())
        msgs.append({"role": "user", "content": question})
        chat_history.set(msgs)

        ui.update_text("chat_input", value="", session=session)

        # Try local answer first (instant, no API call)
        local = get_local_answer(question)
        if local:
            msgs = list(chat_history.get())
            msgs.append({"role": "assistant", "content": local})
            chat_history.set(msgs)
            return


        is_loading.set(True)
        await asyncio.sleep(0)  # yield so the UI renders the loading state

        ctx = build_context(
            events         = filtered_events(),
            tone_gap       = filtered_tone_gap(),
            date_start     = selected_dates()[0],
            date_end       = selected_dates()[1],
            media_groups   = selected_media(),
            forecast_metrics = DATA.forecast_metrics,
        )

        try:
            response = await asyncio.to_thread(
                call_deepseek, SYSTEM_PROMPT, question, ctx
            )
        except Exception as exc:
            response = f"❌ Error: {str(exc)[:120]}"

        msgs = list(chat_history.get())
        msgs.append({"role": "assistant", "content": response})
        chat_history.set(msgs)
        is_loading.set(False)


# ── Forecast metric card builder ───────────────────────────────────────────────

def forecast_metric_cards_ui(metrics: pd.DataFrame):
    rows = forecast_metric_rows(metrics)
    if not rows:
        return [ui.div("Forecast metrics unavailable.", class_="metric-card muted")]
    cards = []
    for row in rows:
        cards.append(
            ui.div(
                ui.div(
                    ui.span(row["model"], class_="metric-model"),
                    ui.span("Best MAE", class_="best-badge") if row["best"] else None,
                    class_="metric-head",
                ),
                ui.div(
                    ui.div(ui.span("MAE"), ui.strong(f"{row['mae']:.3f}")),
                    ui.div(ui.span("RMSE"), ui.strong(f"{row['rmse']:.3f}")),
                    class_="metric-values",
                ),
                class_=f"metric-card {'best' if row['best'] else ''}",
            )
        )
    return cards


app = App(
    app_ui,
    server,
    # static_assets makes files in static/ accessible at the root URL.
    # Combined with method="link_files" in include_css, this ensures:
    #   - CSS url("US-China-trade-war-web2.jpg") resolves correctly
    #   - <img src="US-China-trade-war-web2.jpg"> resolves correctly
    #   - <img src="phrase_word_cloud.png"> resolves correctly
    static_assets=APP_DIR / "static",
)
