from __future__ import annotations
from enum import StrEnum

Segment = str | StrEnum


class PathBuilder:
    __slots__ = ("segments",)

    def __init__(self, *segments: Segment) -> None:
        self.segments: tuple[str, ...] = tuple(str(s) for s in segments)

    @classmethod
    def from_string(cls, s: str) -> PathBuilder:
        if not s:
            return cls()
        return cls(*s.split("/"))

    def add(self, *new_segments: Segment) -> PathBuilder:
        return PathBuilder(*self.segments, *new_segments)

    def back(self, steps: int = 1) -> PathBuilder:
        if steps <= 0 or len(self.segments) < steps:
            return PathBuilder(*self.segments)
        return PathBuilder(*self.segments[:-steps])

    def pop(self, segment: int | str) -> PathBuilder:
        if not self.segments:
            return self.back()
        if isinstance(segment, int):
            remaining = list(self.segments)
            del remaining[segment]
        else:
            remaining = [s for s in self.segments if s != segment]
        return PathBuilder(*remaining)

    def change(self, old_segment: str, new_segment: str) -> PathBuilder:
        return PathBuilder(
            *(new_segment if s == old_segment else s for s in self.segments)
        )

    def build(self) -> str:
        return "/".join(self.segments)

    def __add__(self, other: PathBuilder) -> PathBuilder:
        return PathBuilder(*(self.segments + other.segments))

    def __str__(self) -> str:
        return self.build()

    def __len__(self) -> int:
        return len(self.segments)
