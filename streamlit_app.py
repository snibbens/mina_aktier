import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime, date, timedelta


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Aktieportfölj",
    page_icon="📈",
    layout="wide"
)

DB_FILE = "portfolio.db"


# ============================================================
# DATABASE
# ============================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            ticker TEXT,
            name TEXT,
            price REAL,
            shares REAL,
            amount REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            dividend_date TEXT,
            amount REAL,
            UNIQUE(ticker, dividend_date)
        )
    """)

    cur.execute(
        "SELECT COUNT(*) FROM account"
    )

    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO account (id, balance) VALUES (1, 0)"
        )

    conn.commit()
    conn.close()


init_db()


# ============================================================
# ACCOUNT
# ============================================================

def get_balance():

    conn = db()

    cur = conn.cursor()

    cur.execute(
        "SELECT balance FROM account WHERE id = 1"
    )

    result = cur.fetchone()

    conn.close()

    return float(result[0])


def change_balance(amount):

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE account
        SET balance = balance + ?
        WHERE id = 1
        """,
        (amount,)
    )

    conn.commit()
    conn.close()


# ============================================================
# TRANSACTIONS
# ============================================================

def add_transaction(
    ticker,
    name,
    price,
    shares,
    amount
):

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO transactions
        (date, ticker, name, price, shares, amount)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            ticker,
            name,
            price,
            shares,
            amount
        )
    )

    conn.commit()
    conn.close()


def get_transactions():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM transactions
        ORDER BY date ASC
        """,
        conn
    )

    conn.close()

    return df


# ============================================================
# DIVIDENDS
# ============================================================

def get_dividends():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM dividends
        """,
        conn
    )

    conn.close()

    return df


