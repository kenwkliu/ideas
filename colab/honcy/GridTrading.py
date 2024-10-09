import collections
from concurrent.futures import ThreadPoolExecutor
import json
import math
import time

from profitview import Link, http, logger

VENUE = 'WooPaper'

Setting = collections.namedtuple('Setting', ['limit', 'base'])
settings = [
	Setting(2, 0.003),
	Setting(5, 0.0035),
	Setting(10, 0.004),
	Setting(15, 0.0045),
	Setting(20, 0.005),
]

class Price(object):
    def __init__(self):
        self.bid = 0
        self.ask = 0
        self.time = 0
        
    def update(self, bid, ask, time):
        self.bid = bid
        self.ask = ask
        self.time = time


class Symbol(object):
    def __init__(self, sym, factor):
        self.sym = sym
        self.factor = factor
        self.price = Price()
        
    def update_from_quote(self, trade_data):
        # logger.info(f "updating {self.sym}")
        self.price.update(
            trade_data['bid'][0] * self.factor,
            trade_data['ask'][0] * self.factor,
            trade_data['time'],
        )
        
    def buy(self, link, size):
        size = round(size * abs(self.factor), 1)
        link.create_market_order(
            VENUE,
            sym=self.sym,
            side='Buy',
            size=size,
        )
        logger.info(f"Bought {size} of {self.sym} @ {self.price.ask / self.factor}")
    
    def sell(self, link, size):
        size = round(size * abs(self.factor), 1)
        link.create_market_order(
            VENUE,
            sym=self.sym,
            side='Sell',
            size=size,
        )
        logger.info(f"Sold {size} of {self.sym} @ {self.price.bid / self.factor}")

    
