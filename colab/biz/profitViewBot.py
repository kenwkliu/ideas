from profitview import Link, http, logger


class Trading(Link):
    def __init__(self):
        super().__init__()
		venue = 'Woo X'
		logger.info('------- Start -------')
		#logger.info(self.fetch_balances(venue))
		#logger.info(self.fetch_open_orders(venue))
		logger.info(self.fetch_positions(venue))
		#logger.info(self.fetch_candles('Woo X', sym='PERP_BTC_USDT'))
	
    def order_update(self, src, sym, data):
        """Event: receive order updates from connected exchanges"""

    def fill_update(self, src, sym, data):
        """Event: receive trade fill updates from connected exchanges"""

    def quote_update(self, src, sym, data):
        """Event: receive top of book quotes from subscribed symbols"""

    def trade_update(self, src, sym, data):
		data['src'] = src
		data['sym'] = sym
		self.publish(sym, data)
        """Event: receive market trades from subscribed symbols"""


    @http.route
    def post_example(self, data):
        return data

	@http.route
	def get_balances(self, data):
		return self.fetch_balances('Woo X')
	
	@http.route
	def get_candles(self, data):
		if 'level' in data:
			level = data['level']
		else:
			level = '1m'		
		
		if 'since' in data:
			since = int(data['since'])
		else:
			since = None

		logger.info('level:{}, since:{}'.format(level, since))
		return self.fetch_candles('Woo X', sym='PERP_BTC_USDT', level=level, since=since)
	
	@http.route
	def get_quote(self, data):
		src = 'woo'
		sym = 'PERP_BTC_USDT'
		return self.quotes[src][sym]	
	
	@http.route
	def get_trade(self, data):
		src = 'woo'
		sym = 'PERP_BTC_USDT'
		return self.trades[src][sym]
	
	@http.route
	def get_trades(self, data):
		trades = {}
		trades['woo-PERP_BTC_USDT'] = self.trades['woo']['PERP_BTC_USDT']
		trades['bitmex-XBTUSD'] = self.trades['bitmex']['XBTUSD']	
		return trades