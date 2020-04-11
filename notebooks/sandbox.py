# coding: utf-8

import sys; sys.path.insert(0, "src")
import matplotlib.pyplot as plt

import pandas as pd
import quantstats as qs

from pathlib import Path
from preprocess import (
    generate_cashflows,
    positions_raw_to_clean,
    positions_xls_to_df,
)
from api_methods import download_cashflows, download_positions, get_login_data
import datetime


qs.extend_pandas()
plt.style.use("ggplot")

ISIN_CASH = "LU1959429272"
CONFIG_DIR = "/Users/mmngreco/github/KikeM/degiro-wrapper/credentials"

user_data = get_login_data(config=CONFIG_DIR)
path = Path(r"./positions/").expanduser().absolute()
if not path.exists():
    path.mkdir()

# Descargamos el excel con la composición del portfolio de cada día laborable:
date_start = "20191001"
date_end = datetime.datetime.today()
calendar = pd.date_range(start=date_start, end=date_end, freq="B")
download_positions(
    calendar=calendar,
    path=path,
    data=user_data,
    filename_template="pos_%Y%m%d",
)
positions_raw_df = positions_xls_to_df(path, isin_cash=ISIN_CASH)
cleaned_data = positions_raw_to_clean(positions_raw_df)
amount_df, prices_df, shares_df, nav_df, rets_df = cleaned_data

# =============================================================================
# Cashflows

path_account = download_cashflows(user_data, date_start, date_end, path)
cashflows_df, cashflows_external_df = generate_cashflows(
    path_account=path_account, isin_cash=ISIN_CASH
)

# ??? : What means ss and why the following is needed
cashflows_ss = cashflows_df.drop(columns=ISIN_CASH).sum(axis=1)
cashflows_total_ss = (
        cashflows_external_df
        .set_index("date")["amount"]
        .reindex(cashflows_ss.index, fill_value=0.0)
        .add(cashflows_ss)
    )

# =============================================================================
# ### Compute cash returns

cash_calendar = cashflows_total_ss.index
for today, yesterday in zip(cash_calendar[1:], cash_calendar):
    cash_today = amount_df.loc[today, ISIN_CASH]
    cash_yesterday = amount_df.loc[yesterday, ISIN_CASH]

    flows = cashflows_total_ss.loc[today]

    rets_df.loc[today, ISIN_CASH] = (cash_today - flows) / cash_yesterday - 1

# =============================================================================
# Compute performance

weights_df = amount_df.div(amount_df.sum(axis=1), axis="index").shift(1)
weights_df = weights_df.rename(columns={ISIN_CASH: "Cash"})

weights_df.plot.area(title="Weights")
weights_df.tail(1).T[weights_df.index[-1]].plot.pie()
plt.show()

pf_returns_ss = (rets_df * weights_df).dropna(how="all").sum(axis=1)
pf_equity_ss = pf_returns_ss.add(1).cumprod().sub(1)
qs.reports.full(returns=pf_returns_ss, benchmark="^IBEX")