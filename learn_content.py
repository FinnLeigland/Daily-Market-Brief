"""Field guide content: modules of concepts, each with a one-liner, an explanation, an example, and where to see it."""

# Each concept: (name, one_line, body, example, where_in_dashboard)
MODULES = {
    "The basics": [
        (
            "What a stock is",
            "A share of ownership in a company, and a claim on a slice of its future profits.",
            "Owning one share of a company with 1 billion shares means you own one-billionth of it. Its price moves because "
            "investors constantly re-estimate what those future profits are worth today. Short term, prices react to news "
            "and sentiment. Long term, they tend to follow earnings.",
            "A company earning $10B a year with 1B shares makes $10 per share. If investors will pay 20× that, the stock "
            "trades near $200.",
            "Stock Lab: the header shows price, market cap and analyst targets.",
        ),
        (
            "How the market sets prices",
            "Every trade needs a buyer and a seller; the price is wherever they agree.",
            "Exchanges like the NYSE and Nasdaq match buy and sell orders. When more people want to buy than sell at the "
            "current price, buyers have to bid higher and the price rises. Good news doesn't move a stock by itself. It "
            "moves because it changes how much buyers are willing to pay.",
            "A company beats earnings, but the stock falls 5%. Investors expected an even bigger beat, so sellers "
            "outnumbered buyers at the old price.",
            "Stock Lab: click a labeled move on the price chart to see what pushed buyers or sellers.",
        ),
        (
            "Indexes",
            "A basket of stocks tracked as one number, used to measure 'the market'.",
            "The S&P 500 holds 500 large US companies, weighted by size, so giants like Apple and Nvidia move it most. "
            "The Nasdaq Composite is tech-heavy; the Dow tracks just 30 big companies; the Russell 2000 tracks small companies. "
            "When people say 'the market was up 1%', they usually mean the S&P 500.",
            "If Nvidia is 7% of the S&P 500 and rises 10%, it alone adds about 0.7% to the index.",
            "Digest: the pulse strip at the top.",
        ),
        (
            "ETFs and index funds",
            "Funds that hold a basket of stocks and trade like a single stock.",
            "Instead of buying 500 companies, you can buy one share of SPY and own a sliver of all of them. Sector ETFs "
            "like XLK (tech) or XLE (energy) hold one slice of the market. Fees are usually tiny, and you get instant "
            "diversification.",
            "XLK's biggest holdings are Nvidia, Apple and Microsoft, so XLK's moves are mostly their moves.",
            "Digest sector cards, Sector Rotation, and the peer groups in Stock Lab all use sector ETFs.",
        ),
        (
            "Market capitalization",
            "Share price × number of shares: what the whole company is worth to the market.",
            "Market cap, not share price, tells you how big a company is. A $50 stock can be a bigger company than a $500 "
            "stock if it has more shares. Large caps (over $10B) tend to be steadier; small caps swing more but can grow faster.",
            "10B shares × $50 = $500B market cap; 100M shares × $500 = $50B.",
            "Stock Lab: market cap in the header.",
        ),
        (
            "Sectors",
            "Groups of companies in similar businesses, which tend to move together.",
            "The market is split into 11 sectors (Technology, Financials, Energy, Health Care and so on). Companies in the "
            "same sector share drivers: banks care about interest rates, energy companies about oil prices. That's why "
            "comparing a stock to its own sector is more useful than comparing it to everything.",
            "When oil jumps 10%, Exxon and Chevron usually rise together, regardless of company-specific news.",
            "Sector Rotation and Macro step 4.",
        ),
    ],
    "Reading a company": [
        (
            "Revenue vs. earnings",
            "Revenue is what customers pay; earnings (profit) is what's left after every cost.",
            "Revenue is the top line; net income is the bottom line. A company can grow revenue quickly and still lose "
            "money if costs grow faster. Investors watch both: revenue growth shows demand, earnings show whether the "
            "business model works.",
            "$100B revenue − $60B costs − $15B operating expenses − $5B taxes and interest = $20B earnings.",
            "Stock Lab scorecard: revenue growth and earnings growth.",
        ),
        (
            "Margins",
            "The share of each revenue dollar a company keeps, at different stages.",
            "Gross margin is after the direct cost of making the product. Operating margin is after all running costs "
            "(staff, R&D, marketing). Net margin is after interest and taxes. High, stable margins usually signal pricing "
            "power: customers keep paying even when prices rise.",
            "A software company might have 80% gross margins; a grocery store might have 25%. Neither is 'bad'; "
            "they're different businesses. Compare within a sector.",
            "Stock Lab scorecard: profitability block and the operating-margin peer chart.",
        ),
        (
            "EPS (earnings per share)",
            "Net income divided by shares outstanding.",
            "EPS turns total profit into a per-share number you can compare with the share price. Analysts publish EPS "
            "estimates before every quarterly report; beating or missing them is what moves stocks on earnings day. "
            "Buybacks raise EPS by shrinking the share count, even if profit is flat.",
            "$20B profit ÷ 4B shares = $5.00 EPS. Analysts expected $4.80, so it's a 4% beat.",
            "Stock Lab: click an earnings label on the price chart to see EPS vs. the estimate.",
        ),
        (
            "Free cash flow",
            "Cash from operations minus what the company spends on equipment and buildings.",
            "Earnings include accounting choices; free cash flow is the actual cash the business throws off, which can "
            "be paid out as dividends, used for buybacks, or reinvested. Many investors trust it more than earnings.",
            "Operating cash flow of $30B minus $8B of capital spending = $22B of free cash flow.",
            "Analyst Desk → Trade Journal: the DCF and reverse DCF both start from free cash flow.",
        ),
        (
            "Debt and the balance sheet",
            "What a company owns, what it owes, and what's left for shareholders.",
            "Debt magnifies results: it boosts returns in good times and adds risk in bad ones, because interest has to "
            "be paid no matter what. Debt-to-equity compares borrowing to shareholder capital. Companies with lots of "
            "debt are more sensitive to rising interest rates.",
            "Debt/equity of 2× means the company has borrowed $2 for every $1 shareholders have put in.",
            "Stock Lab scorecard: the balance sheet and risk block.",
        ),
        (
            "Earnings season and guidance",
            "Each quarter, companies report results and often forecast the next quarter.",
            "The reported numbers matter, but guidance often matters more, because stock prices look forward. A company "
            "can beat this quarter and still fall if it lowers its outlook. Earnings season clusters in the weeks after "
            "each quarter ends.",
            "'Revenue beat, but full-year guidance was cut' → stock drops 8% the next morning.",
            "Stock Lab: earnings-labeled moves on the price chart.",
        ),
        (
            "Dividends and buybacks",
            "The two ways companies return cash to shareholders.",
            "A dividend pays cash per share, usually quarterly. A buyback uses cash to repurchase shares, so each "
            "remaining share owns more of the company. Mature companies (utilities, staples) lean on dividends; tech "
            "companies favor buybacks.",
            "A $2 annual dividend on a $50 stock is a 4% dividend yield.",
            "Stock Lab scorecard: dividend yield.",
        ),
    ],
    "Valuation": [
        (
            "P/E ratio",
            "Price ÷ earnings per share: how many dollars you pay for $1 of annual profit.",
            "The most common valuation yardstick. A higher P/E means investors expect faster growth or see the business "
            "as higher quality or safer. P/Es only mean something compared with peers, the company's own history, or "
            "the market (the S&P 500 has averaged roughly 15–20× over the long run).",
            "A $150 stock with $5 EPS trades at 30× earnings. If peers trade at 20×, you're paying a premium.",
            "Stock Lab scorecard and peer charts; Analyst Desk → Trade Journal's earnings × multiple method.",
        ),
        (
            "Trailing vs. forward P/E",
            "Trailing uses the last 12 months of earnings; forward uses analysts' estimates for the next 12.",
            "For fast-growing companies, forward P/E is often much lower than trailing because earnings are expected "
            "to rise. Forward numbers depend on forecasts that can be wrong.",
            "Trailing EPS $4, forward EPS $6, price $120: trailing P/E 30×, forward P/E 20×.",
            "Stock Lab scorecard: both P/Es side by side.",
        ),
        (
            "PEG ratio",
            "P/E divided by the expected growth rate.",
            "PEG tries to adjust valuation for growth. A PEG near 1 is often called 'fairly priced for its growth', below 1 "
            "potentially cheap, well above 1 expensive. It's a rough tool: growth estimates are guesses.",
            "P/E of 30 and 30% expected growth → PEG of 1.0. P/E of 30 and 10% growth → PEG of 3.0.",
            "Stock Lab scorecard.",
        ),
        (
            "Price-to-sales and EV/EBITDA",
            "Valuation measures for when earnings are small, negative, or distorted.",
            "Price-to-sales compares market value to revenue: useful for young companies that aren't profitable yet. "
            "EV/EBITDA uses enterprise value (market cap plus debt minus cash) against operating cash earnings, so it "
            "compares companies with different debt levels fairly.",
            "Market cap $90B + debt $20B − cash $10B = EV $100B. EBITDA $10B → EV/EBITDA 10×.",
            "Stock Lab scorecard: valuation block.",
        ),
        (
            "Discounted cash flow (DCF)",
            "A company is worth all its future cash, adjusted for the fact that later cash is worth less.",
            "A DCF projects free cash flow for years ahead, then 'discounts' each year back to today using a required "
            "return. Money in 10 years is worth less than money now because you could have invested it elsewhere. Small "
            "changes in the growth or discount rate swing the answer a lot, so treat a DCF as a range, not a number.",
            "$100 received in 10 years, discounted at 9% a year, is worth about $42 today.",
            "Analyst Desk → Trade Journal → Price target builder, method 2.",
        ),
        (
            "Reverse DCF",
            "Instead of guessing growth to get a value, take today's price and solve for the growth it implies.",
            "This flips valuation into a question you can actually reason about: 'what do I have to believe to own this "
            "stock?' If the price implies 20% growth for a decade and the company is growing 10%, the market is "
            "optimistic. If it implies 3% and the company grows 12%, the market may be too pessimistic.",
            "Costco at $923 implied ~19% a year of cash-flow growth vs. ~11% recent revenue growth: a high bar.",
            "Analyst Desk → Trade Journal → Price target builder → What's priced in?",
        ),
        (
            "Growth vs. value",
            "Two investing styles: paying up for fast growers, or buying solid businesses priced cheaply.",
            "Growth stocks have high P/Es because most of their value is expected far in the future, which makes them "
            "sensitive to interest rates. Value stocks trade at low multiples, often in mature or out-of-favor "
            "industries. Leadership rotates between the two over the cycle.",
            "In 2022, as rates jumped, many high-P/E tech stocks fell 50%+ while low-P/E energy stocks rose.",
            "Sector Rotation: risk-appetite line; Macro: interest rates.",
        ),
    ],
    "Trading mechanics": [
        (
            "Bid, ask and spread",
            "The bid is the highest price a buyer will pay; the ask is the lowest a seller will accept.",
            "The gap between them is the spread, a hidden cost every time you trade. Big, heavily traded stocks have "
            "spreads of a penny; small, thinly traded ones can be much wider.",
            "Bid $99.98, ask $100.02: buying and immediately selling would lose $0.04 a share.",
            "Not shown directly; liquidity shows up as trading volume in the move overview.",
        ),
        (
            "Market vs. limit orders",
            "A market order buys or sells now at whatever the price is; a limit order only trades at your price or better.",
            "Market orders guarantee the trade but not the price, which is risky in fast markets or thin stocks. Limit "
            "orders guarantee the price but not the trade: it may never fill.",
            "Limit buy at $95 on a $100 stock: it only fills if the price drops to $95.",
            "Your entry price in the Analyst Desk → Trade Journal is what you actually paid.",
        ),
        (
            "Stop-loss orders",
            "An order that sells automatically if the price falls to a level you set.",
            "Stops enforce discipline: you decide your exit before emotions get involved. A stop becomes a market order "
            "when triggered, so in a sudden gap down you can sell below your stop price.",
            "Bought at $100, stop at $88: you cap the planned loss at about 12%.",
            "Analyst Desk → Trade Journal: each position's stop, and the stop-to-target progress chart.",
        ),
        (
            "Short selling",
            "Borrowing shares and selling them, hoping to buy them back cheaper later.",
            "Shorting profits when a stock falls. The risk is asymmetric: a stock can only fall to zero, but it can rise "
            "without limit, so losses on a short are theoretically unlimited. Heavily shorted stocks can 'squeeze' upward "
            "when shorts rush to buy back.",
            "Short at $50, cover at $40 → $10 profit per share. Cover at $80 → $30 loss.",
            "Not tracked in the journal, which assumes long positions.",
        ),
        (
            "Margin and leverage",
            "Borrowing from your broker to buy more stock than your cash allows.",
            "Leverage magnifies gains and losses equally. If the account falls too far, the broker issues a margin call "
            "and can sell your positions at the worst time. Most long-term investors avoid it.",
            "$10k of your money + $10k borrowed: a 20% drop in the stock wipes out 40% of your money.",
            "Not used anywhere in the dashboard.",
        ),
        (
            "Volume and liquidity",
            "Volume is how many shares trade; liquidity is how easily you can trade without moving the price.",
            "Unusual volume on a big move signals conviction: large investors are acting on the news. A price move on "
            "light volume is easier to reverse.",
            "A stock that normally trades 10M shares a day trades 30M on earnings: 3× normal volume.",
            "Stock Lab: the move overview shows volume vs. its 50-day average.",
        ),
    ],
    "Risk and portfolios": [
        (
            "Volatility",
            "How much a price swings around, usually measured as the annualized standard deviation of returns.",
            "Higher volatility means a bumpier ride and a wider range of outcomes. The S&P 500's long-run volatility is "
            "around 15–20% a year; individual stocks are often 30–60%.",
            "A stock with 40% volatility has historically moved roughly ±40% in a typical year.",
            "Stock Lab: Risk vs. the market table.",
        ),
        (
            "Beta",
            "How much a stock tends to move when the market moves 1%.",
            "Beta of 1 moves with the market; 1.5 moves about 50% more; 0.5 about half as much. It measures market "
            "sensitivity, not total risk: a stock can have low beta but huge company-specific swings.",
            "Beta 1.8: on a day the S&P 500 falls 2%, the stock has typically fallen about 3.6%.",
            "Stock Lab risk table; Analyst Desk → Trade Journal: your portfolio's beta.",
        ),
        (
            "Drawdown",
            "The fall from a previous peak to a trough.",
            "Max drawdown is the worst loss an investor would have sat through. It matters because losses compound "
            "asymmetrically: a 50% loss needs a 100% gain just to get back to even.",
            "The S&P 500 fell roughly 57% from its 2007 peak to its March 2009 low.",
            "Stock Lab: drawdown chart vs. the S&P 500.",
        ),
        (
            "Diversification and correlation",
            "Owning things that don't all move together, so one bad bet can't sink you.",
            "Correlation runs from −1 (opposite moves) to +1 (identical moves). Mixing low-correlation assets reduces "
            "swings without necessarily reducing returns. Owning five tech stocks isn't much diversification; they're "
            "highly correlated.",
            "Two stocks with 0.9 correlation behave almost like one position.",
            "Analyst Desk → Trade Journal: 'How concentrated is your risk?' shows share of money vs. share of risk.",
        ),
        (
            "Position sizing",
            "Deciding how much money to put in each idea.",
            "Sizing matters as much as picking. A common rule is to size so that hitting your stop loses only a small, "
            "fixed share of the portfolio (often 1–2%). Higher conviction can justify a bigger position, never "
            "an unlimited one.",
            "A $10k portfolio risking 1% per trade can lose $100. With a stop 10% below entry, the position is $1,000.",
            "Analyst Desk → Trade Journal: shares × entry price, and the risk-concentration chart.",
        ),
        (
            "Sharpe ratio",
            "Return per unit of volatility.",
            "Two investments with the same return aren't equal if one got there with half the swings. Sharpe divides "
            "return (above the risk-free rate) by volatility. Above 1 over long periods is strong.",
            "12% return with 10% volatility (Sharpe ≈ 1.2) beats 15% return with 25% volatility (≈ 0.6) on a risk-adjusted basis.",
            "Stock Lab: Risk vs. the market table.",
        ),
    ],
    "Macro and rates": [
        (
            "The Fed and interest rates",
            "The Federal Reserve sets the short-term interest rate that everything else builds on.",
            "The Fed raises rates to cool inflation and cuts them to support growth. Higher rates make borrowing more "
            "expensive, slow the economy, and make safe bonds more attractive compared with stocks.",
            "When the Fed raised rates from near 0% to over 5% in 2022–23, mortgage rates more than doubled.",
            "Macro step 3: Fed funds, the 2-year and the 10-year.",
        ),
        (
            "Inflation and CPI",
            "How fast prices are rising, measured by the Consumer Price Index.",
            "Moderate inflation (the Fed targets 2%) is normal. High inflation erodes profits and purchasing power, and "
            "pushes the Fed to keep rates high. Core CPI excludes food and energy to show the underlying trend.",
            "CPI of 3.4% means a basket that cost $100 a year ago costs $103.40 now.",
            "Macro step 2.",
        ),
        (
            "The yield curve",
            "Treasury yields plotted from short maturities to long ones.",
            "Normally long-term bonds pay more than short-term ones. When short rates rise above long rates, the curve "
            "is 'inverted', a sign markets expect the Fed to cut because the economy will weaken. Inversions have "
            "preceded most US recessions, though with long and variable lags.",
            "3-month bill at 5.3%, 10-year at 4.3% → spread of −1.0 pts: inverted.",
            "Macro step 3 and the recession warning lights.",
        ),
        (
            "Why rates move stock prices",
            "Higher rates lower the value of future profits today.",
            "A stock's value is the present value of its future cash. Raise the discount rate and distant cash is worth "
            "less, which hits companies whose profits are mostly far in the future (high-growth tech) hardest. Rate-"
            "sensitive sectors like real estate and utilities also suffer because they carry lots of debt and compete "
            "with bond yields for income investors.",
            "Raising the discount rate from 8% to 10% can cut a long-duration DCF value by 25% or more.",
            "Analyst Desk → Trade Journal: try changing the required return in the DCF.",
        ),
        (
            "The business cycle and sector rotation",
            "Economies cycle through expansion and slowdown, and different sectors lead in each phase.",
            "Early in a recovery, cyclicals (financials, industrials, consumer discretionary) tend to lead. Late in the "
            "cycle, energy and materials often do well as inflation rises. In slowdowns, defensives (utilities, staples, "
            "health care) hold up better because demand for their products is steady.",
            "In a Reflation regime, Technology and Energy have historically beaten the S&P 500; Staples have lagged.",
            "Macro step 4 and Sector Rotation.",
        ),
        (
            "Recessions",
            "A significant, broad decline in economic activity lasting more than a few months.",
            "In the US, the National Bureau of Economic Research (NBER) officially dates recessions, often months after "
            "they start. Stocks usually fall before a recession begins and bottom before it ends, because markets look "
            "ahead.",
            "The 2008–09 recession lasted 18 months; the 2020 COVID recession lasted just 2.",
            "Macro step 5: the recession model and warning lights.",
        ),
    ],
    "Investor behavior": [
        (
            "Writing a thesis",
            "A short, specific reason you own a stock, plus what would prove you wrong.",
            "Writing it down before you buy turns a hunch into something you can test. The 'I'm wrong if' part matters "
            "most: it tells you when to sell for a reason instead of an emotion.",
            "'Data-center demand keeps growing; I'm wrong if gross margin falls below 60% for two quarters.'",
            "Analyst Desk → Trade Journal: every position requires a thesis and an 'I'm wrong if'.",
        ),
        (
            "Loss aversion",
            "Losses feel about twice as painful as equal gains feel good.",
            "This makes investors hold losers too long ('it'll come back') and sell winners too early ('lock it in'). "
            "A pre-set stop and target take the decision out of the moment.",
            "Refusing to sell a stock down 30% because selling would 'make the loss real'.",
            "Analyst Desk → Trade Journal: stops and targets, set when you're calm.",
        ),
        (
            "Confirmation bias",
            "Seeking out information that agrees with what you already believe.",
            "Once you own a stock, it's natural to read only the bullish news. Deliberately look for the best argument "
            "against your position, and update your view when the facts change.",
            "Dismissing three downgrades but sharing one upgrade.",
            "Analyst Desk → Trade Journal → Thesis log: record your view before big news, then compare.",
        ),
        (
            "Chasing and FOMO",
            "Buying because a stock has already gone up a lot and you're afraid of missing more.",
            "Big recent gains often mean the good news is already in the price. Ask what's priced in before chasing.",
            "A stock up 80% in three months now needs even stronger results to justify the new price.",
            "Analyst Desk → Trade Journal → Price target builder: the reverse DCF shows what's priced in.",
        ),
        (
            "Time horizon",
            "How long you plan to hold, which changes what matters.",
            "Over days, prices are mostly noise and news. Over years, they mostly follow earnings growth. Mismatching "
            "your strategy to your horizon (day-trading a long-term idea, or holding a short-term trade for years) is a "
            "common mistake.",
            "The S&P 500 has been down in about 1 of every 4 years, but positive over most 10-year periods.",
            "Analyst Desk → Trade Journal: each position's horizon.",
        ),
    ],
}


def all_terms() -> list[tuple[str, str, str]]:
    """(term, one-line definition, module) for the A–Z glossary."""
    import config

    terms = [(name, one, mod) for mod, items in MODULES.items() for name, one, *_ in items]
    known = {t[0].lower() for t in terms}
    terms += [(t, d, "Glossary") for t, d in config.GLOSSARY if t.lower() not in known]
    return sorted(terms, key=lambda t: t[0].lower())
