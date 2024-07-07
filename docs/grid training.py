from profitview import Link, logger

class Trading(Link):
    '''
    Highly Sensitive Grid Trading Bot for automated trading on the ProfitView platform, using market orders.
    '''

    # Initialize trading parameters
    SRC = 'woo'
    VENUE = 'WooPaper'
    SYMBOL = 'PERP_BTC_USDT'
    INITIAL_GRID_SIZE = 5  # Increased grid size
    ORDER_SIZE = 10  # Order size for each grid level
    GRID_MARGIN = 0.005  # Reduced margin percentage for more frequent adjustments
    GRID_STEP_PERCENTAGE = 0.5  # Grid step as a percentage of the price

    def on_start(self):
        """Setup initial variables and wait for the first quote to initialize the grid."""
        self.current_price = None
        self.last_order_price = None
        self.grid_levels = []
        self.previous_grid_levels = []

    def quote_update(self, src, sym, data):
        """Monitor market prices and place market orders when grid levels are hit, adjust grid if necessary."""
        bid_price = data['bid'][0]
        ask_price = data['ask'][0]
        mid_price = (bid_price + ask_price) / 2

        if not self.current_price or abs(mid_price - self.current_price) > self.GRID_MARGIN * self.current_price:
            self.initialize_grid(mid_price)
            self.current_price = mid_price

        if self.should_place_order(mid_price):
            self.place_market_order(mid_price)

    def initialize_grid(self, start_price):
        """Initialize or adjust grid levels based on the current price."""
        self.close_positions_between_grids()
        
        self.previous_grid_levels = self.grid_levels.copy()
        
        grid_step = start_price * (self.GRID_STEP_PERCENTAGE / 100)
        self.grid_levels = [start_price + i * grid_step for i in range(-self.INITIAL_GRID_SIZE, self.INITIAL_GRID_SIZE + 1)]
        self.last_order_price = None  # Reset last order price on grid re-initialization
        logger.info(f"Grid (re)initialized around price {start_price} with dynamic step {grid_step}")

    def close_positions_between_grids(self):
        """Fetch and close positions that are between the new grid level and old grid level."""
        positions = self.fetch_positions(self.VENUE)
        if positions['error']:
            logger.error(f"Error fetching positions: {positions['error']['message']}")
            return
        
        if not positions['data']:
            return

        CLOSE_SIDE = {'Buy': 'Sell', 'Sell': 'Buy'}

        for position in positions['data']:
            entry_price = position['entry_price']
            if self.is_between_grids(entry_price):
                self.create_market_order(
                    self.VENUE,
                    sym=self.SYMBOL,
                    side=CLOSE_SIDE[position['side']],
                    size=position['pos_size'],
                )
                logger.info(f"Closed {position['side']} position of size {position['pos_size']} at price {position['entry_price']}.")

    def is_between_grids(self, price):
        """Check if the price is between the old and new grid levels."""
        for old_level in self.previous_grid_levels:
            for new_level in self.grid_levels:
                if min(old_level, new_level) <= price <= max(old_level, new_level):
                    return True
        return False

    def should_place_order(self, price):
        """Determine if a market order should be placed based on grid levels."""
        closest_grid_level = min(self.grid_levels, key=lambda x: abs(x - price))
        if self.last_order_price is None or abs(closest_grid_level - self.last_order_price) >= price * (self.GRID_STEP_PERCENTAGE / 100):
            return True
        return False

    def place_market_order(self, price):
        """Place a market order and update the last order price."""
        direction = 'Buy' if price < self.current_price else 'Sell'
        self.create_market_order(self.VENUE, self.SYMBOL, side=direction, size=self.ORDER_SIZE)
        self.last_order_price = price
        logger.info(f"Placed {direction} market order at {price} for {self.ORDER_SIZE} units.")

    def on_stop(self):
        """Clean up when stopping the bot."""
        logger.info("Stopping the trading bot.")