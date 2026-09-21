# Internal Marketplace Design - Compute Capital Trading

**Document Version:** 1.0
**Date:** October 14, 2025
**Status:** Research Complete - Ready for Implementation

---

## Executive Summary

The **Internal CC Marketplace** enables peer-to-peer trading of Compute Capital (CC) between users without platform intermediation. This creates **liquidity**, **price discovery**, and **maximum capital efficiency** while maintaining regulatory compliance by keeping trades internal-only (Phase 1-2).

**Vision:** Make CC as tradable as Bitcoin, but without the regulatory complexity of external exchanges.

**Key Features:**
- **Order Book Trading** - Users set buy/sell prices
- **Automated Market Maker (AMM)** - Instant swaps via liquidity pools
- **P2P Escrow** - Direct user-to-user trades with platform guarantee
- **Bulk Pricing** - Discounts for large CC purchases
- **Reputation System** - Build trust scores through successful trades

---

## Table of Contents

1. [Trading Mechanisms](#trading-mechanisms)
2. [Order Book vs AMM Design](#order-book-vs-amm-design)
3. [Escrow and Settlement](#escrow-and-settlement)
4. [Liquidity Incentives](#liquidity-incentives)
5. [Price Discovery Mechanisms](#price-discovery-mechanisms)
6. [Anti-Manipulation Safeguards](#anti-manipulation-safeguards)
7. [Implementation Roadmap](#implementation-roadmap)

---

## Trading Mechanisms

### Why Enable P2P Trading?

**Problem Scenarios:**
```
Scenario 1: Emergency Cash Need
- User A has 1,000 CC earned from providing compute
- Needs cash urgently for unexpected expense
- Platform withdrawal has 5% fee + 3-day delay
- Solution: Sell CC to User B at 3% discount for instant USD payment

Scenario 2: Bulk Discount Arbitrage
- User C needs 10,000 CC for massive ML training job
- Buying from platform: 10,000 CC × $0.10 = $1,000
- Buying from users with surplus: 10,000 CC × $0.095 = $950 (5% savings)

Scenario 3: Time Preference Trading
- User D earned 500 CC but won't need compute for 3 months
- User E needs compute NOW but doesn't have CC yet
- D sells 500 CC to E at slight premium ($0.11 vs $0.10)
- Both benefit from timing arbitrage
```

### Trading Models Comparison

| Model | Liquidity | Price Discovery | Simplicity | Recommended Phase |
|-------|-----------|----------------|------------|-------------------|
| **Order Book** | Low (needs volume) | Excellent | Medium | Phase 2-3 |
| **AMM** | Always available | Good | High | Phase 1-2 (MVP) |
| **P2P Escrow** | Depends on matching | Fair | High | Phase 1 (manual) |
| **Hybrid** | Best of all | Excellent | Medium | Phase 3+ |

**Recommendation:** Start with AMM + P2P escrow, add order book in Phase 2.

---

## Order Book vs AMM Design

### Option 1: Order Book (Centralized Matching)

**How it works:**
```
Users post limit orders (buy at X price or sell at Y price)
Platform matches orders when prices overlap

BUY ORDERS (Bids):
User A: Buy 1,000 CC @ $0.095 each
User B: Buy 500 CC @ $0.090 each
User C: Buy 2,000 CC @ $0.088 each

SELL ORDERS (Asks):
User D: Sell 800 CC @ $0.102 each
User E: Sell 1,200 CC @ $0.105 each
User F: Sell 500 CC @ $0.110 each

MATCH:
User A's bid ($0.095) < User D's ask ($0.102) → NO MATCH
Spread = $0.102 - $0.095 = $0.007 (0.7¢)

If User D lowers ask to $0.095:
→ MATCH: 800 CC trade @ $0.095
→ User A gets 800 CC, needs 200 more
→ User D gets $76 ($0.095 × 800)
```

**Code Implementation:**

```python
class OrderBook:
    def __init__(self):
        self.bids = []  # Buy orders (sorted descending by price)
        self.asks = []  # Sell orders (sorted ascending by price)
        self.trades = []

    def add_order(self, user_id, side, quantity, price, order_type="limit"):
        """
        Add a new order to the book.

        Args:
            side: 'buy' or 'sell'
            quantity: Amount of CC
            price: USD per CC
            order_type: 'limit' or 'market'
        """
        order = {
            "id": generate_uuid(),
            "user_id": user_id,
            "side": side,
            "quantity": quantity,
            "price": price if order_type == "limit" else None,
            "filled": 0,
            "status": "open",
            "timestamp": time.time()
        }

        if side == "buy":
            # Escrow buyer's USD
            escrow_usd(user_id, quantity * price)
            self.bids.append(order)
            self.bids.sort(key=lambda x: x["price"], reverse=True)
        else:  # sell
            # Escrow seller's CC
            escrow_cc(user_id, quantity)
            self.asks.append(order)
            self.asks.sort(key=lambda x: x["price"])

        # Try to match immediately
        self.match_orders()

        return order["id"]

    def match_orders(self):
        """
        Match buy and sell orders when prices overlap.
        """
        while self.bids and self.asks:
            top_bid = self.bids[0]
            top_ask = self.asks[0]

            # Check if prices overlap
            if top_bid["price"] >= top_ask["price"]:
                # Calculate trade quantity (min of both orders)
                trade_quantity = min(
                    top_bid["quantity"] - top_bid["filled"],
                    top_ask["quantity"] - top_ask["filled"]
                )

                # Trade price = ask price (taker pays ask)
                trade_price = top_ask["price"]

                # Execute trade
                self.execute_trade(
                    buyer_id=top_bid["user_id"],
                    seller_id=top_ask["user_id"],
                    quantity=trade_quantity,
                    price=trade_price
                )

                # Update filled amounts
                top_bid["filled"] += trade_quantity
                top_ask["filled"] += trade_quantity

                # Remove fully filled orders
                if top_bid["filled"] >= top_bid["quantity"]:
                    top_bid["status"] = "filled"
                    self.bids.pop(0)

                if top_ask["filled"] >= top_ask["quantity"]:
                    top_ask["status"] = "filled"
                    self.asks.pop(0)
            else:
                # No more matches possible
                break

    def execute_trade(self, buyer_id, seller_id, quantity, price):
        """
        Settle a matched trade.
        """
        total_usd = quantity * price
        platform_fee = total_usd * 0.02  # 2% fee

        # Transfer CC: seller → buyer
        transfer_cc(from_user=seller_id, to_user=buyer_id, amount=quantity)

        # Transfer USD: buyer → seller (minus fee)
        transfer_usd(from_user=buyer_id, to_user=seller_id, amount=total_usd - platform_fee)

        # Platform collects fee
        collect_fee(platform_fee)

        # Record trade
        trade = {
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "quantity": quantity,
            "price": price,
            "total_usd": total_usd,
            "fee": platform_fee,
            "timestamp": time.time()
        }
        self.trades.append(trade)

        # Emit event
        emit_trade_event(trade)

    def get_market_depth(self, levels=10):
        """
        Return current order book depth.
        """
        return {
            "bids": self.bids[:levels],
            "asks": self.asks[:levels],
            "spread": self.asks[0]["price"] - self.bids[0]["price"] if self.bids and self.asks else None
        }
```

**Benefits:**
- Transparent price discovery
- User-controlled pricing
- Familiar to traders (like stock exchanges)
- Best execution for large orders

**Drawbacks:**
- Requires high liquidity (thin markets = wide spreads)
- Complexity for casual users
- May have no matches during low activity

---

### Option 2: Automated Market Maker (AMM)

**How it works (Uniswap-style constant product formula):**
```
Platform maintains a liquidity pool:
- 100,000 CC
- $10,000 USD
- Constant product K = CC × USD = 1,000,000,000

Price = USD / CC = $10,000 / 100,000 = $0.10 per CC

User wants to buy 1,000 CC:
- Deposits USD into pool
- Removes CC from pool
- K must stay constant

Formula:
(CC - cc_out) × (USD + usd_in) = K
(100,000 - 1,000) × ($10,000 + usd_in) = 1,000,000,000
99,000 × ($10,000 + usd_in) = 1,000,000,000
$10,000 + usd_in = 10,101.01
usd_in = $101.01

Effective price = $101.01 / 1,000 = $0.10101 per CC
Slippage = 1.01% (higher than order book for large trades)

New pool state:
- 99,000 CC
- $10,101.01 USD
- K = 1,000,000,000 (constant preserved)
```

**Code Implementation:**

```python
class AMM:
    def __init__(self, initial_cc, initial_usd):
        self.cc_reserve = initial_cc
        self.usd_reserve = initial_usd
        self.k = initial_cc * initial_usd  # Constant product
        self.fee_rate = 0.003  # 0.3% fee (standard for AMMs)

    def get_price(self):
        """Current price (USD per CC)"""
        return self.usd_reserve / self.cc_reserve

    def quote_buy(self, cc_amount):
        """
        Calculate how much USD needed to buy cc_amount.

        Returns:
            {
                "usd_required": float,
                "effective_price": float,
                "slippage": float,
                "fee": float
            }
        """
        # Apply fee first
        cc_amount_after_fee = cc_amount / (1 - self.fee_rate)

        # Calculate USD needed using constant product formula
        # (cc_reserve - cc_amount) × (usd_reserve + usd_required) = k
        new_cc_reserve = self.cc_reserve - cc_amount
        new_usd_reserve = self.k / new_cc_reserve
        usd_required = new_usd_reserve - self.usd_reserve

        # Calculate metrics
        effective_price = usd_required / cc_amount
        current_price = self.get_price()
        slippage = (effective_price - current_price) / current_price

        return {
            "usd_required": usd_required,
            "effective_price": effective_price,
            "slippage": slippage,
            "fee": usd_required * self.fee_rate
        }

    def execute_buy(self, user_id, cc_amount):
        """
        Execute a buy (user trades USD for CC).
        """
        quote = self.quote_buy(cc_amount)

        # Verify user has enough USD
        if get_user_usd_balance(user_id) < quote["usd_required"]:
            raise InsufficientFundsError()

        # Deduct USD from user
        deduct_usd(user_id, quote["usd_required"])

        # Add USD to pool (minus fee)
        self.usd_reserve += quote["usd_required"] * (1 - self.fee_rate)

        # Remove CC from pool
        self.cc_reserve -= cc_amount

        # Give CC to user
        add_cc(user_id, cc_amount)

        # Collect platform fee
        collect_fee(quote["fee"])

        # Record trade
        record_trade({
            "user_id": user_id,
            "type": "buy",
            "cc_amount": cc_amount,
            "usd_amount": quote["usd_required"],
            "effective_price": quote["effective_price"],
            "fee": quote["fee"],
            "timestamp": time.time()
        })

        return quote

    def execute_sell(self, user_id, cc_amount):
        """
        Execute a sell (user trades CC for USD).
        """
        # Similar logic, inverted
        # (cc_reserve + cc_amount) × (usd_reserve - usd_received) = k
        # ...

    def add_liquidity(self, user_id, cc_amount, usd_amount):
        """
        User provides liquidity to pool, receives LP tokens.

        LP tokens represent proportional ownership of pool.
        """
        # Verify ratio matches current pool ratio
        current_ratio = self.usd_reserve / self.cc_reserve
        provided_ratio = usd_amount / cc_amount

        if abs(provided_ratio - current_ratio) > 0.01:
            raise RatioMismatchError("Must provide liquidity at current ratio")

        # Calculate LP token share
        lp_share = cc_amount / self.cc_reserve  # % of pool

        # Update reserves
        self.cc_reserve += cc_amount
        self.usd_reserve += usd_amount
        self.k = self.cc_reserve * self.usd_reserve

        # Mint LP tokens to user
        mint_lp_tokens(user_id, lp_share)

        return lp_share

    def remove_liquidity(self, user_id, lp_share):
        """
        User burns LP tokens, receives proportional CC + USD.
        """
        # Calculate amounts to return
        cc_returned = self.cc_reserve * lp_share
        usd_returned = self.usd_reserve * lp_share

        # Update reserves
        self.cc_reserve -= cc_returned
        self.usd_reserve -= usd_returned
        self.k = self.cc_reserve * self.usd_reserve

        # Burn user's LP tokens
        burn_lp_tokens(user_id, lp_share)

        # Return assets to user
        add_cc(user_id, cc_returned)
        add_usd(user_id, usd_returned)

        return {
            "cc_returned": cc_returned,
            "usd_returned": usd_returned
        }
```

**Benefits:**
- Always available liquidity (never "no matches")
- Simple UX ("swap" button, instant execution)
- Predictable pricing (calculate before executing)
- Proven model (Uniswap has $4B+ TVL)

**Drawbacks:**
- Slippage on large trades
- Impermanent loss for LPs
- Requires platform to seed initial liquidity
- Less efficient than order book for perfect matches

---

### Hybrid Model (RECOMMENDED)

**Best of both worlds:**
```
Small trades (<100 CC): Route to AMM
- Instant execution
- No waiting for matches
- Acceptable slippage

Large trades (>100 CC): Route to Order Book
- Better pricing
- Reduced slippage
- Worth waiting for match

Platform logic:
if trade_amount < 100:
    use_amm()
else:
    try_order_book()
    if no_match_after_30_seconds:
        use_amm()  # Fallback
```

---

## Escrow and Settlement

### P2P Direct Trading (Manual)

**Use case:** Friends/colleagues trading CC directly

**Flow:**
```
1. Seller creates offer:
   "Selling 500 CC for $45 USD (10% discount)"

2. Buyer accepts offer

3. Platform escrows:
   - Seller's 500 CC (locked)
   - Buyer's $45 USD (locked)

4. Seller confirms: "USD received via Venmo/PayPal"
   OR
   Buyer confirms: "CC delivered"

5. Both confirm → Platform releases assets
   - 500 CC → Buyer
   - $45 USD → Seller (minus 2% platform fee)

6. If dispute: Platform reviews evidence, makes final decision
```

**Code Implementation:**

```python
class P2PEscrow:
    def create_offer(self, seller_id, cc_amount, usd_price):
        """
        Seller lists CC for sale.
        """
        # Verify seller has CC
        if get_cc_balance(seller_id) < cc_amount:
            raise InsufficientFundsError()

        # Lock seller's CC in escrow
        escrow_cc(seller_id, cc_amount)

        offer = {
            "id": generate_uuid(),
            "seller_id": seller_id,
            "cc_amount": cc_amount,
            "usd_price": usd_price,
            "status": "open",
            "created_at": time.time(),
            "expires_at": time.time() + 86400  # 24 hours
        }

        db.insert("p2p_offers", offer)
        return offer["id"]

    def accept_offer(self, offer_id, buyer_id):
        """
        Buyer accepts seller's offer, initiates escrow.
        """
        offer = db.get("p2p_offers", offer_id)

        if offer["status"] != "open":
            raise OfferUnavailableError()

        # Verify buyer has USD
        if get_usd_balance(buyer_id) < offer["usd_price"]:
            raise InsufficientFundsError()

        # Lock buyer's USD in escrow
        escrow_usd(buyer_id, offer["usd_price"])

        # Update offer status
        offer["status"] = "in_escrow"
        offer["buyer_id"] = buyer_id
        db.update("p2p_offers", offer)

        # Notify both parties
        notify(offer["seller_id"], "Buyer accepted your offer")
        notify(buyer_id, "Offer accepted, complete payment")

        return offer

    def confirm_payment(self, offer_id, user_id, payment_proof=None):
        """
        Seller or buyer confirms payment completed.

        Requires BOTH parties to confirm before releasing escrow.
        """
        offer = db.get("p2p_offers", offer_id)

        if user_id == offer["seller_id"]:
            offer["seller_confirmed"] = True
            offer["seller_confirmation_time"] = time.time()
            offer["payment_proof"] = payment_proof

        elif user_id == offer["buyer_id"]:
            offer["buyer_confirmed"] = True
            offer["buyer_confirmation_time"] = time.time()

        else:
            raise UnauthorizedError()

        db.update("p2p_offers", offer)

        # Check if both confirmed
        if offer.get("seller_confirmed") and offer.get("buyer_confirmed"):
            self.release_escrow(offer_id)

    def release_escrow(self, offer_id):
        """
        Both parties confirmed, release assets.
        """
        offer = db.get("p2p_offers", offer_id)

        platform_fee = offer["usd_price"] * 0.02  # 2% fee

        # Transfer CC: seller → buyer
        transfer_cc(
            from_user=offer["seller_id"],
            to_user=offer["buyer_id"],
            amount=offer["cc_amount"]
        )

        # Transfer USD: buyer → seller (minus fee)
        transfer_usd(
            from_user=offer["buyer_id"],
            to_user=offer["seller_id"],
            amount=offer["usd_price"] - platform_fee
        )

        # Collect platform fee
        collect_fee(platform_fee)

        # Update offer status
        offer["status"] = "completed"
        offer["completed_at"] = time.time()
        db.update("p2p_offers", offer)

        # Notify parties
        notify(offer["seller_id"], "Trade completed!")
        notify(offer["buyer_id"], "Trade completed!")

    def dispute(self, offer_id, user_id, reason):
        """
        User raises a dispute (payment not received, CC not delivered, etc.)
        """
        offer = db.get("p2p_offers", offer_id)

        offer["status"] = "disputed"
        offer["dispute_raised_by"] = user_id
        offer["dispute_reason"] = reason
        offer["dispute_time"] = time.time()
        db.update("p2p_offers", offer)

        # Escalate to admin review
        escalate_to_admin(offer_id)

        # Freeze escrow until resolution
        # Admin will manually release to appropriate party
```

---

## Liquidity Incentives

### Problem: Bootstrapping AMM Liquidity

**Challenge:** AMM needs liquidity to work, but why would users provide it?

**Solution: Multi-Layered Incentives**

#### 1. Trading Fee Share (Standard)
```
AMM charges 0.3% fee on all trades
100% of fees go to liquidity providers (LPs)

Example:
- Pool has $10K USD + 100K CC
- Daily trading volume: $50K
- Daily fees: $50K × 0.003 = $150
- Distributed to LPs proportionally

If you own 10% of pool (via LP tokens):
→ You earn $15/day = $5,475/year
→ On $1K investment = 547% APY (if volume sustains)
```

#### 2. Platform Incentives (Bootstrap)
```
Platform allocates 1M CC (10% of genesis supply) for LP rewards

Distribution:
- Month 1-3: 100K CC/month → Early LPs get massive rewards
- Month 4-6: 50K CC/month → Tapered rewards
- Month 7-12: 25K CC/month → Ongoing support
- Year 2+: Market-driven (trading fees only)

Example (Month 1):
- You provide $1K USD + 10K CC liquidity
- Pool total: $10K USD + 100K CC
- Your share: 10%
- Monthly reward: 100K CC × 10% = 10K CC ($1,000 value)
- Effective return: $1,000/month on $1K investment = 100% APY
```

#### 3. Impermanent Loss Protection
```
Problem: If CC price moves a lot, LPs may lose value vs just holding

Solution: Platform covers impermanent loss for first 12 months
- LP adds liquidity at CC = $0.10
- 6 months later withdraws at CC = $0.15
- Impermanent loss: 2% (would've been better just holding CC)
- Platform refunds 2% in CC to make LP whole
```

---

## Price Discovery Mechanisms

### How to Determine "Fair" CC Price?

**Multiple Reference Points:**

```
1. Platform Sell Price (Ceiling)
   - Buying CC from platform: $0.10 per CC
   - This sets upper bound (why buy from market if cheaper from platform?)

2. Platform Buy Price (Floor)
   - Selling CC to platform: $0.10 - withdrawal_fee
   - With 5% fee: $0.095 per CC
   - This sets lower bound (why sell to users below platform rate?)

3. Market Forces (Middle)
   - Supply/demand in order book or AMM
   - Typically hovers around $0.10 ± 2%

4. External Indicators (Phase 3+)
   - If CC listed on Coinbase: Use spot price
   - If CC has futures: Use forward price
   - Cross-exchange arbitrage opportunities
```

**Price Oracle Design:**

```python
class PriceOracle:
    def get_fair_price(self):
        """
        Calculate fair market price for CC.

        Uses multiple data sources for accuracy.
        """
        prices = []

        # Source 1: Platform official rate
        platform_rate = 0.10  # $0.10 per CC
        prices.append(("platform", platform_rate, 0.30))  # 30% weight

        # Source 2: Order book mid-price
        order_book = get_order_book()
        if order_book["bids"] and order_book["asks"]:
            mid_price = (order_book["bids"][0]["price"] + order_book["asks"][0]["price"]) / 2
            prices.append(("order_book", mid_price, 0.30))  # 30% weight

        # Source 3: AMM pool price
        amm = get_amm()
        amm_price = amm.get_price()
        prices.append(("amm", amm_price, 0.30))  # 30% weight

        # Source 4: Recent trade prices (TWAP)
        recent_trades = get_recent_trades(hours=24)
        if recent_trades:
            twap = sum(t["price"] for t in recent_trades) / len(recent_trades)
            prices.append(("twap", twap, 0.10))  # 10% weight

        # Calculate weighted average
        total_weight = sum(weight for _, _, weight in prices)
        fair_price = sum(price * weight for _, price, weight in prices) / total_weight

        return {
            "fair_price": fair_price,
            "sources": prices,
            "confidence": self.calculate_confidence(prices)
        }

    def calculate_confidence(self, prices):
        """
        Higher confidence if all sources agree.
        Lower confidence if sources diverge (sign of manipulation or low liquidity).
        """
        price_values = [p for _, p, _ in prices]
        std_dev = statistics.stdev(price_values)
        mean = statistics.mean(price_values)

        # Coefficient of variation
        cv = std_dev / mean

        if cv < 0.02:  # Prices within 2%
            return "high"
        elif cv < 0.05:  # Prices within 5%
            return "medium"
        else:
            return "low"  # Prices diverging > 5% (potential manipulation)
```

---

## Anti-Manipulation Safeguards

### Threats

1. **Wash Trading:** User creates fake volume by trading with themselves
2. **Pump and Dump:** Coordinate to artificially inflate CC price, then sell
3. **Front-Running:** See large order, place own order first to profit
4. **Spoofing:** Place large fake orders to manipulate price, then cancel

### Countermeasures

```python
class AntiManipulation:
    def detect_wash_trading(self, user_id):
        """
        Flag if user is trading with themselves or coordinated accounts.

        Indicators:
        - Same IP address for buyer and seller
        - Trades between newly created accounts
        - Repeated trades at unusual prices (not profit-maximizing)
        - High volume with no net position change
        """
        recent_trades = db.query("""
            SELECT * FROM trades
            WHERE buyer_id = %s OR seller_id = %s
              AND timestamp > NOW() - INTERVAL '7 days'
        """, (user_id, user_id))

        # Check for self-trades
        self_trades = [t for t in recent_trades if t["buyer_id"] == t["seller_id"]]
        if len(self_trades) > 0:
            flag_user(user_id, "self_trading")

        # Check for coordinated accounts (same IP)
        buyer_ips = set(get_user_ip(t["buyer_id"]) for t in recent_trades)
        seller_ips = set(get_user_ip(t["seller_id"]) for t in recent_trades)
        if buyer_ips & seller_ips:  # Intersection
            flag_user(user_id, "coordinated_trading")

        # Check for zero-profit patterns
        net_cc_change = calculate_net_position_change(user_id, recent_trades)
        net_usd_change = calculate_net_usd_change(user_id, recent_trades)
        if abs(net_cc_change) < 100 and abs(net_usd_change) < 10:
            # High volume but no net position change = suspicious
            flag_user(user_id, "wash_trading")

    def prevent_pump_and_dump(self):
        """
        Detect coordinated price manipulation.

        Indicators:
        - Sudden 20%+ price increase with no news
        - Followed by large selloff
        - Multiple accounts involved
        """
        price_history = get_price_history(hours=24)

        # Check for sudden spikes
        for i in range(1, len(price_history)):
            price_change = (price_history[i] - price_history[i-1]) / price_history[i-1]

            if price_change > 0.20:  # 20% increase
                # Check if followed by selloff
                if i + 1 < len(price_history) and price_history[i+1] < price_history[i] * 0.90:
                    # Potential pump-and-dump
                    alert_admins("Possible pump-and-dump detected")

                    # Identify participants
                    pump_trades = get_trades_during_spike(price_history[i-1:i+1])
                    dump_trades = get_trades_during_dump(price_history[i:i+2])

                    # Flag coordinated accounts
                    pumpers = set(t["buyer_id"] for t in pump_trades)
                    dumpers = set(t["seller_id"] for t in dump_trades)
                    coordinators = pumpers & dumpers  # Same accounts pumped then dumped

                    for user_id in coordinators:
                        flag_user(user_id, "pump_and_dump")

    def circuit_breaker(self):
        """
        Halt trading if price moves too fast (like stock market circuit breakers).

        Rules:
        - If CC price moves > 10% in 1 hour: Pause trading for 15 minutes
        - If CC price moves > 20% in 1 hour: Pause trading for 1 hour
        - If CC price moves > 30% in 1 hour: Pause trading until admin review
        """
        current_price = get_current_price()
        price_1h_ago = get_price(hours_ago=1)
        price_change = abs(current_price - price_1h_ago) / price_1h_ago

        if price_change > 0.30:
            pause_trading(duration="indefinite")
            alert_admins("CRITICAL: 30% price swing, trading halted")
        elif price_change > 0.20:
            pause_trading(duration=3600)  # 1 hour
            alert_admins("WARNING: 20% price swing, trading paused 1 hour")
        elif price_change > 0.10:
            pause_trading(duration=900)  # 15 minutes
            log("INFO: 10% price swing, brief trading pause")
```

---

## Implementation Roadmap

### Phase 1: MVP (Months 1-6)

**Features:**
- ✅ P2P escrow trading (manual matching)
- ✅ Simple AMM (platform-seeded liquidity)
- ✅ Basic price oracle
- ❌ Order book (too complex for MVP)

**Metrics:**
- 100+ P2P trades
- $10K+ AMM liquidity
- CC price stable $0.08-$0.12

### Phase 2: Scale (Months 7-12)

**Features:**
- ✅ Order book trading
- ✅ Hybrid routing (AMM + order book)
- ✅ Anti-manipulation detection
- ✅ LP incentive program

**Metrics:**
- $100K+ daily trading volume
- 100+ active LPs
- <3% spread on order book

### Phase 3: Advanced (Months 13-24)

**Features:**
- ✅ External exchange listings (if desired)
- ✅ Advanced order types (stop-loss, take-profit)
- ✅ API for algorithmic trading
- ✅ Cross-chain bridges (if CC becomes a token)

---

## Conclusion

The Internal CC Marketplace transforms Compute Capital from a **payment mechanism** into a **liquid trading asset**, enabling:

1. **Price discovery** via order books + AMM
2. **Instant liquidity** via automated market making
3. **P2P flexibility** via escrow system
4. **Fair pricing** via multi-source oracle
5. **Anti-manipulation** via detection algorithms

**Key Success Factors:**
- Start simple (AMM + P2P)
- Incentivize liquidity providers aggressively
- Monitor for manipulation closely
- Add complexity gradually (order book in Phase 2)

**See Also:**
- `compute-capital-currency-design.md` - Token fundamentals
- `circulation-incentives.md` - Keeping CC flowing
- `advanced-features.md` - Futures and derivatives

---

**Document End**
