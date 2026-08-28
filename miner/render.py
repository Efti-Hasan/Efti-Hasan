"""Render the calendar and the miner's route into one self-contained SVG.

Everything animates through CSS keyframes rather than SMIL or script, because
that is the only form of animation GitHub reliably renders in a README.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from .contributions import Calendar
from .route import Route

CELL = 12
GAP = 3
PITCH = CELL + GAP
ROWS = 7
RADIUS = 2.5

PAD_X = 10
PAD_TOP = 10
FOOTER = 28

STEP_SECONDS = 0.085  # time the miner spends on one square
POP_SECONDS = 0.42  # how long a square takes to break apart
TAIL_SECONDS = 2.4  # beat at the end before the loop restarts


@dataclass(frozen=True)
class Palette:
    name: str
    tunnel: str
    rock: str
    ore: tuple[str, str, str, str]
    spark: str
    text: str
    helmet: str
    skin: str
    suit: str
    handle: str
    blade: str


DARK = Palette(
    name="dark",
    tunnel="#080a0d",
    rock="#272d35",
    ore=("#0e4429", "#006d32", "#26a641", "#39d353"),
    spark="#ffd873",
    text="#7d8590",
    helmet="#f5b800",
    skin="#e8b28a",
    suit="#3d6fd6",
    handle="#8b5e34",
    blade="#c9d1d9",
)

LIGHT = Palette(
    name="light",
    tunnel="#b6bfc9",
    rock="#ebedf0",
    ore=("#9be9a8", "#40c463", "#30a14e", "#216e39"),
    spark="#d97706",
    text="#59636e",
    helmet="#e3a008",
    skin="#d69a6f",
    suit="#2f5bb7",
    handle="#7a5028",
    blade="#57606a",
)

PALETTES = {"dark": DARK, "light": LIGHT}


def _num(value: float) -> str:
    """Trim floats so the generated file stays small and diffs stay stable."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _cell_x(week: int) -> float:
    return week * PITCH


def _cell_y(row: int) -> float:
    return row * PITCH


@dataclass(frozen=True)
class Timing:
    steps: int

    @property
    def travel(self) -> float:
        return max(self.steps - 1, 1) * STEP_SECONDS

    @property
    def total(self) -> float:
        return self.travel + TAIL_SECONDS

    def at(self, index: int) -> float:
        """Wall-clock second at which the miner reaches route position `index`."""
        return index * STEP_SECONDS

    def pct(self, seconds: float) -> float:
        return 100.0 * seconds / self.total


def _rule(selector: str, *declarations: str) -> str:
    return selector + "{" + ";".join(declarations) + "}"


def _keyframes(name: str, stops: list[tuple[str, str]]) -> str:
    body = "".join(f"{offset}{{{decl}}}" for offset, decl in stops)
    return f"@keyframes {name}{{{body}}}"


def _travel_keyframes(route: Route, timing: Timing) -> str:
    stops: list[tuple[str, str]] = []
    declaration = "transform:translate(0px,0px)"
    for index, (week, row) in enumerate(route.cells):
        x = _cell_x(week) + CELL / 2
        y = _cell_y(row) + CELL / 2
        declaration = f"transform:translate({_num(x)}px,{_num(y)}px)"
        stops.append((f"{_num(timing.pct(timing.at(index)))}%", declaration))
    stops.append(("100%", declaration))
    return _keyframes("travel", stops)


def _css(palette: Palette, timing: Timing, travel: str) -> str:
    pop = timing.pct(POP_SECONDS)
    mid, end, flash = _num(pop * 0.35), _num(pop), _num(pop * 1.35)
    total = _num(timing.total)

    rules = [
        _rule(".q", f"fill:{palette.tunnel}"),
        _rule(".w", f"fill:{palette.rock}"),
    ]
    for level, colour in enumerate(palette.ore, start=1):
        rules.append(_rule(f".l{level}", f"fill:{colour}"))

    rules += [
        _rule(".w,.k,.s", "transform-box:fill-box", "transform-origin:center"),
        _rule(
            ".b",
            f"animation-duration:{total}s",
            "animation-timing-function:linear",
            "animation-iteration-count:infinite",
            "animation-fill-mode:backwards",
        ),
        _rule(".w.b", "animation-name:dig"),
        _rule(".k.b", "animation-name:crack"),
        _rule(
            ".s",
            "fill:none",
            f"stroke:{palette.spark}",
            "stroke-width:1.2",
            "opacity:0",
            f"animation:spark {total}s linear infinite",
        ),
        _rule(".m", f"animation:travel {total}s linear infinite"),
        _rule(".bob", "animation:bob .46s ease-in-out infinite"),
        _rule(".pk", "animation:pick .46s steps(1,end) infinite"),
        _rule(".pk2", "animation-delay:.23s"),
        _rule(".hl", f"fill:{palette.helmet}"),
        _rule(".sk", f"fill:{palette.skin}"),
        _rule(".su", f"fill:{palette.suit}"),
        _rule(".hd", f"fill:{palette.handle}"),
        _rule(".bl", f"fill:{palette.blade}"),
        _rule(".lp", f"fill:{palette.spark}"),
        _rule(
            ".f",
            f"fill:{palette.text}",
            'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif',
            "font-size:9px",
            "font-weight:600",
        ),
    ]

    frames = [
        _keyframes(
            "dig",
            [
                ("0%", "opacity:1;transform:scale(1)"),
                (f"{mid}%", "opacity:.8;transform:scale(.88)"),
                (f"{end}%", "opacity:0;transform:scale(.5)"),
                ("100%", "opacity:0;transform:scale(.5)"),
            ],
        ),
        _keyframes(
            "crack",
            [
                ("0%", "opacity:1;transform:scale(1)"),
                (f"{mid}%", "opacity:1;transform:scale(1.42)"),
                (f"{end}%", "opacity:0;transform:scale(.2)"),
                ("100%", "opacity:0;transform:scale(.2)"),
            ],
        ),
        _keyframes(
            "spark",
            [
                ("0%", "opacity:0;transform:scale(.2)"),
                (f"{mid}%", "opacity:.95;transform:scale(.65)"),
                (f"{flash}%", "opacity:0;transform:scale(1.6)"),
                ("100%", "opacity:0;transform:scale(1.6)"),
            ],
        ),
        _keyframes(
            "bob",
            [("0%,100%", "transform:translateY(0)"), ("50%", "transform:translateY(-1.2px)")],
        ),
        _keyframes("pick", [("0%,49%", "opacity:1"), ("50%,100%", "opacity:0")]),
        travel,
    ]

    return "".join(rules) + "".join(frames)


