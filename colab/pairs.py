import numpy as np

# based on the data from "Reserch period, 
# back test the result in "Test period"
def backTest(researchData, testData, stockA, stockB):
  cols = [stockA, stockB]
  research_df = researchData[cols].copy()
  backTest_df = testData[cols].copy()

  # Remove the NaN rows
  research_df.dropna(inplace = True)
  backTest_df.dropna(inplace = True)

  backTest_df = addSignal(research_df, backTest_df, stockA, stockB)
  pnl, backTest_df = calcPnl(backTest_df)

  return pnl, backTest_df



### PnL related
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


def calcPnl(backTest_df, dollarValue=10000):
  backTest_df[['longPos', 'shortPos', 'longValue', 'shortValue', 'longPnl', 'shortPnl', 'pnl', 'totalPnl']] = 0
  signal, longPos, shortPos, longValue, shortValue, longPnl, shortPnl, pnl, accumPnl, totalPnl = 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0

  for index, row in backTest_df.iterrows():
    currentSignal = row['signal']

    if currentSignal != signal:
      if currentSignal == 0:
        longValue = 0
        shortValue = 0
		
      else:      
        longValue = dollarValue
        shortValue = dollarValue

      longPos = getLongPos(currentSignal, longValue, row)
      shortPos = getShortPos(currentSignal, shortValue, row)

      longPnl = 0
      shortPnl = 0

      pnl = 0
      accumPnl = totalPnl

    #Store current row value
    backTest_df.loc[index, 'longPos'] = longPos
    backTest_df.loc[index, 'shortPos'] = shortPos

    curentLongValue = getLongValue(currentSignal, longPos, row)
    backTest_df.loc[index, 'longValue'] = curentLongValue

    curentShortValue = getShortValue(currentSignal, shortPos, row)
    backTest_df.loc[index, 'shortValue'] = curentShortValue

    currentLongPnl = curentLongValue - longValue
    backTest_df.loc[index, 'longPnl'] = currentLongPnl

    currentShortPnl = shortValue - curentShortValue
    backTest_df.loc[index, 'shortPnl'] = currentShortPnl

    currentPnl = currentLongPnl + currentShortPnl
    backTest_df.loc[index, 'pnl'] = currentPnl

    totalPnl = accumPnl + currentPnl
    backTest_df.loc[index, 'totalPnl'] = totalPnl

    signal = currentSignal

  finalPnl = backTest_df['totalPnl'].iloc[-1]
  return finalPnl, backTest_df