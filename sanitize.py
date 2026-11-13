"""Defense layer 1 (code): turn a vendor document into only the text a person would see.

Runs before any model sees the document. Removes:
  HTML  - <script>/<style>/<head>, comments, hidden elements (display:none, visibility:hidden,
          opacity:0, hidden attribute, aria-hidden), zero or tiny font sizes, white text,
          text pushed off-screen.
  PDF   - white text, tiny text (under 3 pt), text placed outside the page, invisible render mode,
          and text covered by a white box painted on top of it (added after my Problem 7 red team).
  Email - uses the version a mail app shows (the HTML part, cleaned as above; the plain part
          only if there is no HTML part).
  All   - invisible Unicode characters (zero-width spaces and other format characters).

visible_text(path) returns (text, removed) where `removed` lists what was dropped and why.
"""

from __future__ import annotations

import email
import math
import re
import unicodedata
from email import policy
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

MIN_PDF_FONT_PT = 3.0
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
DROP_TAGS = {"script", "style", "head", "template", "noscript", "svg", "object", "iframe"}
BLOCK_TAGS = {"p", "div", "br", "tr", "li", "ul", "ol", "table", "header", "footer", "section", "article",
              "blockquote", "pre", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "address", "main", "nav"}
WHITE_NAMES = {"white", "#fff", "#ffffff", "snow", "ivory", "ghostwhite", "whitesmoke"}


def _short(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "..."


def strip_invisible_chars(text: str, removed: list[dict]) -> str:
    """Remove zero-width and other Unicode 'format' characters (category Cf)."""
    out = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    if len(out) != len(text):
        removed.append({"why": "invisible Unicode characters", "count": len(text) - len(out)})
    return out


# ------------------------------------------------------------------- HTML
def _css(style: str) -> dict[str, str]:
    decls = {}
    for part in style.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            decls[k.strip().lower()] = v.strip().lower()
    return decls


def _is_white(color: str) -> bool:
    color = color.replace(" ", "").replace("!important", "")
    if color in WHITE_NAMES:
        return True
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", color)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return all(int(h[i:i + 2], 16) >= 0xF0 for i in (0, 2, 4))
    m = re.fullmatch(r"rgba?\((\d+),(\d+),(\d+)(?:,([\d.]+))?\)", color)
    if m:
        return all(int(m.group(i)) >= 240 for i in (1, 2, 3)) or (m.group(4) is not None and float(m.group(4)) < 0.1)
    return color == "transparent"


def _font_too_small(size: str) -> bool:
    m = re.fullmatch(r"([\d.]+)\s*(px|pt|em|rem|%)?", size.replace("!important", "").strip())
    if not m:
        return False
    n, unit = float(m.group(1)), m.group(2) or "px"
    return {"px": n < 4, "pt": n < 3, "em": n < 0.3, "rem": n < 0.3, "%": n < 30}[unit]


def _px(value: str) -> float | None:
    m = re.match(r"(-?[\d.]+)\s*(px|pt|em|rem)?", value)
    return float(m.group(1)) if m else None


def _hidden_reason(tag: str, attrs: dict[str, str | None]) -> str | None:
    if tag in DROP_TAGS:
        return f"<{tag}> content"
    if "hidden" in attrs:
        return "hidden attribute"
    if (attrs.get("aria-hidden") or "").lower() == "true":
        return "aria-hidden"
    if tag == "input" and (attrs.get("type") or "").lower() == "hidden":
        return "hidden input"
    css = _css(attrs.get("style") or "")
    if css.get("display", "").startswith("none"):
        return "display:none"
    if css.get("visibility", "").split()[0:1] in (["hidden"], ["collapse"]):
        return "visibility:hidden"
    if "opacity" in css and (_px(css["opacity"]) or 0) < 0.1:
        return "opacity:0"
    if "font-size" in css and _font_too_small(css["font-size"]):
        return f"font-size:{css['font-size']}"
    if "color" in css and _is_white(css["color"]):
        return f"white text (color:{css['color']})"
    if css.get("color") and css.get("color") == css.get("background-color", css.get("background")):
        return "text same color as background"
    for prop in ("text-indent", "left", "top", "margin-left", "margin-top"):
        v = _px(css.get(prop, ""))
        if v is not None and v <= -500:
            return f"pushed off-screen ({prop}:{css[prop]})"
    if (css.get("height", "").startswith("0") or css.get("max-height", "").startswith("0")
            or css.get("width", "").startswith("0")) and css.get("overflow", "") == "hidden":
        return "zero-size box with overflow:hidden"
    if "clip" in css and re.search(r"rect\(0", css["clip"]):
        return "clipped to nothing"
    if re.search(r"scale\(0", css.get("transform", "")):
        return "transform:scale(0)"
    return None


class _VisibleHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []   # (tag, hidden reason)
        self.out: list[str] = []
        self.hidden: dict[str, list[str]] = {}
        self.comments: list[str] = []

    def _hidden(self) -> str | None:
        for _, why in reversed(self.stack):
            if why:
                return why
        return None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): v for k, v in attrs}
        why = _hidden_reason(tag, a)
        if tag in BLOCK_TAGS:
            self.out.append("\n")
        elif tag in ("td", "th"):
            self.out.append("  ")
        if tag not in VOID_TAGS:
            self.stack.append((tag, why))

    def handle_startendtag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.out.append("\n")

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag in BLOCK_TAGS:
            self.out.append("\n")

    def handle_data(self, data):
        why = self._hidden()
        if why:
            if data.strip():
                self.hidden.setdefault(why, []).append(data)
        else:
            self.out.append(data)

    def handle_comment(self, data):
        if data.strip():
            self.comments.append(data)