def _sprite() -> str:
    """The miner, drawn around (0,0) so it can be dropped on any cell centre."""
    raised = (
        '<g class="pk">'
        '<path class="hd" d="M2.8 -3L10.6 -10.8L11.8 -9.6L4 -1.8Z"/>'
        '<path class="bl" d="M14.9 -7.9L13 -12L8.9 -13.9L10.8 -9.8Z"/>'
        "</g>"
    )
    struck = (
        '<g class="pk pk2">'
        '<path class="hd" d="M3.9 -3L11.7 2.8L10.7 4L2.9 -1.8Z"/>'
        '<path class="bl" d="M14.5 .8L13.2 5.1L9.5 7.6L10.8 3.3Z"/>'
        "</g>"
    )
    body = (
        '<rect class="su" x="-3.2" y="3.2" width="2.6" height="2.6" rx=".9"/>'
        '<rect class="su" x=".6" y="3.2" width="2.6" height="2.6" rx=".9"/>'
        '<rect class="su" x="-4" y="-2" width="8" height="6" rx="1.7"/>'
        '<rect class="sk" x="-2.9" y="-5.2" width="5.8" height="3.4" rx="1.3"/>'
        '<ellipse class="hl" cx="0" cy="-7.6" rx="3.7" ry="3.2"/>'
        '<rect class="hl" x="-4.8" y="-6.6" width="9.6" height="1.5" rx=".75"/>'
        '<circle class="lp" cx="0" cy="-7.8" r="1.1"/>'
    )
    return f'<g class="bob">{body}{raised}{struck}</g>'


def _grid(calendar: Calendar, route: Route, timing: Timing) -> str:
    tunnels: list[str] = []
    blocks: list[str] = []
    sparks: list[str] = []
    box = f'width="{CELL}" height="{CELL}" rx="{RADIUS}"'

    for week, column in enumerate(calendar.weeks):
        for row, day in enumerate(column):
            if day is None:
                continue
            x, y = _num(_cell_x(week)), _num(_cell_y(row))
            kind = f"k l{day.level}" if day.level else "w"
            visit = route.first_visit.get((week, row))

            if visit is None:  # rock the miner never reaches
                blocks.append(f'<rect class="{kind}" x="{x}" y="{y}" {box}/>')
                continue

            delay = _num(timing.at(visit))
            tunnels.append(f'<rect class="q" x="{x}" y="{y}" {box}/>')
            blocks.append(
                f'<rect class="{kind} b" x="{x}" y="{y}" {box} style="animation-delay:{delay}s"/>'
            )
            if day.level:
                cx = _num(_cell_x(week) + CELL / 2)
                cy = _num(_cell_y(row) + CELL / 2)
                sparks.append(
                    f'<circle class="s" cx="{cx}" cy="{cy}" r="5" style="animation-delay:{delay}s"/>'
                )

    return "".join(tunnels) + "".join(blocks) + "".join(sparks)


def render(calendar: Calendar, route: Route, palette: Palette, *, login: str) -> str:
    """Return a complete, standalone animated SVG document."""
    if not route.cells:
        raise ValueError("the route is empty - nothing to animate")

    weeks = len(calendar.weeks)
    timing = Timing(steps=len(route))
    width = PAD_X * 2 + weeks * PITCH - GAP
    height = PAD_TOP + ROWS * PITCH - GAP + FOOTER
    baseline = height - 9

    days = [day for column in calendar.weeks for day in column if day]
    span = f"{days[0].day:%b %Y} - {days[-1].day:%b %Y}" if days else ""
    tally = f"{calendar.total:,} contributions mined"
    label = f"{calendar.total:,} GitHub contributions by {login}, {span}, drawn as a mine"

    css = _css(palette, timing, _travel_keyframes(route, timing))
    grid = _grid(calendar, route, timing)
    offset = f"translate({PAD_X},{PAD_TOP})"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_num(width)}" '
        f'height="{_num(height)}" viewBox="0 0 {_num(width)} {_num(height)}" '
        f'role="img" aria-label="{escape(label)}">'
        f"<title>{escape(label)}</title>"
        f"<style>{css}</style>"
        f'<g transform="{offset}">{grid}</g>'
        f'<g transform="{offset}"><g class="m">{_sprite()}</g></g>'
        f'<text class="f" x="{PAD_X}" y="{_num(baseline)}">{escape(tally)}</text>'
        f'<text class="f" x="{_num(width - PAD_X)}" y="{_num(baseline)}" '
        f'text-anchor="end">{escape(span)}</text>'
        "</svg>"
    )



