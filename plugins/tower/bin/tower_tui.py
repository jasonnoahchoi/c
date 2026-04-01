"""
Tower TUI - Interactive terminal UI for browsing Claude Code transcripts.

Requires: pip install textual
"""

import json
import time
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static, Collapsible, Footer, Input, Label
from textual.reactive import reactive

from tower_parser import parse_entry, Message, ToolCall, ToolResult


# --- Widgets ---

class ToolCallWidget(Collapsible):
    """A collapsible tool call with summary header and expanded detail."""

    def __init__(self, tool_call: ToolCall):
        super().__init__(title=tool_call.summary, collapsed=True)
        self.tool_call = tool_call

    def compose(self) -> ComposeResult:
        yield Static(self.tool_call.full_detail_rich, markup=True, classes="tool-detail")


class ToolResultWidget(Static):
    """Dim display of tool results."""

    def __init__(self, results: list[ToolResult]):
        parts = []
        for tr in results:
            label = "[yellow]ERROR[/yellow]" if tr.is_error else "[dim]ok[/dim]"
            parts.append(f"  ({label}) {tr.content[:100]}")
        super().__init__("\n".join(parts), markup=True)
        self.add_class("tool-result")


class MessageWidget(Vertical):
    """A single message (user, assistant, or tool_result)."""

    def __init__(self, message: Message):
        super().__init__()
        self.message = message
        self.add_class(f"message-{message.type}")

    def compose(self) -> ComposeResult:
        if self.message.type == "user":
            yield Label("## User", classes="header-user")
            yield Static(self.message.text, classes="content-user")

        elif self.message.type == "assistant":
            yield Label("## Assistant", classes="header-assistant")
            if self.message.text:
                yield Static(self.message.text, classes="content-assistant")
            for tc in self.message.tool_calls:
                yield ToolCallWidget(tc)

        elif self.message.type == "tool_result":
            yield Label("## Tools", classes="header-tools")
            yield ToolResultWidget(self.message.tool_results)


class SessionHeader(Static):
    """Fixed header bar with session info."""

    message_count = reactive(0)

    def __init__(self, path: str, message_count: int = 0):
        super().__init__()
        self.path = path
        self.session_id = Path(path).stem[:12]
        self.message_count = message_count

    def render(self) -> str:
        return f" Tower | {self.session_id}... | {self.message_count} messages | {self.path}"


# --- App ---

class TowerApp(App):
    """Interactive TUI for browsing Claude Code transcripts."""

    CSS_PATH = "tower_tui.css"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("t", "toggle_tools", "Toggle tools"),
        Binding("d", "toggle_diffs", "Toggle diffs"),
        Binding("slash", "search", "Search"),
        Binding("j", "scroll_down", "Down"),
        Binding("k", "scroll_up", "Up"),
        Binding("g", "scroll_top", "Top"),
        Binding("G", "scroll_bottom", "Bottom"),
        Binding("escape", "clear_search", "Clear search"),
    ]

    show_tools = reactive(True)
    show_diffs = reactive(True)
    _at_bottom = True

    def __init__(self, transcript_path: str):
        super().__init__()
        self.transcript_path = transcript_path
        self._message_count = 0
        self._closing = False

    def compose(self) -> ComposeResult:
        yield SessionHeader(self.transcript_path, id="header")
        yield ScrollableContainer(id="message-list")
        yield Input(placeholder="Search...", id="search-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).display = False
        self.load_existing_messages()
        self.tail_file()

    def load_existing_messages(self) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        try:
            with open(self.transcript_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        msg = parse_entry(entry)
                        if msg:
                            container.mount(MessageWidget(msg))
                            self._message_count += 1
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            container.mount(Static("Waiting for transcript..."))

        header = self.query_one("#header", SessionHeader)
        header.message_count = self._message_count
        self.call_after_refresh(self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        container.scroll_end(animate=False)
        self._at_bottom = True

    def add_message(self, msg: Message) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        container.mount(MessageWidget(msg))
        self._message_count += 1
        header = self.query_one("#header", SessionHeader)
        header.message_count = self._message_count
        if self._at_bottom:
            self.call_after_refresh(self._scroll_to_bottom)

    @work(thread=True)
    def tail_file(self) -> None:
        with open(self.transcript_path, encoding="utf-8") as f:
            f.seek(0, 2)
            while not self._closing:
                line = f.readline()
                if line:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            msg = parse_entry(entry)
                            if msg:
                                self.call_from_thread(self.add_message, msg)
                        except json.JSONDecodeError:
                            pass
                else:
                    time.sleep(0.3)

    def on_scrollable_container_scroll(self) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        self._at_bottom = container.scroll_offset.y >= (
            container.virtual_size.height - container.size.height - 5
        )

    # --- Actions ---

    def action_scroll_down(self) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        container.scroll_relative(y=3)

    def action_scroll_up(self) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        container.scroll_relative(y=-3)

    def action_scroll_top(self) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        container.scroll_home(animate=False)

    def action_scroll_bottom(self) -> None:
        self._scroll_to_bottom()

    def action_toggle_tools(self) -> None:
        self.show_tools = not self.show_tools
        for widget in self.query(ToolCallWidget):
            widget.display = self.show_tools
        for widget in self.query(ToolResultWidget):
            widget.display = self.show_tools

    def action_toggle_diffs(self) -> None:
        self.show_diffs = not self.show_diffs
        for widget in self.query(".tool-detail"):
            widget.display = self.show_diffs

    def action_search(self) -> None:
        search = self.query_one("#search-input", Input)
        search.display = True
        search.focus()

    def action_clear_search(self) -> None:
        search = self.query_one("#search-input", Input)
        search.value = ""
        search.display = False
        # Show all messages
        for widget in self.query(MessageWidget):
            widget.display = True
        self.query_one("#message-list", ScrollableContainer).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.lower()
        if not query:
            self.action_clear_search()
            return
        for widget in self.query(MessageWidget):
            text = widget.message.text.lower()
            tool_text = " ".join(tc.summary.lower() for tc in widget.message.tool_calls)
            if query in text or query in tool_text:
                widget.display = True
            else:
                widget.display = False

    def on_unmount(self) -> None:
        self._closing = True
