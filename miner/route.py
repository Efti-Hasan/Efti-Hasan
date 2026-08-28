"""Plan the miner's tunnel through the calendar.

The miner works chronologically, left to right, one week at a time. Inside a
week it detours up or down to every square that has contributions, carving a
tunnel through the rock it passes on the way. Weeks with no contributions are
crossed in a straight line.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contributions import Calendar

Cell = tuple[int, int]  # (week index, row index)

MIDDLE_ROW = 3


@dataclass
class Route:
    cells: list[Cell] = field(default_factory=list)
    first_visit: dict[Cell, int] = field(default_factory=dict)

    def step(self, cell: Cell) -> None:
        if self.cells and self.cells[-1] == cell:
            return
        self.first_visit.setdefault(cell, len(self.cells))
        self.cells.append(cell)

    def __len__(self) -> int:
        return len(self.cells)


def _ore_rows(week: list) -> list[int]:
    return [row for row, day in enumerate(week) if day and day.level > 0]


def build(calendar: Calendar) -> Route:
    """Walk every ore square in the calendar and return the path taken."""
    route = Route()
    row = MIDDLE_ROW

    for index, week in enumerate(calendar.weeks):
        targets = _ore_rows(week)

        if not route.cells:
            row = targets[0] if targets else MIDDLE_ROW
        route.step((index, row))

        if not targets:
            continue

        # Sweep in whichever direction starts closest to where the miner stands.
        if abs(targets[0] - row) > abs(targets[-1] - row):
            targets = list(reversed(targets))

        for target in targets:
            direction = 1 if target > row else -1
            while row != target:
                row += direction
                route.step((index, row))

    return route
