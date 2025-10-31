import pandas as pd

df = pd.read_csv("/Users/Aarya/Downloads/form4_data_fixed.csv")
print(df.shape)
print(df.head())
print(df.isna().sum())