"""Reusable Shiny UI fragments."""

from __future__ import annotations

from shiny import ui
from shinywidgets import output_widget


def kpi_card(label: str, value_id: str, note: str, tone: str = ""):
    return ui.div(
        ui.div(label, class_="kpi-label"),
        ui.div(ui.output_text(value_id), class_="kpi-value"),
        ui.div(note, class_="kpi-note"),
        class_=f"kpi-card {tone}",
    )


def chart_card(title: str, kicker: str, output_id: str, height: str = "460px", class_name: str = "", tip: str = ""):
    children = [
        ui.div(
            ui.div(kicker, class_="chart-kicker"),
            ui.h3(title),
            class_="chart-card-header",
        ),
    ]
    if tip:
        children.append(ui.p(tip, class_="chart-tip"))
    children.append(ui.div(output_widget(output_id, height=height), class_="chart-stage"))
    return ui.div(*children, class_=f"chart-card {class_name}".strip())


def table_card(title: str, description: str, output_id: str, class_name: str = ""):
    return ui.div(
        ui.div(
            ui.div("Drilldown", class_="chart-kicker"),
            ui.h3(title),
            ui.p(description, class_="card-copy"),
            class_="chart-card-header",
        ),
        ui.div(ui.output_data_frame(output_id), class_="table-stage"),
        class_=f"chart-card table-card {class_name}".strip(),
    )


def ui_card(title: str, kicker: str, output_id: str, class_name: str = ""):
    return ui.div(
        ui.div(
            ui.div(kicker, class_="chart-kicker"),
            ui.h3(title),
            class_="chart-card-header",
        ),
        ui.div(ui.output_ui(output_id), class_="html-card-stage"),
        class_=f"chart-card {class_name}".strip(),
    )


def insight_card(title: str, body: str, accent: str = ""):
    return ui.div(
        ui.div(title, class_="insight-title"),
        ui.p(body),
        class_=f"insight-card {accent}".strip(),
    )


def story_section(section_id: str, number: str, eyebrow: str, headline: str, explanation: str, insight: str, *children):
    return ui.tags.section(
        ui.div(
            ui.div(f"{number} / {eyebrow}", class_="section-number"),
            ui.h2(headline),
            ui.p(explanation, class_="section-copy"),
            insight_card("What to look for", insight),
            class_="section-intro",
        ),
        ui.div(*children, class_="section-body"),
        id=section_id,
        class_="story-section reveal",
    )
