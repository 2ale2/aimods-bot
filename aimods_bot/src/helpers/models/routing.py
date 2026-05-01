from __future__ import annotations
from enum import Enum
from typing import Self

Segment = str | Enum


class PathBuilder:
    def __init__(self, *segments: Segment) -> None:
        self.segments = [str(s) for s in segments]

    @classmethod
    def from_string(cls, string: str) -> Self:
        return cls(*string.split("/"))

    def add(self, *new_segments: Segment) -> Self:
        self.segments.extend(str(s) for s in new_segments)
        return self

    def back(self, steps: int = 1) -> Self:
        if len(self.segments) > steps:
            self.segments = self.segments[:-steps]
        return self

    def pop(self, idx: int) -> Self:
        if self.segments:
            self.segments.pop(idx)
        return self

    def change(self, old_segment: str, new_segment: str) -> Self:
        self.segments = [
            new_segment if s == old_segment else s for s in self.segments
        ]
        return self

    def build(self) -> str:
        return "/".join(self.segments)

    def __str__(self) -> str:
        return self.build()

    def __len__(self) -> int:
        return len(self.segments)

    def __add__(self, other: PathBuilder) -> PathBuilder:
        return PathBuilder(*(self.segments + other.segments))
