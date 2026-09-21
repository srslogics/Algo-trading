from decimal import Decimal

from optionlab.domain import Quote, TradeIntent


class PaperBroker:
    """All-or-none immediate fill, one tick adverse slippage; no queue model."""

    def fill(self, intent: TradeIntent, quote: Quote) -> Decimal:
        price = quote.ask + quote.instrument.tick_size
        if (
            intent.side != "BUY"
            or price > intent.limit_price
            or quote.ask_quantity < intent.quantity
        ):
            raise ValueError("Paper fill unavailable within limit or displayed depth")
        return price

    def exit_price(self, quote: Quote, quantity: int) -> Decimal:
        if quote.bid_quantity < quantity:
            raise ValueError("Insufficient displayed bid depth for paper exit")
        return max(quote.instrument.tick_size, quote.bid - quote.instrument.tick_size)
