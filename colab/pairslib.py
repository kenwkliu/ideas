import pandas as pd

# Calculate the PnL of the Pair portfolio
def calcPortfolio(pairsBackTest):
	portfolio = []
	portfolioPnl = 0

	for backtestDf in pairsBackTest:
		pnl, pnlDf = calcPnl(backtestDf)

		stockA = backtestDf.columns[0]
		stockB = backtestDf.columns[1]
		print(stockA, 'vs', stockB, '---> $', pnl)

		portfolio.append([stockA, stockB, pnl])
		portfolioPnl += pnl

	print("=================================================================")
	print('PortfolioPnl: $', portfolioPnl)
	portfolioDf = pd.DataFrame(portfolio, columns=['stockA', 'stocksB', 'Pnl'])
	return portfolioPnl, portfolioDf


# Calculate the PnL of one Pair
def calcPnl(backTest_df):
	pnl_df = backTest_df.copy()

	pnl_df[['longPos', 'shortPos', 'longValue', 'shortValue', 'longPnl', 'shortPnl', 'pnl', 'totalPnl']] = 0
	signal, longPos, shortPos, longValue, shortValue, longPnl, shortPnl, pnl, accumPnl, totalPnl = 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0

	for index, row in pnl_df.iterrows():
		currentSignal = row['signal']

		if currentSignal != signal:
			if currentSignal == 0:
				longValue = 0
				shortValue = 0

			else:
				longValue = row['dollarValue']
				shortValue = row['dollarValue']

			longPos = getLongPos(currentSignal, longValue, row)
			shortPos = getShortPos(currentSignal, shortValue, row)

			longPnl = 0
			shortPnl = 0

			pnl = 0
			accumPnl = totalPnl

		#Store current row value
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

		currentPnl = currentLongPnl + currentShortPnl
		pnl_df.loc[index, 'pnl'] = currentPnl

		totalPnl = accumPnl + currentPnl
		pnl_df.loc[index, 'totalPnl'] = totalPnl

		signal = currentSignal

	finalPnl = pnl_df['totalPnl'].iloc[-1]
	return finalPnl, pnl_df


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