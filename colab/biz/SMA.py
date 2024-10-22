from profitview import Link, http, logger


class Trading(Link):
    """See docs: https://profitview.net/docs/trading/"""

	'''
	A very simple SMA (Simple Moving Avearge) crossover trading strategy
	'''
	
	# Account and symbol 
	SRC = 'woo'
	VENUE = 'WooPaper'
	SYMBOL = 'PERP_BTC_USDT'	

	# Define trading parameters	(constants)
	SMA_SHORT_TRADES = 2
	SMA_LONG_TRADES = 5	
	THRESHOLD_PERCENT = 0.005
	STOP_PROFIT_PERCENT = 0.01
	STOP_LOSS_PERCENT = -0.01
	ORDER_SIZE = 1
	
	# Account position 
	positionSide = ''
	positionSize = 0
	positionPx = 0
	
    # Stop price
    stopProfitPx = 0
	stopLossPx = 0
	
	# Init the tradePxList to store the most recent trade px 
	tradePxList = []

	# pause or resume the strategy
	running = True
	
    def on_start(self):
        """Called on start up of trading script"""
		
		# Get the latest account position
		# which update positionSide, positionSize, positionPx
		self.queryLatest()
		
		
    def trade_update(self, src, sym, data):
        """Called on market trades from subscribed symbols"""
		if self.running:
			self.mainLogic(data)
		
     
     # Update current position and stop price
	def queryLatest(self):
		positionData = self.fetch_positions(self.VENUE)['data']
		
		if len(positionData) > 0: 
			position = positionData[0]
			self.positionSide = position['side']
			self.positionSize = position['pos_size']
			self.positionPx = position['entry_price']
		else:
			self.positionSide = ''
			self.positionSize = 0
			self.positionPx = 0
			
        if self.positionSide == 'Buy':
			self.stopProfitPx = self.positionPx * (1 + self.STOP_PROFIT_PERCENT / 100)
			self.stopLossPx = self.positionPx * (1 - self.STOP_PROFIT_PERCENT / 100)
		elif self.positionSide == 'Sell':
			self.stopProfitPx = self.positionPx * (1 - self.STOP_PROFIT_PERCENT / 100)
			self.stopLossPx = self.positionPx * (1 + self.STOP_PROFIT_PERCENT / 100)
		else:
			self.stopProfitPx = 0
			self.stopLossPx = 0
			
		logger.info("Position: {} {}@{}, stopProfitPx={}, stopLossPx={}"
					.format(self.positionSide, self.positionSize, self.positionPx,
						   self.stopProfitPx, self.stopLossPx))
		
		
	# Main logic that called by every trade happens in the market
	def mainLogic(self, data):
		# Update the tradePxList with the current tradePx
		self.tradePxList.append(tradePx := data['price'])
        # Only use the most recent (SMA_LONG_TRADES) trade px
        self.tradePxList = self.tradePxList[max(0, len(self.tradePxList) - self.SMA_LONG_TRADES):  ]
		logger.info(self.tradePxList)
		
		if self.positionSize == 0:
			# When there's no position and have enough number of trade px, do the trade logic
			if len(self.tradePxList) == self.SMA_LONG_TRADES:
            	self.determineTrade()
		
		# Do stopLoss or stopProfit
		else:
			self.determineStop(tradePx)


	# The main trade logic
	def determineTrade(self):
        '''
		1. Calculate trading indicators (smaLong, smaShort) from the current tradePxList
			Using the recent SMA_LONG_TRADES number of trades for the smaLong (lagging) indicator
			Using the recent SMA_SHORT_TRADES number of trades for the smaShort (leading) indicator
        '''
		smaLong = sum(self.tradePxList) / self.SMA_LONG_TRADES 
        smaShort = sum(self.tradePxList[(self.SMA_LONG_TRADES - self.SMA_SHORT_TRADES):]) / self.SMA_SHORT_TRADES
        # Determine the trading signal and send order accordling

		'''
		2. Determine the trading signal
		 	 1: long signal - when sma crossover is bigger than the threshold (short term uptrend)
		 	 0: flat signal - when sma crossover is within the threshold (signal not strong enough yet)
		 	-1: short signal - when sma crossover is smaller the threshold (short term downtrend)
		'''
		diffPercent = (smaShort - smaLong) / smaShort * 100
		
		if diffPercent > self.THRESHOLD_PERCENT: signal = 1
		elif diffPercent < -self.THRESHOLD_PERCENT: signal = -1
		else: signal = 0

		logger.info("smaLong={}, smaShort={}, threshold%={}, diff%={}, signal={}"
					.format(smaLong, smaShort, self.THRESHOLD_PERCENT, diffPercent, signal))		
		
		'''
        3. Open a trade position if signal is non-zero
		'''
		if signal != 0:
			self.openPosition(signal)
		
		
	# Depends on the signal, open a Buy(long) / Sell(short) position		
	def openPosition(self, signal):
		if signal == 1 or signal == -1:
			# signal ==  1: Buy
            # signal == -1: Sell
            side = 'Buy' if signal == 1 else 'Sell'
			size = self.ORDER_SIZE
			logger.info("Opening position: {} {}".format(side, size))

			self.sendMarketOrder(side, size)
		else:
  			logger.error('Wong signal')

    
	# Send the market order execution instruction to the exchange
	def sendMarketOrder(self, side, size):
		# Send market order to the exchange
        ret = self.create_market_order(self.VENUE, self.SYMBOL, side=side, size=size)
		retData = ret['data']
		logger.info("Market Order Executed: {} {}@{}"
				   .format(retData['side'], retData['order_size'], retData['order_price']))
		
        # After the trade, update to the current position and stop price
        self.queryLatest()	

    
	# Check whether to stopProfit or stopLoss given the current trade price
	def determineStop(self, tradePx):
        logger.info("Check StopPrice for {} position: tradePx={}, stopProfitPx={}, stopLossPx={}"
				   .format(self.positionSide, tradePx, self.stopProfitPx, self.stopLossPx))
		# For long position 
        if self.positionSide == 'Buy':
			if tradePx > self.stopProfitPx :
                logger.info("### StopProfit")
				self.closePosition()
			elif tradePx < self.stopLossPx :
				logger.info("### StopLoss")
				self.closePosition()
        # For short position 
		elif self.positionSide == 'Sell':
			if tradePx < self.stopProfitPx :
				logger.info("### StopProfit")
				self.closePosition()
			elif tradePx > self.stopLossPx :
				logger.info("### StopLoss")
				self.closePosition()	

	
	# Close the Buy/Sell position based on the current position holding
	def closePosition(self):
		size = self.positionSize
		
		if size > 0:
			'''
			Send Buy order to close the Sell position or
			Send Sell order to close the Buy position
			'''
			side = 'Buy' if self.positionSide == 'Sell' else 'Sell'
			logger.info("Closing position: {} {}".format(side, size))

			self.sendMarketOrder(side, size)

		else:
  			logger.error('No position to close')

			
	# The following are webhook function which allow ProfitView to communicate external
	@http.route
	def get_quote(self, data):
		return self.quotes[self.SRC][self.SYMBOL]	
	
	
	@http.route
	def get_trade(self, data):
		return self.trades[self.SRC][self.SYMBOL]
	
	
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
		return self.fetch_candles('Woo X', sym=self.SYMBOL, level=level, since=since)
	
	
	@http.route
	def get_balance(self, data):
		balance = {}
		balance['balance'] = self.fetch_balances(self.VENUE)['data']
		balance['position'] = self.fetch_positions(self.VENUE)['data']
		
		return balance

	
	@http.route
	def post_pause(self, data):
		self.running = False
		logger.info("Strategy paused")
		return "Paused"

	
	@http.route
	def post_resume(self, data):
		self.running = True
		logger.info("Strategy resumed")
		return "Resumed"
	
	
	@http.route
	def post_closeAllPositions(self, data):	
		positions = self.fetch_positions(self.VENUE)['data']
		msgList = []

		for position in positions:
			side = 'Buy' if position['side'] == 'Sell' else 'Sell'
			self.create_market_order(self.VENUE, position['sym'], side=side, size=position['pos_size'])

			msg = "Close position: {} {}, qty={} @ Market".format(side, position['sym'], position['pos_size'])
			msgList.append(msg)
			logger.info(msg)
			
		self.queryLatest()
		
		return msgList