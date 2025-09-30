from bokeh.io import output_notebook
output_notebook()
import yfinance as yf
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA
import plotly.graph_objects as go
from plotly.subplots import make_subplots


#Indicators#

#EXPONENTIAL MOVING AVERAGE#
def EMA(series, span):
    return pd.Series(series).ewm(span=span, adjust=False).mean()

#RELATIVE STRENGTH INDEX#
def RSI(series, period=5):
    series = pd.Series(series)
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    gain = pd.Series(gain, index=series.index)
    loss = pd.Series(loss, index=series.index)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50).values

#AVERAGE TRUE RANGE for a stop loss#
def ATR(high, low, close, period=14):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

#Strategy#
class EMA_RSI_ATR(Strategy):
    fast_ema_period = 5
    slow_ema_period = 13
    rsi_period = 5
    atr_period = 14
    atr_multiplier = 1.2 

    def init(self):
        close = self.data.Close
        self.ema_fast = self.I(EMA, close, self.fast_ema_period)
        self.ema_slow = self.I(EMA, close, self.slow_ema_period)
        self.rsi = self.I(RSI, close, self.rsi_period)
        self.atr = self.I(ATR, self.data.High, self.data.Low, close, self.atr_period)
        self.entry_price = None

    def next(self):
        if np.isnan(self.ema_fast[-1]) or np.isnan(self.ema_slow[-1]):
            return

        #Entry signals#
        if not self.position:
            if self.ema_fast[-1] > self.ema_slow[-1] and self.rsi[-1] < 30:
                self.buy(size=0.05)
                self.entry_price = self.data.Close[-1]
            elif self.ema_fast[-1] < self.ema_slow[-1] and self.rsi[-1] > 70:
                self.sell(size=0.05)
                self.entry_price = self.data.Close[-1]

        #ATR stop-loss exit#
        if self.position and self.entry_price is not None:
            if self.position.is_long:
                if self.data.Close[-1] < self.entry_price - self.atr_multiplier * self.atr[-1]:
                    self.position.close()
                    self.entry_price = None
            else:
                if self.data.Close[-1] > self.entry_price + self.atr_multiplier * self.atr[-1]:
                    self.position.close()
                    self.entry_price = None
                  
#INPUT#
ticker = yf.Ticker(input('enter the ticker'))
price_data =ticker.history(period = '10d', interval = '15m') 

#OUTPUT#
backtest = Backtest(price_data, EMA_RSI_ATR, cash=10000, commission=0.001, exclusive_orders=True)
results = backtest.run()
print(results)
backtest.plot()
