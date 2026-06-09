import sys
from src.data.yfinance_handler import YahooFinanceDataHandler
from src.strategies.ma_crossover import ma_crossover_signals

# Redireciona saída para garantir que funcione
sys.stdout.reconfigure(encoding='utf-8')

dh = YahooFinanceDataHandler(auto_adjust=True)
df = dh.fetch_ohlc("AAPL", start="2019-01-01", end="2024-01-01")

out = ma_crossover_signals(df, short_window=50, long_window=200)

print(out[["close","ma_short","ma_long","signal","trade"]].tail(10))
print("Trades:", (out["trade"] != 0).sum())

