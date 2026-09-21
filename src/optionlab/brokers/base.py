from decimal import Decimal
from typing import Protocol

from optionlab.domain import Quote, TradeIntent


class ExecutionBroker(Protocol):
    def fill(self, intent: TradeIntent, quote: Quote) -> Decimal: ...


class LiveExecutionDisabled(RuntimeError):
    pass