class Portfolio(object):
    STOP_LOSS_THRESHOLD = 0.04  # 0.025
    # STOP_PROFIT_THRESHOLD = 0.004
    THRESHOLD = 0.004
    STEP = 0.0015
    # POSITION_LIMIT = 50
    
    def __init__(self, symbols, parity):
        self.assets = {
            symbol.sym: symbol
            for symbol in symbols
        }
        self.size = abs(symbols[-1].factor)
        self.position_count = 0
        self.positions = collections.deque([])
        self.stop_profit_counts = 0
        self.stop_loss_counts = 0
        self.next_upper = self.THRESHOLD
        self.next_lower = -self.THRESHOLD
        self.last_order_at = 0  # For threshold
        self.new_order_allowed = False
        self.new_position_allowed = False
        self.parity = parity
		self.start_at = int(time.time())
		self.current_setting = 4
		self.base_profit = 0.005
		self.position_limit = 50
		self.update_setting()
		
	def update_setting(self):
		self.base_profit = settings[self.current_setting].base
		self.position_limit = settings[self.current_setting].limit
		logger.info(f"Updated, base profit is {self.base_profit}, position limit is {self.position_limit}")

    @property
    def stop_profit_threshold(self):
		return self.base_profit + max(0, 10 - self.position_count) * 0.0004
    
    def get_report(self):
        return {
            "assets": [
                {
                    'symbol': symbol.sym,
                    'bid': symbol.price.bid / symbol.factor,
                    'ask': symbol.price.ask / symbol.factor,
                }
                for symbol in self.assets.values()
            ],
            "# of positions": self.position_count,
            "positions": list(self.positions),
            "# of stop profit": self.stop_profit_counts,
            "# of stop loss": self.stop_loss_counts,
            "next upper": self.next_upper,
            "next lower": self.next_lower,
            "last order at": self.last_order_at,
            "parity": self.parity,
            "new order allowed": self.new_order_allowed,
            "new position allowed": self.new_position_allowed,
        }
        
    def get_new_diff(self, with_log=False):
        long_ask, long_bid, short_ask, short_bid = 0, 0, 0, 0
        for symbol in self.assets.values():
            if symbol.price.time == 0:
                return None

            if symbol.factor > 0:
                long_ask += symbol.price.ask
                long_bid += symbol.price.bid
            else:
                short_ask -= symbol.price.ask
                short_bid -= symbol.price.bid
        
        if any(x <= 0 for x in (long_ask, long_bid, short_ask, short_bid)):
            return None
        
        low_diff = math.log(long_bid) - math.log(short_ask) - self.parity
        high_diff = math.log(long_ask) - math.log(short_bid) - self.parity
        if with_log:
            logger.info((
                f"long side price {long_bid / self.size:.4f} - {long_ask / self.size:.4f}, "
                f"short side price {short_bid / self.size:.4f} - {short_ask / self.size:.4f}, "
                f"diff {low_diff:.4f} - {high_diff:.4f}"
            ))
        return (low_diff, high_diff)
    
    def get_imparity(self):
        now = int(time.time() * 1000)
        return {
            'time': [now - symbol.price.time for symbol in self.assets.values()],
            'imparity': self.get_new_diff(with_log=True)
        }
    
    def place_order(self, link, new_diff, now):
        low_diff, high_diff = new_diff
        position_change = 0
        if (
            self.position_count > 0
            and high_diff > self.positions[0] > 0
            and high_diff - self.positions[0] > self.STOP_LOSS_THRESHOLD
        ):
            # Stop loss case 1
            self.stop_loss_counts += 1
            logger.info(f"Stop loss #{self.stop_loss_counts}, low short at {self.positions[0]}, cover at {high_diff}")
            self.positions.popleft()
            self.position_count -= 1
            position_change = 1
            self.next_upper = high_diff
        elif (
            self.position_count > 0
            and low_diff < self.positions[-1] < 0
            and self.positions[-1] - low_diff > self.STOP_LOSS_THRESHOLD
        ):
            # Stop loss case 2
            self.stop_loss_counts += 1
            logger.info(f"Stop loss #{self.stop_loss_counts}, high long at {self.positions[-1]}, cover at {low_diff}")
            self.positions.pop()
            self.position_count -= 1
            position_change = -1
            self.next_lower = low_diff
        elif (
            self.position_count > 0
            and self.positions[0] < 0
            and (
                low_diff > self.THRESHOLD
                or low_diff - self.positions[0] > self.stop_profit_threshold
            )
        ):
            # Stop profit case 1
            self.stop_profit_counts += 1
            logger.info(f"Stop profit #{self.stop_profit_counts}, low long at {self.positions[0]}, stop at {low_diff}")
            self.next_lower = self.positions.popleft()
            self.position_count -= 1
            if self.position_count == 0:
                self.next_lower = min(-self.THRESHOLD, low_diff - self.STEP)
            position_change = -1
        elif (
            self.position_count > 0
            and self.positions[-1] > 0
            and (
                high_diff < -self.THRESHOLD
                or self.positions[-1] - high_diff > self.stop_profit_threshold
            )
        ):
            # Stop profit case 2
            self.stop_profit_counts += 1
            logger.info(f"Stop profit #{self.stop_profit_counts}, high short at {self.positions[-1]}, stop at {high_diff}")
            self.next_upper = self.positions.pop()
            self.position_count -= 1
            if self.position_count == 0:
                self.next_upper = max(self.THRESHOLD, high_diff + self.STEP)
            position_change = 1
        elif (
            self.new_position_allowed
            and self.position_count < self.position_limit
            and high_diff < self.next_lower
        ):
            # New position case 1
            logger.info(f"new long position at {high_diff}")
            self.positions.appendleft(high_diff)
            self.next_lower = high_diff - self.STEP
            self.next_upper = self.THRESHOLD
            self.position_count += 1
            position_change = 1
        elif (
            self.new_position_allowed
            and self.position_count < self.position_limit
            and low_diff > self.next_upper
        ):
            # New position case 2
            logger.info(f"new short position at {low_diff}")
            self.positions.append(low_diff)
            self.next_upper = low_diff + self.STEP
            self.next_lower = -self.THRESHOLD
            self.position_count += 1
            position_change = -1
        else:
            # Nothing to do
            return

        logger.info(self.positions)
        for symbol in self.assets.values():
            func = symbol.buy if position_change * symbol.factor > 0 else symbol.sell
            func(link, 1)
        # with ThreadPoolExecutor(max_workers=3) as e:
        #     for symbol in self.assets.values():
        #         func = symbol.buy if position_change * symbol.factor > 0 else symbol.sell
        #         e.submit(func, link, 1)

        self.last_order_at = now
        
    def update_from_quote(self, link, sym, data):
		remaining = 86400 - (int(time.time()) - self.start_at)
		if remaining <= 0:
			self.close_all_positions(link)
			return False
		
		setting_idx = min(4, remaining // 9000)
		if self.current_setting != setting_idx:
			self.current_setting = setting_idx
			self.update_setting()
		
        now = data['time']
        symbol = self.assets.get(sym)
        if not symbol:
            return True
        symbol.update_from_quote(data)
        if not self.new_order_allowed or now - self.last_order_at <= 5000:
            return True
        new_diff = self.get_new_diff()
        if new_diff is None:
            return True
        
        self.place_order(link, new_diff, now)
		return True
        
    def close_all_positions(self, link):
        size = 0
        for position in self.positions:
            if position > 0:
                size -= 1
            else:
                size += 1
                
        if size == 0:
            return
        
        logger.info("Closing all positions...")
		logger.info(
			f"imparity: {self.get_new_diff()}, positions: {self.positions}"
		)
        for symbol in self.assets.values():
            func = symbol.buy if size * symbol.factor < 0 else symbol.sell
            func(link, abs(size))
        # with ThreadPoolExecutor(max_workers=3) as e:
        #     for symbol in self.assets.values():
        #         func = symbol.buy if size * symbol.factor < 0 else symbol.sell
        #         e.submit(func, link, abs(size))


class Trading(Link):
    """See docs: https://profitview.net/docs/trading/"""
    def __init__(self, *args, **kwargs):
        self.running = False
        self.portfolio = None
        super(Trading, self).__init__(*args, **kwargs)
        
    def on_start(self):
        """Called on start up of trading script"""
        
    def order_update(self, src, sym, data):
        """Called on order updates from connected exchanges"""

    def fill_update(self, src, sym, data):
        """Called on trade fill updates from connected exchanges"""

    def quote_update(self, src, sym, data):
        """Called on top of book quotes from subscribed symbols"""
        if self.running and self.portfolio is not None:
            if not self.portfolio.update_from_quote(self, sym, data):
				self.running = False
				self.portfolio = None

    def trade_update(self, src, sym, data):
        """Called on market trades from subscribed symbols"""
        # if self.running and self.portfolio is not None:
        #     self.portfolio.update_from_trade(self, sym, data)

    @http.route
    def get_portfolio(self, data):
        """Definition of GET request endpoint - see docs for more info"""
        if self.portfolio is None:
            return None
        return self.portfolio.get_report()
        
    @http.route
    def get_imparity(self, data):
        if self.running and self.portfolio is not None:
            return self.portfolio.get_imparity()

    @http.route
    def post_new(self, data):
        """Definition of POST request endpoint - see docs for more info"""
        if 'portfolio' in data and 'parity' in data:
            x = json.loads(data['portfolio'])
            portfolio = Portfolio([
                Symbol(sym, float(factor))
                for sym, factor in x.items()
            ], float(data['parity']))
            self.portfolio = portfolio
            self.running = True
        return None
    
    @http.route
    def post_toggle(self, data):
        if self.portfolio is not None:
            if 'order' in data:
                self.portfolio.new_order_allowed = data['order']
            if 'position' in data:
                self.portfolio.new_position_allowed = data['position']
        return self.portfolio.get_report()
    
	def stop(self):
		self.running = False
        if self.portfolio is not None:
            self.portfolio.close_all_positions(self)
            self.portfolio = None

    @http.route
    def post_stop(self, data):
        """Definition of POST request endpoint - see docs for more info"""
		self.stop()
        return data