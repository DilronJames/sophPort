"""Moving-average crossover backtester, core engine.

Designed to be used three ways:
1. From the command line:        python backtest.py AAPL 2020-01-01 2024-01-01 10000
2. Imported from the Flask app:  from backtest import run, BacktestResult
3. Imported anywhere else:       backtest.run(...)

No GUI is touched on import, matplotlib's backend is only chosen when
`plot_results` or `render_chart_png` is called, so this module is safe to
import inside a web server.
"""

from __future__ import annotations

import argparse
import io
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

TRADING_DAYS = 252
RISK_FREE_ANNUAL = 0.04  # treasury-ish; used for Sharpe


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    """Everything produced by a backtest run.

    Holds both the time-series (prices, equity curves, trade log) and the
    scalar performance metrics. `to_dict` returns a JSON-friendly view for
    rendering in a template.
    """

    ticker: str
    start: str
    end: str
    starting_capital: float
    short_window: int
    long_window: int

    prices: pd.DataFrame
    equity: pd.Series
    buy_hold_equity: pd.Series
    trades: pd.DataFrame

    # strategy metrics
    final_value: float = 0.0
    total_return: float = 0.0
    cagr: float = 0.0
    volatility: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    exposure: float = 0.0

    # buy-and-hold metrics
    bh_final_value: float = 0.0
    bh_total_return: float = 0.0
    bh_cagr: float = 0.0
    bh_volatility: float = 0.0
    bh_sharpe: float = 0.0
    bh_max_drawdown: float = 0.0

    # trade stats
    num_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    profit_factor: float = 0.0

    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Flat dict of scalar metrics + a few formatted strings for templates."""
        def pct(x: float) -> str:
            return f"{x * 100:.2f}%"

        def money(x: float) -> str:
            return f"${x:,.2f}"

        trades_view = []
        for _, row in self.trades.iterrows():
            trades_view.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "side": row["side"],
                "price": float(row["price"]),
                "pnl": None if pd.isna(row["pnl"]) else float(row["pnl"]),
            })

        return {
            "ticker": self.ticker,
            "start": self.start,
            "end": self.end,
            "short_window": self.short_window,
            "long_window": self.long_window,
            "starting_capital": self.starting_capital,
            "starting_capital_fmt": money(self.starting_capital),

            "strategy": {
                "final_value": self.final_value,
                "final_value_fmt": money(self.final_value),
                "total_return": self.total_return,
                "total_return_fmt": pct(self.total_return),
                "cagr": self.cagr,
                "cagr_fmt": pct(self.cagr),
                "volatility": self.volatility,
                "volatility_fmt": pct(self.volatility),
                "sharpe": self.sharpe,
                "sharpe_fmt": f"{self.sharpe:.2f}",
                "sortino": self.sortino,
                "sortino_fmt": f"{self.sortino:.2f}",
                "max_drawdown": self.max_drawdown,
                "max_drawdown_fmt": pct(self.max_drawdown),
                "exposure": self.exposure,
                "exposure_fmt": pct(self.exposure),
            },
            "buy_hold": {
                "final_value": self.bh_final_value,
                "final_value_fmt": money(self.bh_final_value),
                "total_return": self.bh_total_return,
                "total_return_fmt": pct(self.bh_total_return),
                "cagr": self.bh_cagr,
                "cagr_fmt": pct(self.bh_cagr),
                "volatility": self.bh_volatility,
                "volatility_fmt": pct(self.bh_volatility),
                "sharpe": self.bh_sharpe,
                "sharpe_fmt": f"{self.bh_sharpe:.2f}",
                "max_drawdown": self.bh_max_drawdown,
                "max_drawdown_fmt": pct(self.bh_max_drawdown),
            },
            "trade_stats": {
                "num_trades": self.num_trades,
                "win_rate": self.win_rate,
                "win_rate_fmt": pct(self.win_rate),
                "avg_win_fmt": pct(self.avg_win),
                "avg_loss_fmt": pct(self.avg_loss),
                "best_trade_fmt": pct(self.best_trade),
                "worst_trade_fmt": pct(self.worst_trade),
                "profit_factor": self.profit_factor,
                "profit_factor_fmt": (
                    "∞" if math.isinf(self.profit_factor) else f"{self.profit_factor:.2f}"
                ),
            },
            "trades": trades_view,
            "warnings": self.warnings,
            "outperformed": self.total_return > self.bh_total_return,
            "outperformance": self.total_return - self.bh_total_return,
            "outperformance_fmt": pct(self.total_return - self.bh_total_return),
            "plain": plain_summary(self),
        }


# ---------------------------------------------------------------------------
# Data + signals
# ---------------------------------------------------------------------------

def fetch_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download split/dividend-adjusted OHLCV from Yahoo Finance.

    Raises ValueError on any failure path (bad ticker, no rows, network error).
    """
    if not ticker or not ticker.strip():
        raise ValueError("Ticker symbol is required.")
    try:
        _validate_date(start, "start")
        _validate_date(end, "end")
    except ValueError:
        raise

    try:
        df = yf.download(
            ticker, start=start, end=end,
            progress=False, auto_adjust=True, threads=False,
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch '{ticker}': {e}") from e

    if df is None or df.empty:
        raise ValueError(
            f"No data returned for '{ticker}' between {start} and {end}. "
            "Check the symbol and that the date range covers trading days."
        )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if df.empty:
        raise ValueError(f"No usable price rows for '{ticker}'.")
    return df


def _validate_date(s: str, label: str) -> None:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValueError(f"{label} date must be YYYY-MM-DD, got: {s!r}")


def add_signals(df: pd.DataFrame, short_window: int, long_window: int) -> pd.DataFrame:
    """Attach short MA, long MA, position (0/1) and signal (+1/-1) columns.

    Long when short MA > long MA, flat otherwise. Signals come from position
    changes; the simulator executes them on the *next* bar's open.
    """
    if short_window < 2 or long_window < 2:
        raise ValueError("Moving-average windows must be at least 2.")
    if short_window >= long_window:
        raise ValueError(
            f"Short window ({short_window}) must be less than long window ({long_window})."
        )
    if long_window >= len(df):
        raise ValueError(
            f"Long window ({long_window}) is >= the {len(df)} trading days in this "
            f"range. Widen the date range or shrink the window."
        )

    out = df.copy()
    out["SMA_short"] = out["Close"].rolling(short_window).mean()
    out["SMA_long"] = out["Close"].rolling(long_window).mean()
    out["Position"] = (out["SMA_short"] > out["SMA_long"]).astype(int)
    out.loc[out["SMA_long"].isna(), "Position"] = 0
    out["Signal"] = out["Position"].diff().fillna(0).astype(int)
    return out


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def _simulate(
    df: pd.DataFrame, starting_capital: float
) -> tuple[pd.Series, pd.Series, pd.DataFrame, pd.Series]:
    """Run the all-in / all-out simulation.

    Trades fire at the open of the bar *after* the crossover (no lookahead).
    Returns (equity_curve, buy_hold_curve, trade_log, in_market_flag).
    """
    cash = starting_capital
    shares = 0.0
    equity = np.empty(len(df))
    in_market = np.zeros(len(df), dtype=bool)
    trade_log: list[dict[str, Any]] = []
    entry_price: float | None = None

    closes = df["Close"].to_numpy()
    opens = df["Open"].to_numpy()
    signals = df["Signal"].to_numpy()
    dates = df.index

    pending = 0  # +1 buy, -1 sell, executed at next bar's open

    for i in range(len(df)):
        if pending == 1 and shares == 0 and cash > 0:
            price = float(opens[i])
            shares = cash / price
            cash = 0.0
            entry_price = price
            trade_log.append({"date": dates[i], "side": "BUY",
                              "price": price, "pnl": np.nan})
        elif pending == -1 and shares > 0:
            price = float(opens[i])
            pnl = (price - entry_price) / entry_price if entry_price else 0.0
            cash = shares * price
            shares = 0.0
            entry_price = None
            trade_log.append({"date": dates[i], "side": "SELL",
                              "price": price, "pnl": pnl})
        pending = 0

        equity[i] = cash + shares * float(closes[i])
        in_market[i] = shares > 0

        if signals[i] == 1:
            pending = 1
        elif signals[i] == -1:
            pending = -1

    equity_curve = pd.Series(equity, index=df.index, name="Strategy")
    bh_shares = starting_capital / float(closes[0])
    bh_curve = pd.Series(bh_shares * closes, index=df.index, name="BuyHold")
    trades_df = pd.DataFrame(trade_log,
                             columns=["date", "side", "price", "pnl"])
    in_market_series = pd.Series(in_market, index=df.index, name="InMarket")
    return equity_curve, bh_curve, trades_df, in_market_series


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough drop as a negative fraction (e.g. -0.23)."""
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    return float(dd.min())


def _drawdown_series(equity: pd.Series) -> pd.Series:
    return (equity - equity.cummax()) / equity.cummax()


def _annualized(returns: pd.Series) -> tuple[float, float, float, float]:
    """Return (CAGR, ann_vol, Sharpe, Sortino) for a daily returns series."""
    if len(returns) < 2:
        return 0.0, 0.0, 0.0, 0.0
    mean = returns.mean() * TRADING_DAYS
    vol = returns.std(ddof=1) * math.sqrt(TRADING_DAYS)
    excess = mean - RISK_FREE_ANNUAL
    sharpe = excess / vol if vol > 0 else 0.0
    downside = returns[returns < 0]
    dvol = downside.std(ddof=1) * math.sqrt(TRADING_DAYS) if len(downside) > 1 else 0.0
    sortino = excess / dvol if dvol > 0 else 0.0
    return mean, vol, sharpe, sortino


def _cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1


# ---------------------------------------------------------------------------
# Plain-English narrative (no jargon)
# ---------------------------------------------------------------------------

def plain_summary(r: "BacktestResult") -> dict[str, str]:
    """Return a dict of short plain-English strings for non-finance users.

    Describes what happened in normal language, no CAGR, Sharpe, etc.
    """
    ticker = r.ticker
    n_trades = r.num_trades

    # Market condition label from buy-hold return
    bh = r.bh_total_return
    if bh > 0.20:
        market = "a strong bull run"
    elif bh > 0.05:
        market = "a gradual uptrend"
    elif bh > -0.05:
        market = "a choppy, sideways market"
    elif bh > -0.15:
        market = "a mild downturn"
    else:
        market = "a significant bear market"

    # What the strategy did vs just holding
    strat_ret = r.total_return
    bh_ret = r.bh_total_return
    if strat_ret >= bh_ret:
        vs_bh = (
            f"That beat simply holding {ticker}, which returned "
            f"{bh_ret * 100:+.1f}% over the same period."
        )
        verdict = "Beat the market"
        verdict_detail = (
            f"The strategy outperformed buy-and-hold by "
            f"{(strat_ret - bh_ret) * 100:.1f} percentage points."
        )
    else:
        gap = (bh_ret - strat_ret) * 100
        vs_bh = (
            f"Just holding {ticker} the whole time would have done "
            f"{bh_ret * 100:+.1f}%, which is {gap:.1f} points more."
        )
        verdict = "Trailed the market"
        verdict_detail = (
            f"Buy-and-hold outperformed the strategy by "
            f"{gap:.1f} percentage points. The strategy spent time in cash "
            f"that cost returns."
        )

    # Trade activity
    if n_trades == 0:
        activity = f"The strategy never triggered a buy/sell signal during this period."
    elif n_trades == 1:
        activity = f"It made just 1 trade."
    else:
        activity = (
            f"It made {n_trades} round-trip trade{'s' if n_trades != 1 else ''} and was "
            f"invested about {r.exposure * 100:.0f}% of the time, "
            f"sitting in cash the other {(1 - r.exposure) * 100:.0f}%."
        )

    # Worst moment in plain dollars
    worst_dollar = abs(r.max_drawdown) * r.starting_capital
    worst_pct = abs(r.max_drawdown) * 100
    worst_str = (
        f"At its worst point, the portfolio was down ${worst_dollar:,.0f} "
        f"({worst_pct:.1f}%) from its peak."
    )

    # One-line return statement
    final = r.final_value
    start_cap = r.starting_capital
    change = final - start_cap
    sign = "+" if change >= 0 else "-"
    headline = (
        f"Your ${start_cap:,.0f} became ${final:,.0f} "
        f"({sign}${abs(change):,.0f}) using the "
        f"{r.short_window}/{r.long_window}-day MA strategy on {ticker}."
    )

    narrative = (
        f"During this period {ticker} was in {market}. "
        f"{activity} "
        f"{worst_str} "
        f"{vs_bh}"
    )

    return {
        "headline": headline,
        "narrative": narrative,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "won": strat_ret >= bh_ret,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    ticker: str,
    start: str,
    end: str,
    starting_capital: float,
    short_window: int = 20,
    long_window: int = 50,
) -> BacktestResult:
    """End-to-end backtest: fetch, signal, simulate, score.

    Raises ValueError for any invalid input or empty data.
    """
    ticker = ticker.strip().upper()
    if starting_capital <= 0:
        raise ValueError("Starting capital must be positive.")

    df = fetch_data(ticker, start, end)
    df = add_signals(df, short_window, long_window)
    equity, bh, trades, in_market = _simulate(df, starting_capital)

    daily = equity.pct_change().dropna()
    bh_daily = bh.pct_change().dropna()
    cagr, vol, sharpe, sortino = _annualized(daily)
    bh_cagr, bh_vol, bh_sharpe, _ = _annualized(bh_daily)

    sells = trades[trades["side"] == "SELL"]
    num_trades = int(len(sells))
    if num_trades > 0:
        wins = sells.loc[sells["pnl"] > 0, "pnl"]
        losses = sells.loc[sells["pnl"] <= 0, "pnl"]
        win_rate = float(len(wins) / num_trades)
        avg_win = float(wins.mean()) if not wins.empty else 0.0
        avg_loss = float(losses.mean()) if not losses.empty else 0.0
        best = float(sells["pnl"].max())
        worst = float(sells["pnl"].min())
        gross_win = float(wins.sum())
        gross_loss = float(-losses.sum())
        if gross_loss > 0:
            profit_factor = gross_win / gross_loss
        else:
            profit_factor = math.inf if gross_win > 0 else 0.0
    else:
        win_rate = avg_win = avg_loss = best = worst = 0.0
        profit_factor = 0.0

    warnings: list[str] = []
    if num_trades == 0:
        warnings.append(
            "No completed round-trip trades in this window. "
            "The strategy never sold what it bought."
        )
    if (df["Position"].sum() == 0):
        warnings.append("Strategy was never in the market (no crossovers triggered).")

    result = BacktestResult(
        ticker=ticker,
        start=start,
        end=end,
        starting_capital=starting_capital,
        short_window=short_window,
        long_window=long_window,
        prices=df,
        equity=equity,
        buy_hold_equity=bh,
        trades=trades,
        final_value=float(equity.iloc[-1]),
        total_return=float(equity.iloc[-1] / starting_capital - 1),
        cagr=cagr,
        volatility=vol,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=_max_drawdown(equity),
        exposure=float(in_market.mean()),
        bh_final_value=float(bh.iloc[-1]),
        bh_total_return=float(bh.iloc[-1] / starting_capital - 1),
        bh_cagr=bh_cagr,
        bh_volatility=bh_vol,
        bh_sharpe=bh_sharpe,
        bh_max_drawdown=_max_drawdown(bh),
        num_trades=num_trades,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        best_trade=best,
        worst_trade=worst,
        profit_factor=profit_factor,
        warnings=warnings,
    )
    return result


# ---------------------------------------------------------------------------
# Plotting (lazy import so server-side use stays headless-safe)
# ---------------------------------------------------------------------------

def _make_figure(result: BacktestResult, theme: str = "light"):
    """Build a three-panel matplotlib figure: price+MAs, equity, drawdown."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    if theme == "dark":
        bg = "#0c0c0c"; panel = "#111111"; ink = "#f5f5f5"
        grid = "#1f1f1f"; muted = "#707070"
        color_close = "#f5f5f5"; color_short = "#22c55e"; color_long = "#a3a3a3"
        color_strat = "#16ff65"; color_bh = "#525252"; color_dd = "#ef4444"
    else:
        bg = "#fafaf9"; panel = "#ffffff"; ink = "#0a0a0a"
        grid = "#e7e5e4"; muted = "#737373"
        color_close = "#0a0a0a"; color_short = "#16a34a"; color_long = "#737373"
        color_strat = "#15803d"; color_bh = "#a8a29e"; color_dd = "#ef4444"

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.edgecolor": grid,
        "axes.labelcolor": ink,
        "xtick.color": muted, "ytick.color": muted,
        "text.color": ink,
    })

    fig, axes = plt.subplots(
        3, 1, figsize=(11, 9.5),
        gridspec_kw={"height_ratios": [3, 2, 1.2]},
        sharex=True,
    )
    fig.patch.set_facecolor(bg)

    df = result.prices
    trades = result.trades
    buys = trades[trades["side"] == "BUY"]
    sells = trades[trades["side"] == "SELL"]

    # --- Panel 1: price + MAs + trades
    ax1 = axes[0]
    ax1.set_facecolor(panel)
    ax1.plot(df.index, df["Close"], color=color_close, linewidth=1.3, label="Close")
    ax1.plot(df.index, df["SMA_short"], color=color_short, linewidth=1.4,
             label=f"SMA {result.short_window}")
    ax1.plot(df.index, df["SMA_long"], color=color_long, linewidth=1.4,
             label=f"SMA {result.long_window}")
    if not buys.empty:
        ax1.scatter(buys["date"], buys["price"], marker="^", s=110,
                    color="#16a34a", edgecolor="white", linewidth=0.8,
                    label="Buy", zorder=6)
    if not sells.empty:
        ax1.scatter(sells["date"], sells["price"], marker="v", s=110,
                    color="#dc2626", edgecolor="white", linewidth=0.8,
                    label="Sell", zorder=6)
    ax1.set_title(
        f"{result.ticker}  ·  SMA({result.short_window}/{result.long_window})  "
        f"·  {result.start} → {result.end}",
        fontsize=14, fontweight="bold", color=ink, loc="left", pad=12,
    )
    ax1.set_ylabel("Price ($)")
    ax1.grid(color=grid, alpha=0.6, linewidth=0.6)
    ax1.legend(loc="upper left", frameon=False, fontsize=9)

    # --- Panel 2: equity curves
    ax2 = axes[1]
    ax2.set_facecolor(panel)
    ax2.plot(result.equity.index, result.equity, color=color_strat,
             linewidth=1.8, label="Strategy")
    ax2.plot(result.buy_hold_equity.index, result.buy_hold_equity,
             color=color_bh, linewidth=1.6, linestyle="--", label="Buy & Hold")
    ax2.axhline(result.starting_capital, color=muted, linewidth=0.7, alpha=0.5)
    ax2.set_ylabel("Portfolio ($)")
    ax2.grid(color=grid, alpha=0.6, linewidth=0.6)
    ax2.legend(loc="upper left", frameon=False, fontsize=9)

    # --- Panel 3: drawdown
    ax3 = axes[2]
    ax3.set_facecolor(panel)
    dd = _drawdown_series(result.equity) * 100
    ax3.fill_between(dd.index, dd.values, 0, color=color_dd, alpha=0.35,
                     linewidth=0)
    ax3.plot(dd.index, dd.values, color=color_dd, linewidth=1.0)
    ax3.set_ylabel("Drawdown (%)")
    ax3.set_xlabel("Date")
    ax3.grid(color=grid, alpha=0.6, linewidth=0.6)
    ax3.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax3.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax3.xaxis.get_major_locator()))

    for ax in axes:
        for spine in ax.spines.values():
            spine.set_color(grid)

    fig.tight_layout()
    return fig


