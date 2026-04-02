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
from textual.containers import ScrollableContainer
from textual.widgets import Static, Footer, Input
from textual.reactive import reactive

from rich.text import Text as RichText
from tower_parser import parse_entry, Message, _escape_rich


# --- Widgets ---

class DiffDetail(Static):
    """Expandable diff/tool detail block."""

    DEFAULT_CSS = "DiffDetail { height: auto; padding: 0 0 0 2; }"


class MessageWidget(Static):
    """A single message rendered as rich markup."""

    DEFAULT_CSS = "MessageWidget { height: auto; }"

    def __init__(self, message: Message, **kwargs):
        self.message = message
        self._diff_details: list[DiffDetail] = []
        super().__init__(**kwargs)
        self.add_class(f"message-{message.type}")

    def compose(self) -> ComposeResult:
        yield from self._diff_details

    def on_mount(self) -> None:
        if self.message.type == "assistant":
            for tc in self.message.tool_calls:
                if tc.full_detail_rich:
                    detail = DiffDetail(
                        RichText.from_markup(tc.full_detail_rich),
                        classes="diff-detail",
                    )
                    detail.display = self.app.show_diffs
                    self.mount(detail)

    def render(self) -> RichText:
        markup = self._render_message(self.message)
        return RichText.from_markup(markup)

    @staticmethod
    def _render_message(msg: Message) -> str:
        # Colors from Claude Code darkTheme RGB values (src/utils/theme.ts)
        parts = []
        if msg.type == "user":
            parts.append("[bold rgb(122,180,232)]## You[/bold rgb(122,180,232)]")
            if msg.text:
                parts.append(f"  {_escape_rich(msg.text)}")

        elif msg.type == "assistant":
            parts.append("[bold rgb(215,119,87)]## Claude[/bold rgb(215,119,87)]")
            if msg.text:
                parts.append(f"  {_escape_rich(msg.text)}")
            for tc in msg.tool_calls:
                parts.append(f"  [rgb(253,93,177)]{_escape_rich(tc.summary)}[/rgb(253,93,177)]")
            # Diff details are rendered as child DiffDetail widgets

        elif msg.type == "tool_result":
            parts.append("[rgb(153,153,153)]## Tools[/rgb(153,153,153)]")
            for tr in msg.tool_results:
                if tr.is_error:
                    label = "[rgb(255,107,128)]ERROR[/rgb(255,107,128)]"
                else:
                    label = "[rgb(78,186,101)]ok[/rgb(78,186,101)]"
                content = _escape_rich(tr.content).replace("\n", "\n  ")
                parts.append(f"  ({label})\n  [rgb(153,153,153)]{content}[/rgb(153,153,153)]")

        return "\n".join(parts)


class SessionHeader(Static):
    """Fixed header bar with session info."""

    message_count = reactive(0)

    def __init__(self, path: str, message_count: int = 0, **kwargs):
        super().__init__(**kwargs)
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
        self._tail_offset = 0  # File offset after initial load

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
                self._tail_offset = f.tell()
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
        # Wait for file to exist
        while not self._closing:
            try:
                f = open(self.transcript_path, encoding="utf-8")
                break
            except FileNotFoundError:
                time.sleep(1)
        else:
            return

        with f:
            f.seek(self._tail_offset)
            partial = ""
            while not self._closing:
                line = f.readline()
                if line:
                    if not line.endswith("\n"):
                        partial += line
                        continue
                    line = (partial + line).strip()
                    partial = ""
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
        for widget in self.query(".message-tool_result"):
            widget.display = self.show_tools

    def action_toggle_diffs(self) -> None:
        self.show_diffs = not self.show_diffs
        for widget in self.query(".diff-detail"):
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
            tool_text = " ".join(
                tc.summary.lower() + " " + tc.full_detail.lower()
                for tc in widget.message.tool_calls
            )
            res_text = " ".join(tr.content.lower() for tr in widget.message.tool_results)
            if query in text or query in tool_text or query in res_text:
                widget.display = True
            else:
                widget.display = False

    def on_unmount(self) -> None:
        self._closing = True
