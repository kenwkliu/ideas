import pandas as pd

TRADING_DAYS_IN_YEARS = 256

# Calculate the PnL of the Pair portfolio
def calcPortfolio(pairsBackTest):
	portfolio = []
	portfolioPnl = 0

	for backtestDf in pairsBackTest:
		stats, pnlDf = calcPnl(backtestDf)
		pnl = stats['tradingPnL'] - stats['shortInterest'] - stats['transCost']
		
		stockA = backtestDf.columns[0]
		stockB = backtestDf.columns[1]
		print("{} vs {} ---> ${}".format(stockA, stockB, pnl))

		portfolio.append([stockA, stockB, stats['tradingPnL'], stats['shortInterest'], stats['transCost'], pnl])
		portfolioPnl += pnl

	print("=================================================================")
	print('PortfolioPnl: $', portfolioPnl)
	portfolioDf = pd.DataFrame(portfolio, columns=['stockA', 'stocksB', 'tradingPnL', 'shortInterest', 'transCost', 'Pnl'])
	return portfolioPnl, portfolioDf


# Calculate the PnL of one Pair
def calcPnl(backTest_df, interestRate=0.03, commRate=0.005):
	dailyInterestRate = interestRate / TRADING_DAYS_IN_YEARS
	pnl_df = backTest_df.copy()

	pnl_df[['longPos', 'shortPos', 'longValue', 'shortValue', 'longPnl', 'shortPnl', 'shortInterest', 'transCost', 'pnl', 'totalPnl']] = 0
	signal, longPos, shortPos, longValue, shortValue, longPnl, shortPnl, shortInterest, transCost, pnl, accumPnl, totalPnl = 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0

	for index, row in pnl_df.iterrows():
		currentSignal = row['signal']
		transCost = 0
		
		# When trading signal is changed
		if currentSignal != signal:
			if currentSignal == 0:
				transCost = (curentLongValue + curentShortValue) * commRate
				longValue = 0
				shortValue = 0

			else:
				longValue = row['dollarValue']
				shortValue = row['dollarValue']
				transCost = (longValue + shortValue) * commRate

			longPos = getLongPos(currentSignal, longValue, row)
			shortPos = getShortPos(currentSignal, shortValue, row)

			
			
			longPnl = 0
			shortPnl = 0

			pnl = 0
			accumPnl = totalPnl

		#Store current row value
		pnl_df.loc[index, 'transCost'] = transCost
		
		pnl_df.loc[index, 'longPos'] = longPos
		pnl_df.loc[index, 'shortPos'] = shortPos

		curentLongValue = getLongValue(currentSignal, longPos, row)
		pnl_df.loc[index, 'longValue'] = curentLongValue

		curentShortValue = getShortValue(currentSignal, shortPos, row)
		pnl_df.loc[index, 'shortValue'] = curentShortValue

		currentLongPnl = curentLongValue - longValue
		pnl_df.loc[index, 'longPnl'] = currentLongPnl

		currentShortPnl = shortValue - curentShortValue
		pnl_df.loc[index, 'shortPnl'] = currentShortPnl

		if curentShortValue > 0:
			curentShortInterest = row['dollarValue'] * dailyInterestRate
		else:
			curentShortInterest = 0

		pnl_df.loc[index, 'shortInterest'] = curentShortInterest

		currentPnl = currentLongPnl + currentShortPnl
		pnl_df.loc[index, 'pnl'] = currentPnl

		totalPnl = accumPnl + currentPnl
		pnl_df.loc[index, 'totalPnl'] = totalPnl

		signal = currentSignal

	tradingPnL = pnl_df['totalPnl'].iloc[-1]
	
	stats = {}
	stats['tradingPnL'] = tradingPnL
	stats['shortInterest'] = pnl_df['shortInterest'].sum()
	stats['transCost'] = pnl_df['transCost'].sum()
	
	return stats, pnl_df


def getLongPos(signal, longValue, row):
	if longValue == 0 or signal == 0 : return 0
	if signal == -1: return longValue / row[0]
	if signal == 1: return longValue / row[1]


def getShortPos(signal, shortValue, row):
	if shortValue == 0 or signal == 0 : return 0
	if signal == -1: return shortValue / row[1]
	if signal == 1: return shortValue / row[0]


def getLongValue(signal, longPos, row):
	if longPos == 0 or signal == 0 : return 0
	if signal == -1: return longPos * row[0]
	if signal == 1: return longPos * row[1]


def getShortValue(signal, shortPos, row):
	if shortPos == 0 or signal == 0 : return 0
	if signal == -1: return shortPos * row[1]
	if signal == 1: return shortPos * row[0]