def plot_results(result: BacktestResult, theme: str = "light") -> None:
    """Render the figure to a window (CLI use)."""
    import matplotlib
    matplotlib.use("TkAgg") if matplotlib.get_backend().lower().startswith("agg") else None
    import matplotlib.pyplot as plt
    fig = _make_figure(result, theme=theme)
    plt.show()


def render_chart_png(result: BacktestResult, theme: str = "light") -> bytes:
    """Return the chart as PNG bytes, used by the Flask integration."""
    import matplotlib.pyplot as plt
    fig = _make_figure(result, theme=theme)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_summary(result: BacktestResult) -> None:
    """Pretty-print a side-by-side strategy vs. buy-and-hold table."""
    d = result.to_dict()
    s = d["strategy"]; b = d["buy_hold"]; t = d["trade_stats"]

    line = "=" * 64
    thin = "-" * 64
    print(line)
    print(f"  Backtest  |  {result.ticker}  |  "
          f"{result.start} -> {result.end}")
    print(f"  SMA({result.short_window}/{result.long_window})  "
          f"|  starting capital {d['starting_capital_fmt']}")
    print(line)
    print(f"  {'':<22}{'STRATEGY':>20}{'BUY & HOLD':>20}")
    print(thin)
    row = lambda label, a, b: print(f"  {label:<22}{a:>20}{b:>20}")
    row("Final value",      s["final_value_fmt"],  b["final_value_fmt"])
    row("Total return",     s["total_return_fmt"], b["total_return_fmt"])
    row("CAGR",             s["cagr_fmt"],         b["cagr_fmt"])
    row("Annualized vol",   s["volatility_fmt"],   b["volatility_fmt"])
    row("Sharpe ratio",     s["sharpe_fmt"],       b["sharpe_fmt"])
    row("Sortino ratio",    s["sortino_fmt"],      "-")
    row("Max drawdown",     s["max_drawdown_fmt"], b["max_drawdown_fmt"])
    row("Time in market",   s["exposure_fmt"],     "100.00%")
    print(thin)
    print(f"  Completed trades        : {t['num_trades']}")
    print(f"  Win rate                : {t['win_rate_fmt']}")
    print(f"  Avg win / Avg loss      : {t['avg_win_fmt']} / {t['avg_loss_fmt']}")
    print(f"  Best / Worst trade      : {t['best_trade_fmt']} / {t['worst_trade_fmt']}")
    print(f"  Profit factor           : {t['profit_factor_fmt']}")
    print(line)
    verdict = "Strategy OUTPERFORMED" if d["outperformed"] else "Strategy UNDERPERFORMED"
    print(f"  {verdict} buy-and-hold by {d['outperformance_fmt']}")
    print(line)
    for w in result.warnings:
        print(f"  ! {w}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MA crossover backtester")
    p.add_argument("ticker", help="Stock ticker, e.g. AAPL")
    p.add_argument("start", help="Start date YYYY-MM-DD")
    p.add_argument("end", help="End date YYYY-MM-DD")
    p.add_argument("capital", type=float, help="Starting capital, e.g. 10000")
    p.add_argument("--short", type=int, default=20, help="Short MA window (default 20)")
    p.add_argument("--long", type=int, default=50, help="Long MA window (default 50)")
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--no-plot", action="store_true", help="Skip the matplotlib charts")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        result = run(
            args.ticker, args.start, args.end, args.capital,
            short_window=args.short, long_window=args.long,
        )
    except ValueError as e:
        print(f"Error: {e}")
        return

    print_summary(result)
    if not args.no_plot:
        plot_results(result, theme=args.theme)


if __name__ == "__main__":
    main()
