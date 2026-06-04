"""Floating Narrative Assistant chatbot UI components.

The panel is rendered as a fixed-positioned overlay in the bottom-right corner.
Open/close is handled by plain JS; all data exchange goes through Shiny inputs/outputs.
"""
from __future__ import annotations

from shiny import ui

# (chip label, question text sent on click)
SUGGESTED_CHIPS: list[tuple[str, str]] = [
    ("Summarize current view",    "Please summarize the current filtered view of the dashboard."),
    ("Explain ToneGap",           "Explain ToneGap"),
    ("What does the map show?",   "What does the map show?"),
    ("Western vs Chinese tone",   "Compare Western and Chinese tone in the current filtered view."),
    ("Explain keyword framing",   "Explain keyword framing"),
    ("Best forecast model?",      "Which forecast model performs best and why?"),
    ("What are the limitations?", "What are the main limitations of this dashboard?"),
]

_JS = """
function openChatPanel() {
    document.getElementById('chat-panel').style.display = 'flex';
    document.getElementById('chat-open-btn').style.display = 'none';
    _chatScroll();
}
function closeChatPanel() {
    document.getElementById('chat-panel').style.display = 'none';
    document.getElementById('chat-open-btn').style.display = 'flex';
}
function _chatScroll() {
    var a = document.getElementById('chat-messages-area');
    if (a) setTimeout(function(){ a.scrollTop = a.scrollHeight; }, 80);
}
/* Fill the text input and click Send — works with Shiny's input binding */
function sendChipQuestion(q) {
    var el = document.getElementById('chat_input');
    if (!el) return;
    var setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, q);
    el.dispatchEvent(new Event('input',  {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    setTimeout(function(){
        var btn = document.getElementById('chat_send');
        if (btn) btn.click();
    }, 90);
}
/* Auto-scroll whenever the messages area DOM changes */
document.addEventListener('shiny:connected', function(){
    var a = document.getElementById('chat-messages-area');
    if (!a) return;
    new MutationObserver(_chatScroll).observe(a, {childList: true, subtree: true});
});
"""


def chatbot_panel() -> ui.Tag:
    """Return the complete floating chatbot widget (button + collapsible panel)."""
    chips = [
        ui.tags.button(
            label,
            class_="chat-chip",
            onclick=f"sendChipQuestion({repr(question)})",
        )
        for label, question in SUGGESTED_CHIPS
    ]

    return ui.div(
        # ── Toggle button ──────────────────────────────────────────────────
        ui.tags.button(
            ui.tags.span("💬", class_="chat-btn-icon"),
            ui.tags.span("Narrative Assistant", class_="chat-btn-label"),
            id="chat-open-btn",
            class_="chat-open-btn",
            onclick="openChatPanel()",
        ),

        # ── Chat panel ─────────────────────────────────────────────────────
        ui.div(
            # Header row
            ui.div(
                ui.div(
                    ui.tags.span("🤖", class_="chat-panel-icon"),
                    ui.h4("Narrative Assistant", class_="chat-panel-title"),
                    class_="chat-panel-title-wrap",
                ),
                ui.tags.button("×", class_="chat-close-btn", onclick="closeChatPanel()"),
                class_="chat-panel-header",
            ),

            # Helper text
            ui.p(
                "Ask about the dashboard, dataset, ToneGap, framing terms, or forecast models.",
                class_="chat-helper-text",
            ),

            # Suggested question chips
            ui.div(*chips, class_="chat-chips"),

            # Message history
            ui.div(
                ui.output_ui("chat_messages"),
                id="chat-messages-area",
                class_="chat-messages-area",
            ),

            # Text input + Send button
            ui.div(
                ui.input_text("chat_input", None, placeholder="Ask a question…"),
                ui.input_action_button("chat_send", "Send", class_="chat-send-btn"),
                class_="chat-input-row",
            ),

            id="chat-panel",
            class_="chat-panel",
            style="display: none;",
        ),

        ui.tags.script(_JS),
        class_="chat-float-wrapper",
    )
