import numpy as np

def addSignal(backTest_df, params):
  backTest_df['ratio'] = backTest_df[params['PAIR_STOCK_A']] / backTest_df[params['PAIR_STOCK_B']]

  # signal == -1: Long A Short B
  # signal == 1: Short A Long B
  backTest_df['signal'] = 0
  backTest_df['pSignal'] = np.nan
  backTest_df['nSignal'] = np.nan
  signal = 0

  for index, row in backTest_df.iterrows():
    pxRatio = row['ratio']

    if pxRatio > params['shortA_longB_ratio']:
      signal = 1

    elif pxRatio < params['longA_shortB_ratio']:
      signal = -1

    else:
      if signal == 1 and pxRatio > params['avgPxRatio']:
        signal = 1

      elif signal == -1 and pxRatio < params['avgPxRatio']: 
        signal = -1

      else:
        signal = 0

    backTest_df.loc[index, 'signal'] = signal

    # pSignal and nSignal is for displaying the plot marker
    if signal == 1:
      backTest_df.loc[index, 'pSignal'] = pxRatio

    elif signal == -1:
      backTest_df.loc[index, 'nSignal'] = pxRatio

  return backTest_df


# PnL related
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


def calcPnl(backTest_df, params):
  backTest_df[['longPos', 'shortPos', 'longValue', 'shortValue', 'longPnl', 'shortPnl', 'pnl', 'totalPnl']] = 0
  signal, longPos, shortPos, longValue, shortValue, longPnl, shortPnl, pnl, accumPnl, totalPnl = 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0

  for index, row in backTest_df.iterrows():
    currentSignal = row['signal']

    if currentSignal != signal:
      if currentSignal == 0:
        longValue = 0
        shortValue = 0

      else:      
        longValue = params['dollarValue']
        shortValue = params['dollarValue']

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

  return backTest_df


# back test the result in "Test period"
def backTest(testStocks, params):
  cols = [params['PAIR_STOCK_A'], params['PAIR_STOCK_B']]
  backTest_df = testStocks[cols].copy()

  # Remove the NaN rows
  backTest_df.dropna(inplace = True)

  backTest_df = addSignal(backTest_df, params)
  backTest_df = calcPnl(backTest_df, params)

  return backTest_df