def save_dividend(
    ticker,
    dividend_date,
    amount
):

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO dividends
        (ticker, dividend_date, amount)
        VALUES (?, ?, ?)
        """,
        (
            ticker,
            dividend_date,
            amount
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# STOCK LIST
# ============================================================

SWEDISH_STOCKS = {

    "Volvo B":
        "VOLV-B.ST",

    "Volvo Car B":
        "VOLCAR-B.ST",

    "Investor B":
        "INVE-B.ST",

    "Atlas Copco A":
        "ATCO-A.ST",

    "Atlas Copco B":
        "ATCO-B.ST",

    "Evolution":
        "EVO.ST",

    "Ericsson B":
        "ERIC-B.ST",

    "H&M B":
        "HM-B.ST",

    "Sandvik":
        "SAND.ST",

    "Assa Abloy B":
        "ASSA-B.ST",

    "Swedbank A":
        "SWED-A.ST",

    "SEB A":
        "SEB-A.ST",

    "Nordea":
        "NDA-SE.ST",

    "Handelsbanken A":
        "SHB-A.ST",

    "Telia":
        "TELIA.ST",

    "Boliden":
        "BOL.ST",

    "SKF B":
        "SKF-B.ST",

    "SCA B":
        "SCA-B.ST",

    "Sinch":
        "SINCH.ST",

    "Hexagon B":
        "HEXA-B.ST",

    "Saab B":
        "SAAB-B.ST",

    "Tele2 B":
        "TEL2-B.ST",

    "Axfood":
        "AXFO.ST",

    "Apple":
        "AAPL",

    "Microsoft":
        "MSFT",

    "Tesla":
        "TSLA",

    "Nvidia":
        "NVDA",

    "Amazon":
        "AMZN",

    "Alphabet":
        "GOOGL",

    "Meta":
        "META",

}


# ============================================================
# STOCK SEARCH
# ============================================================

@st.cache_data(ttl=300)
def search_stocks(query):

    query = query.strip().lower()

    if not query:
        return []

    results = []

    # Svenska / manuellt definierade aktier
    for name, ticker in SWEDISH_STOCKS.items():

        if (
            query in name.lower()
            or query in ticker.lower()
        ):

            results.append({
                "name": name,
                "ticker": ticker,
                "exchange": (
                    "Stockholm"
                    if ticker.endswith(".ST")
                    else "NASDAQ / NYSE"
                ),
                "currency": (
                    "SEK"
                    if ticker.endswith(".ST")
                    else "USD"
                )
            })

    # Yahoo Finance search
    try:

        search = yf.Search(query)

        quotes = search.quotes

        for item in quotes:

            ticker = item.get("symbol")

            name = (
                item.get("longname")
                or item.get("shortname")
                or ticker
            )

            if not ticker:
                continue

            if any(
                x["ticker"] == ticker
                for x in results
            ):
                continue

            if ticker.endswith(".ST"):
                exchange = "Stockholm"
                currency = "SEK"

            elif ticker.endswith(".CO"):
                exchange = "Köpenhamn"
                currency = "DKK"

            elif ticker.endswith(".HE"):
                exchange = "Helsingfors"
                currency = "EUR"

            elif ticker.endswith(".OL"):
                exchange = "Oslo"
                currency = "NOK"

            elif ticker.endswith(".L"):
                exchange = "London"
                currency = "GBP"

            else:
                exchange = (
                    item.get("exchange")
                    or "Övrig börs"
                )

                currency = "USD"

            results.append({
                "name": name,
                "ticker": ticker,
                "exchange": exchange,
                "currency": currency
            })

    except Exception:
        pass

    return results[:20]


# ============================================================
# CURRENT PRICE
# ============================================================

@st.cache_data(ttl=60)
def get_price(ticker):

    try:

        stock = yf.Ticker(ticker)

        data = stock.history(
            period="2d",
            interval="1d"
        )

        if data.empty:
            return None

        close = data["Close"].dropna()

        if close.empty:
            return None

        return float(close.iloc[-1])

    except Exception:
        return None


# ============================================================
# PREVIOUS PRICE
# ============================================================

@st.cache_data(ttl=300)
def get_previous_price(ticker):

    try:

        stock = yf.Ticker(ticker)

        data = stock.history(
            period="5d",
            interval="1d"
        )

        close = data["Close"].dropna()

        if len(close) < 2:
            return None

        return float(close.iloc[-2])

    except Exception:
        return None


# ============================================================
# PORTFOLIO
# ============================================================

def create_portfolio():

    transactions = get_transactions()

    if transactions.empty:
        return pd.DataFrame()

    portfolio = []

    for ticker, group in transactions.groupby(
        "ticker"
    ):

        shares = group["shares"].sum()

        invested = group["amount"].sum()

        if shares <= 0:
            continue

        gav = invested / shares

        name = group["name"].iloc[-1]

        price = get_price(ticker)

        if price is not None:

            value = shares * price

            profit = value - invested

            profit_percent = (
                profit / invested * 100
                if invested > 0
                else 0
            )

        else:

            value = 0
            profit = 0
            profit_percent = 0

        portfolio.append({

            "Aktie": name,

            "Ticker": ticker,

            "Antal": shares,

            "GAV": gav,

            "Kurs": price,

            "Investerat": invested,

            "Värde": value,

            "Vinst/Förlust": profit,

            "Avkastning %": profit_percent

        })

    return pd.DataFrame(portfolio)


# ============================================================
# HISTORICAL PORTFOLIO
# ============================================================

def portfolio_history():

    transactions = get_transactions()

    if transactions.empty:
        return pd.DataFrame()

    transactions["date"] = pd.to_datetime(
        transactions["date"]
    )

    start = transactions["date"].min().date()

    end = date.today()

    dates = pd.date_range(
        start=start,
        end=end,
        freq="B"
    )

    tickers = transactions[
        "ticker"
    ].unique()

    rows = []

    for current_date in dates:

        value = 0

        for ticker in tickers:

            buys = transactions[
                (
                    transactions["ticker"] == ticker
                )
                &
                (
                    transactions["date"]
                    <= current_date
                )
            ]

            if buys.empty:
                continue

            shares = buys[
                "shares"
            ].sum()

            try:

                history = yf.Ticker(
                    ticker
                ).history(
                    start=(
                        current_date
                        - timedelta(days=7)
                    ).date(),
                    end=(
                        current_date
                        + timedelta(days=1)
                    ).date()
                )

                if history.empty:
                    continue

                price = float(
                    history["Close"]
                    .dropna()
                    .iloc[-1]
                )

                value += shares * price

            except Exception:
                pass

        rows.append({
            "Datum": current_date,
            "Portföljvärde": value
        })

    return pd.DataFrame(rows)


# ============================================================
# DIVIDENDS
# ============================================================

def check_dividends():

    transactions = get_transactions()

    if transactions.empty:
        return 0

    processed = get_dividends()

    total_new = 0

    for ticker in transactions[
        "ticker"
    ].unique():

        try:

            stock = yf.Ticker(ticker)

            dividends = stock.dividends

            if dividends.empty:
                continue

            for dividend_date, dividend in dividends.items():

                d = pd.Timestamp(
                    dividend_date
                ).date().isoformat()

                already = (
                    (
                        (processed["ticker"] == ticker)
                        &
                        (
                            processed[
                                "dividend_date"
                            ] == d
                        )
                    ).any()
                    if not processed.empty
                    else False
                )

                if already:
                    continue

                transaction_dates = pd.to_datetime(
                    transactions[
                        transactions["ticker"] == ticker
                    ]["date"]
                ).dt.date

                shares = transactions[
                    (
                        transactions["ticker"] == ticker
                    )
                    &
                    (
                        transaction_dates
                        <= pd.Timestamp(
                            dividend_date
                        ).date()
                    )
                ]["shares"].sum()

                if shares <= 0:
                    continue

                amount = (
                    shares
                    * float(dividend)
                )

                change_balance(amount)

                save_dividend(
                    ticker,
                    d,
                    amount
                )

                total_new += amount

        except Exception:
            continue

    return total_new


# ============================================================
# PROCESS DIVIDENDS
# ============================================================

new_dividends = check_dividends()


# ============================================================
# HEADER
# ============================================================

st.title("📈 Min Aktieportfölj")

st.write(
    "Sök efter aktier, välj själv hur mycket du vill investera "
    "och följ portföljens utveckling."
)


# ============================================================
# ACCOUNT SUMMARY
# ============================================================

portfolio = create_portfolio()

balance = get_balance()

if portfolio.empty:

    portfolio_value = 0
    invested_total = 0
    total_profit = 0

else:

    portfolio_value = portfolio[
        "Värde"
    ].sum()

    invested_total = portfolio[
        "Investerat"
    ].sum()

    total_profit = (
        portfolio_value
        - invested_total
    )

total_value = (
    balance
    + portfolio_value
)

if invested_total > 0:

    total_return = (
        total_profit
        / invested_total
        * 100
    )

else:

    total_return = 0


if new_dividends > 0:

    st.success(
        f"💰 Nya utdelningar: "
        f"{new_dividends:,.2f} kr"
    )


c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "💰 Kontanter",
        f"{balance:,.2f} kr"
    )

with c2:

    st.metric(
        "📊 Portfölj",
        f"{portfolio_value:,.2f} kr"
    )

with c3:

    st.metric(
        "💼 Totalt",
        f"{total_value:,.2f} kr"
    )

with c4:

    st.metric(
        "📈 Avkastning",
        f"{total_return:+.2f}%"
    )


# ============================================================
# DEPOSIT
# ============================================================

with st.sidebar:

    st.header("💰 Konto")

    st.metric(
        "Saldo",
        f"{get_balance():,.2f} kr"
    )

    st.divider()

    st.subheader(
        "Sätt in pengar"
    )

    deposit = st.number_input(
        "Belopp",
        min_value=1.0,
        value=10000.0,
        step=100.0
    )

    if st.button(
        "➕ Sätt in pengar",
        use_container_width=True
    ):

        change_balance(deposit)

        st.success(
            f"{deposit:,.2f} kr insatt."
        )

        st.rerun()


# ============================================================
# SEARCH
# ============================================================

st.divider()

st.header("🔎 Sök aktie")

query = st.text_input(
    "Sök",
    placeholder="T.ex. Volvo, Investor, Atlas Copco, Evolution...",
    label_visibility="collapsed"
)


if query:

    results = search_stocks(query)

    if results:

        st.write(
            f"**{len(results)} aktier hittades**"
        )

        for index, result in enumerate(
            results
        ):

            ticker = result["ticker"]

            name = result["name"]

            exchange = result["exchange"]

            currency = result["currency"]

            price = get_price(ticker)

            if "Volvo Car" in name:
                icon = "🚗"

            elif "Volvo" in name:
                icon = "🏢"

            elif "Investor" in name:
                icon = "🏦"

            elif "Atlas Copco" in name:
                icon = "🏭"

            else:
                icon = "📈"

            with st.container(
                border=True
            ):

                col1, col2, col3 = st.columns(
                    [4, 2, 1]
                )

                with col1:

                    st.subheader(
                        f"{icon} {name}"
                    )

                    st.caption(
                        f"{ticker} · {exchange}"
                    )

                with col2:

                    if price is not None:

                        st.metric(
                            "Aktuell kurs",
                            f"{price:,.2f} {currency}"
                        )

                    else:

                        st.write(
                            "Kurs saknas"
                        )

                with col3:

                    if st.button(
                        "Välj",
                        key=f"select_{ticker}_{index}"
                    ):

                        st.session_state[
                            "selected_ticker"
                        ] = ticker

                        st.session_state[
                            "selected_name"
                        ] = name

                        st.session_state[
                            "selected_exchange"
                        ] = exchange

                        st.session_state[
                            "selected_currency"
                        ] = currency

                        st.rerun()

    else:

        st.warning(
            "Ingen aktie hittades."
        )


# ============================================================
# BUY
# ============================================================

if "selected_ticker" in st.session_state:

    ticker = st.session_state[
        "selected_ticker"
    ]

    name = st.session_state[
        "selected_name"
    ]

    exchange = st.session_state[
        "selected_exchange"
    ]

    currency = st.session_state[
        "selected_currency"
    ]

    price = get_price(ticker)

    st.divider()

    st.header(
        f"🛒 Köp {name}"
    )

    st.caption(
        f"{ticker} · {exchange}"
    )

    if price is not None:

        st.metric(
            "Aktuell kurs",
            f"{price:,.2f} {currency}"
        )

        amount = st.number_input(
            "💵 Hur mycket vill du investera?",
            min_value=1.0,
            value=1000.0,
            step=100.0
        )

        shares = amount / price

        st.info(
            f"Du investerar **{amount:,.2f} kr** "
            f"och får ungefär **{shares:.4f} aktier**."
        )

        balance_now = get_balance()

        if amount > balance_now:

            st.error(
                f"Du har bara "
                f"{balance_now:,.2f} kr."
            )

        else:

            if st.button(
                "🚀 Köp aktie",
                type="primary",
                use_container_width=True
            ):

                change_balance(
                    -amount
                )

                add_transaction(
                    ticker=ticker,
                    name=name,
                    price=price,
                    shares=shares,
                    amount=amount
                )

                st.success(
                    f"🎉 Du köpte "
                    f"{shares:.4f} aktier i "
                    f"{name} för "
                    f"{amount:,.2f} kr."
                )

                for key in [
                    "selected_ticker",
                    "selected_name",
                    "selected_exchange",
                    "selected_currency"
                ]:

                    if key in st.session_state:
                        del st.session_state[key]

                st.rerun()

    else:

        st.error(
            "Kunde inte hämta aktiekursen."
        )


# ============================================================
# PORTFOLIO
# ============================================================

st.divider()

st.header("📊 Min portfölj")

if portfolio.empty:

    st.info(
        "Du har inte köpt några aktier ännu."
    )

else:

    st.dataframe(
        portfolio,
        use_container_width=True,
        hide_index=True,
        column_config={

            "Antal":
                st.column_config.NumberColumn(
                    format="%.4f"
                ),

            "GAV":
                st.column_config.NumberColumn(
                    format="%.2f"
                ),

            "Kurs":
                st.column_config.NumberColumn(
                    format="%.2f"
                ),

            "Investerat":
                st.column_config.NumberColumn(
                    format="%.2f kr"
                ),

            "Värde":
                st.column_config.NumberColumn(
                    format="%.2f kr"
                ),

            "Vinst/Förlust":
                st.column_config.NumberColumn(
                    format="%.2f kr"
                ),

            "Avkastning %":
                st.column_config.NumberColumn(
                    format="%.2f %"
                )
        }
    )


# ============================================================
# TODAY'S PROFIT
# ============================================================

st.divider()

st.header("📅 Dagens vinst/förlust")

daily_profit = 0

if not portfolio.empty:

    for _, row in portfolio.iterrows():

        current = get_price(
            row["Ticker"]
        )

        previous = get_previous_price(
            row["Ticker"]
        )

        if (
            current is not None
            and previous is not None
        ):

            daily_profit += (
                current
                - previous
            ) * row["Antal"]


if daily_profit >= 0:

    st.success(
        f"📈 +{daily_profit:,.2f} kr idag"
    )

else:

    st.error(
        f"📉 {daily_profit:,.2f} kr idag"
    )


# ============================================================
# PIE CHART
# ============================================================

st.divider()

st.header("🥧 Portföljfördelning")

if not portfolio.empty:

    pie = portfolio[
        ["Aktie", "Värde"]
    ].copy()

    pie = pie[
        pie["Värde"] > 0
    ]

    if not pie.empty:

        fig = px.pie(
            pie,
            names="Aktie",
            values="Värde",
            hole=0.45
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# HISTORICAL GRAPH
# ============================================================

st.divider()

st.header("📈 Historiskt portföljvärde")

history = portfolio_history()

if not history.empty:

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=history["Datum"],
            y=history["Portföljvärde"],
            mode="lines",
            name="Portfölj"
        )
    )

    fig.update_layout(
        height=500,
        xaxis_title="Datum",
        yaxis_title="Värde (kr)",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.info(
        "Historiken visas efter ditt första köp."
    )


# ============================================================
# OMX COMPARISON
# ============================================================

st.divider()

st.header("🏆 Jämför med OMX")

if not history.empty:

    try:

        start_date = (
            history["Datum"]
            .min()
            .date()
        )

        omx = yf.Ticker(
            "^OMX"
        ).history(
            start=start_date,
            end=date.today()
            + timedelta(days=1)
        )

        if not omx.empty:

            omx_close = (
                omx["Close"]
                .dropna()
            )

            portfolio_start = (
                history[
                    "Portföljvärde"
                ].iloc[0]
            )

            if portfolio_start > 0:

                portfolio_index = (
                    history[
                        "Portföljvärde"
                    ]
                    / portfolio_start
                    * 100
                )

                omx_index = (
                    omx_close
                    / omx_close.iloc[0]
                    * 100
                )

                fig = go.Figure()

                fig.add_trace(
                    go.Scatter(
                        x=history["Datum"],
                        y=portfolio_index,
                        mode="lines",
                        name="Min portfölj"
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=omx_index.index,
                        y=omx_index.values,
                        mode="lines",
                        name="OMX"
                    )
                )

                fig.update_layout(
                    height=500,
                    yaxis_title="Index (start = 100)",
                    hovermode="x unified"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

    except Exception:

        st.warning(
            "Kunde inte hämta OMX-data."
        )


# ============================================================
# TRANSACTIONS
# ============================================================

st.divider()

st.header("📜 Transaktionshistorik")

transactions = get_transactions()

if transactions.empty:

    st.info(
        "Inga transaktioner ännu."
    )

else:

    display = transactions.copy()

    display["date"] = pd.to_datetime(
        display["date"]
    ).dt.strftime(
        "%Y-%m-%d %H:%M"
    )

    display.columns = [
        "ID",
        "Datum",
        "Ticker",
        "Aktie",
        "Pris",
        "Antal",
        "Belopp"
    ]

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "📈 Aktieportfölj · Aktiekurser via Yahoo Finance · "
    "Detta är en simulator och inte en riktig depå."
)
