from __future__ import annotations
from enum import Enum


class PathBuilder:
    def __init__(self, *segments: str | Enum):
        self.segments = [str(s) for s in segments]

    @classmethod
    def from_string(cls, string: str) -> PathBuilder:
        return cls(*string.split("/"))

    def add(self, *new_segments: str | Enum) -> PathBuilder:
        return PathBuilder(*(self.segments + list(new_segments)))

    def back(self, steps: int = 1) -> PathBuilder:
        if len(self.segments) > steps:
            return PathBuilder(*self.segments[:-steps])
        return self

    def pop(self, idx: int) -> PathBuilder:
        if len(self.segments) > 0:
            return PathBuilder(self.segments.pop(idx))
        return self

    def change(self, old_segment: str, new_segment: str) -> PathBuilder:
        return PathBuilder([new_segment if segment == old_segment else old_segment for segment in self.segments])

    def build(self) -> str:
        return "/".join(self.segments)

    def __str__(self) -> str:
        return self.build()

    def __len__(self) -> int:
        return len(self.segments)
