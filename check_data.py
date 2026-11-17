import pandas as pd
df = pd.read_csv("8891_motorcycles.csv")
print(df[["brand", "model", "price_twd", "year", "region"]].head())
