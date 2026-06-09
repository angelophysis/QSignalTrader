from src.data.yfinance_handler import YahooFinanceDataHandler

print("Testando YahooFinanceDataHandler...")
print("=" * 70)

dh = YahooFinanceDataHandler(auto_adjust=True)
df = dh.fetch_ohlc("AAPL", start="2023-01-01", end="2023-03-01")

print(f"\nColunas: {list(df.columns)}")
print(f"Shape: {df.shape}")
print(f"Período: {df.index[0]} até {df.index[-1]}")

print("\n" + "=" * 70)
print("PRIMEIRAS 5 LINHAS:")
print("=" * 70)
for idx, row in df.head().iterrows():
    print(f"{idx.date()}: open={row['open']:.2f}, high={row['high']:.2f}, "
          f"low={row['low']:.2f}, close={row['close']:.2f}, volume={int(row['volume'])}")

print("\n" + "=" * 70)
print("ÚLTIMAS 5 LINHAS:")
print("=" * 70)
for idx, row in df.tail().iterrows():
    print(f"{idx.date()}: open={row['open']:.2f}, high={row['high']:.2f}, "
          f"low={row['low']:.2f}, close={row['close']:.2f}, volume={int(row['volume'])}")

print("\n" + "=" * 70)
print(f"✅ SUCESSO! Baixados {len(df)} dias de dados da AAPL")
print("=" * 70)
