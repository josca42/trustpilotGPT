import pandas as pd


def str2date(date_str):
    try:
        return pd.to_datetime(date_str).date()
    except:
        return None