def visible_html(html: str, removed: list[dict]) -> str:
    p = _VisibleHTML()
    p.feed(html)
    p.close()
    for why, parts in p.hidden.items():
        text = " ".join(" ".join(parts).split())
        if why in ("<style> content", "<head> content"):
            continue          # CSS and the page title: not quote content, not worth reporting
        removed.append({"why": why, "text": _short(text)})
    for c in p.comments:
        removed.append({"why": "HTML comment", "text": _short(c)})
    lines = [" ".join(line.split()) for line in "".join(p.out).splitlines()]
    return "\n".join(line for line in lines if line)


# ------------------------------------------------------------------- PDF
def _mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2, c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)


def _decode(obj) -> str:
    if isinstance(obj, bytes):
        return obj.decode("latin-1")
    return str(obj)


def visible_pdf(path: Path, removed: list[dict]) -> str:
    reader = PdfReader(str(path))
    lines: list[str] = []
    for page in reader.pages:
        box = page.mediabox
        left, bottom, right, top = float(box.left), float(box.bottom), float(box.right), float(box.top)
        contents = page.get_contents()
        if contents is None:
            continue
        gs = {"ctm": (1, 0, 0, 1, 0, 0), "fill": (0.0,), "size": 12.0, "tl": 0.0, "tr": 0}
        stack: list[dict] = []
        tm = tlm = (1, 0, 0, 1, 0, 0)
        items: list[dict] = []          # visible-so-far text pieces, in drawing order
        path_rects: list[tuple] = []    # rectangles in the current path (page coordinates)

        def is_white(fill: tuple) -> bool:
            return all(v <= 0.05 for v in fill) if len(fill) == 4 else all(v >= 0.95 for v in fill)

        def paint_white_box(x0: float, y0: float, x1: float, y1: float) -> None:
            """A white box painted now hides any text drawn earlier underneath it."""
            for it in items:
                if it["covered"]:
                    continue
                width = 0.5 * it["size"] * len(it["text"])          # rough Helvetica width
                if (x0 <= it["x"] + 1 and x1 >= it["x"] + 0.6 * width
                        and y0 <= it["y"] and y1 >= it["y"] + 0.7 * it["size"]):
                    it["covered"] = True

        def show(text: str) -> None:
            if not text.strip():
                return
            m = _mul(tm, gs["ctm"])
            x, y = m[4], m[5]
            size = gs["size"] * math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))
            white = is_white(gs["fill"])
            why = None
            if gs["tr"] in (3, 7):
                why = "invisible text render mode"
            elif white:
                why = "white text on a white page"
            elif size < MIN_PDF_FONT_PT:
                why = f"tiny text ({size:.1f} pt)"
            elif not (left - 1 <= x <= right and bottom - 1 <= y <= top):
                why = f"text placed outside the page (x={x:.0f}, y={y:.0f})"
            if why:
                removed.append({"why": why, "text": _short(text)})
                return
            items.append({"x": x, "y": y, "size": size, "text": text, "covered": False})

        def td(tx: float, ty: float) -> None:
            nonlocal tm, tlm
            tlm = _mul((1, 0, 0, 1, tx, ty), tlm)
            tm = tlm

        for operands, op in contents.operations:
            op = op.decode() if isinstance(op, bytes) else op
            vals = operands
            if op == "q":
                stack.append(dict(gs))
            elif op == "Q" and stack:
                gs = stack.pop()
            elif op == "cm":
                gs["ctm"] = _mul(tuple(float(v) for v in vals), gs["ctm"])
            elif op in ("rg", "g", "k", "sc", "scn") and vals and all(isinstance(v, (int, float)) or hasattr(v, "as_numeric") for v in vals):
                gs["fill"] = tuple(float(v) for v in vals)
            elif op == "re":
                x, y, w, h = (float(v) for v in vals)
                c = gs["ctm"]
                xs = [c[0] * px + c[2] * py + c[4] for px, py in ((x, y), (x + w, y + h))]
                ys = [c[1] * px + c[3] * py + c[5] for px, py in ((x, y), (x + w, y + h))]
                path_rects.append((min(xs), min(ys), max(xs), max(ys)))
            elif op in ("f", "F", "f*", "B", "B*", "b", "b*"):
                if is_white(gs["fill"]):
                    for r in path_rects:
                        paint_white_box(*r)
                path_rects = []
            elif op in ("n", "S", "s"):
                path_rects = []
            elif op == "BT":
                tm = tlm = (1, 0, 0, 1, 0, 0)
            elif op == "Tf":
                gs["size"] = float(vals[1])
            elif op == "TL":
                gs["tl"] = float(vals[0])
            elif op == "Tr":
                gs["tr"] = int(vals[0])
            elif op == "Tm":
                tm = tlm = tuple(float(v) for v in vals)
            elif op == "Td":
                td(float(vals[0]), float(vals[1]))
            elif op == "TD":
                gs["tl"] = -float(vals[1])
                td(float(vals[0]), float(vals[1]))
            elif op == "T*":
                td(0, -gs["tl"])
            elif op == "Tj":
                show(_decode(vals[0]))
            elif op == "TJ":
                show("".join(_decode(v) for v in vals[0] if not isinstance(v, (int, float)) and not hasattr(v, "as_numeric")))
            elif op == "'":
                td(0, -gs["tl"])
                show(_decode(vals[0]))
            elif op == '"':
                td(0, -gs["tl"])
                show(_decode(vals[2]))
        last_y = None
        for it in items:
            if it["covered"]:
                removed.append({"why": "text covered by a white box drawn on top", "text": _short(it["text"])})
                continue
            if last_y is not None and abs(it["y"] - last_y) < 1 and lines:
                lines[-1] += " " + it["text"]
            else:
                lines.append(it["text"])
            last_y = it["y"]
    return "\n".join(lines)


# ------------------------------------------------------------------- email
def visible_eml(path: Path, removed: list[dict]) -> str:
    msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    head = [f"{h}: {msg[h]}" for h in ("From", "To", "Subject", "Date") if msg[h]]
    html_part = msg.get_body(preferencelist=("html",))
    plain_part = msg.get_body(preferencelist=("plain",))
    if html_part is not None:
        body = visible_html(html_part.get_content(), removed)
        if plain_part is not None:
            removed.append({"why": "plain-text copy not shown by mail apps (HTML version used)",
                            "text": _short(plain_part.get_content())})
    elif plain_part is not None:
        body = plain_part.get_content()
    else:
        body = ""
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            removed.append({"why": "attachment not read", "text": part.get_filename() or "unnamed"})
    return "\n".join(head) + "\n\n" + body.strip()


# ------------------------------------------------------------------- entry point
def visible_text(path: Path) -> tuple[str, list[dict]]:
    removed: list[dict] = []
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        text = visible_html(path.read_text(encoding="utf-8", errors="replace"), removed)
    elif suffix == ".pdf":
        text = visible_pdf(path, removed)
    elif suffix == ".eml":
        text = visible_eml(path, removed)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    return strip_invisible_chars(text, removed), removed
