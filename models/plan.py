from dataclasses import dataclass
from typing import Optional


@dataclass
class Plan:

    event: Optional[str] = None
    style: Optional[str] = None
    budget: Optional[int] = None
    color: Optional[str] = None
    clothing_type: Optional[str] = None
    season: Optional[str] = None
    raw_input: Optional[str] = None
