from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PaymentAmount:
    cents: int
    currency: Literal["usd"] = "usd"
