from profitview import Link, http, logger

# See docs: https://profitview.net/docs/trading/
class Trading(Link):
	'''
	A very simple SMA (Simple Moving Avearge) crossover trading strategy
    
    Based on the most recent 2 trades as the short term SMA (leading indicator)
    and the most recent 5 trades as the long term SMA (lagging indicator)
    
    
    opened position, will wait for stopLoss or  stopProfit
    
    for easier position managment, will at most open 1 position only
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
	ORDER_SIZE = 1 # For each open position size
	
	tradePxList = [] # Init the tradePxList to store the most recent trade px 
	
    # Stop price
    stopProfitPx = 0
	stopLossPx = 0

	init = True # for running the first time
    running = True # pause or resume the strategy
		
        
    #Called on market trades from subscribed symbols
    def trade_update(self, src, sym, data):
        # Start clean, close all the existing positions first
        if self.init and self.hasPosition():
            self.closePosition()
            
        self.init = False
        
        # Update the latest tradePx
        tradePx = data['price']
        self.updateTradePxList(tradePx)

		if self.running:
            # When there's no position, try to 
            if not self.hasPosition():
                self.determineOpenTrade()
            
            # When, check stopLoss or stopProfit
            else:
                self.determineStopTrade(tradePx)
        	

    def updateTradePxList(self, tradePx):
		# Update the tradePxList with the current tradePx
		self.tradePxList.append(tradePx)
        
        # Only use the most recent trade px defined in SMA_LONG_TRADES
        self.tradePxList = self.tradePxList[max(0, len(self.tradePxList) - self.SMA_LONG_TRADES): ]
		logger.info(self.tradePxList)
     

	# The main trade logic
	def determineOpenTrade(self):
        # Have enough number of trade px, do the trade logic
		if len(self.tradePxList) == self.SMA_LONG_TRADES:
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
                 1 (long signal): when sma crossover is bigger than the threshold (short term uptrend)
                 0: (no action signal): when sma crossover is within the threshold (signal not strong enough yet) and don't do anything
                -1: (short signal): when sma crossover is smaller the threshold (short term downtrend)
            '''
            diffPercent = (smaShort - smaLong) / smaShort * 100
            
            if diffPercent > self.THRESHOLD_PERCENT: signal = 1
            elif diffPercent < -self.THRESHOLD_PERCENT: signal = -1
            else: signal = 0

            logger.info(f"smaLong={smaLong}, smaShort={smaShort}, threshold%={self.THRESHOLD_PERCENT}, diff%={diffPercent}, signal={signal}")
            
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
			logger.info(f"Opening {side} position")

			self.sendMarketOrder(side, size)
            self.calcStopPrice()
            
		else:
  			logger.error('Wong signal')

    
    def calcStopPrice(self):
        # Calculate the stop profit and stop loss after opening a position
        positionSide = self.fetch_positions(self.VENUE)['data'][0]["side"]
        positionPx = self.fetch_positions(self.VENUE)['data'][0]["entry_price"]
        
        if positionSide == 'Buy':
            self.stopProfitPx = positionPx * (1 + self.STOP_PROFIT_PERCENT / 100)
            self.stopLossPx = positionPx * (1 - self.STOP_PROFIT_PERCENT / 100)
        else:
            self.stopProfitPx = positionPx * (1 - self.STOP_PROFIT_PERCENT / 100)
            self.stopLossPx = positionPx * (1 + self.STOP_PROFIT_PERCENT / 100)
            
        logger.info(f"stopProfitPx={self.stopProfitPx}, stopLossPx={self.stopLossPx}")    
    
    
	# Send the market order execution instruction to the exchange
	def sendMarketOrder(self, side, size):
		# Send market order to the exchange
        ret = self.create_market_order(self.VENUE, self.SYMBOL, side=side, size=size)
		retData = ret['data']
		logger.info(f"Market Order Executed: {retData['side']} {retData['order_size']}@{retData['order_price']}")
		
    
	# Check whether to stopProfit or stopLoss given the current trade price
	def determineStopTrade(self, tradePx):
        positionSide = self.fetch_positions(self.VENUE)['data'][0]["side"]
        logger.info(f"Check StopPrice for {positionSide} position: tradePx={tradePx}, stopProfitPx={self.stopProfitPx}, stopLossPx={self.stopLossPx}")
		
        # For long position 
        if positionSide == 'Buy':
			if tradePx > self.stopProfitPx :
                logger.info("### StopProfit")
				self.closePosition()
			elif tradePx < self.stopLossPx :
				logger.info("### StopLoss")
				self.closePosition()
        # For short position 
		elif positionSide == 'Sell':
			if tradePx < self.stopProfitPx :
				logger.info("### StopProfit")
				self.closePosition()
			elif tradePx > self.stopLossPx :
				logger.info("### StopLoss")
				self.closePosition()	

	
    def hasPosition(self):
        positions = self.fetch_positions(self.VENUE)['data']
        
        if len(positions) > 0: return True
        else: return False
        

	def closePosition(self):	
		positions = self.fetch_positions(self.VENUE)['data']

		for position in positions:
			'''
			Send Buy order to close the Sell position or
			Send Sell order to close the Buy position
			'''        
			side = 'Buy' if position['side'] == 'Sell' else 'Sell'
			logger.info(f"Closing position: {side} {position['sym']}, qty={position['pos_size']} @ Market")
            self.sendMarketOrder(side, position['pos_size'])

            
			
	# The following are webhook function which allow ProfitView to communicate external
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
