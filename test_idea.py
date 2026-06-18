import yfinance as yf

data = yf.download(
    "IDEA.NS",
    period="1mo",
    progress=False
)

print(data.tail())