"""Daily Lesson curriculum: 7 units × 4 lessons, each about five minutes.

Each lesson has short learning cards, a one-line takeaway to use in real life, three quiz questions
(options, the index of the right answer, and why), and a small task to try.
"""


def Q(q: str, options: list[str], answer: int, why: str) -> dict:
    return {"q": q, "options": options, "answer": answer, "why": why}


UNITS = [
    {
        "title": "Money that grows",
        "blurb": "Why investing beats saving, and the few rules that do most of the work.",
        "lessons": [
            {
                "id": "compounding",
                "title": "Compounding",
                "cards": [
                    "Compounding means your returns start earning returns of their own. Invest $1,000 at 8% and you "
                    "have $1,080 after a year. In year two you earn 8% on $1,080, not $1,000. The growth curve bends "
                    "upward over time.",
                    "The Rule of 72 is a quick way to feel it: divide 72 by the annual return to get roughly how many "
                    "years it takes your money to double. At 8%, that's about 9 years; at 6%, about 12.",
                    "Because growth builds on itself, time matters more than almost anything else. Money invested at 20 "
                    "has many more doublings ahead of it than money invested at 40.",
                ],
                "takeaway": "Start early, even with small amounts. Time does the heavy lifting.",
                "questions": [
                    Q(
                        "Using the Rule of 72, how long does money take to double at 9% a year?",
                        ["About 4 years", "About 8 years", "About 12 years", "About 18 years"],
                        1,
                        "72 ÷ 9 = 8 years.",
                    ),
                    Q(
                        "You invest $1,000 at 10% a year. How much do you have after two years?",
                        ["$1,200", "$1,210", "$1,100", "$1,020"],
                        1,
                        "Year 1: $1,100. Year 2: 10% of $1,100 is $110, so $1,210. The extra $10 is compounding.",
                    ),
                    Q(
                        "Why does starting 10 years earlier matter so much?",
                        [
                            "You avoid taxes",
                            "Your money gets more doublings",
                            "Stocks were cheaper in the past",
                            "Brokers charge young investors less",
                        ],
                        1,
                        "Each extra decade at ~7% is roughly one more doubling of everything you'd already built.",
                    ),
                ],
                "try": "Pick a return you think is realistic (say 7%) and use the Rule of 72 to estimate how many "
                "times $1,000 would double by the time you're 60.",
            },
            {
                "id": "real-returns",
                "title": "Inflation and real returns",
                "cards": [
                    "Inflation is the rate prices rise. If prices go up 3% this year, $100 buys what $97 bought last "
                    "year. Money that sits still is quietly losing value.",
                    "Your real return is roughly your return minus inflation. A savings account paying 4% with 3% "
                    "inflation grows your buying power by only about 1% a year.",
                    "Stocks have historically beaten inflation over long periods because companies can raise prices "
                    "and grow earnings. That's the main reason people invest instead of only saving.",
                ],
                "takeaway": "Always ask what you earn after inflation. That's the number that buys things.",
                "questions": [
                    Q(
                        "Your account earns 5% while inflation is 3%. What is your approximate real return?",
                        ["8%", "5%", "2%", "-2%"],
                        2,
                        "Real return ≈ 5% − 3% = 2%. That's how much more your money can actually buy.",
                    ),
                    Q(
                        "Inflation is 4% and your cash earns 0%. What happens to your buying power in a year?",
                        ["It stays the same", "It falls about 4%", "It rises about 4%", "It falls 40%"],
                        1,
                        "Prices rose 4% and your money didn't grow, so it buys about 4% less.",
                    ),
                    Q(
                        "Why have stocks tended to beat inflation over decades?",
                        [
                            "Governments guarantee stock returns",
                            "Companies can raise prices and grow profits",
                            "Stocks never fall when inflation rises",
                            "Inflation is good for every company",
                        ],
                        1,
                        "Businesses pass higher costs to customers over time, so their earnings tend to keep up. "
                        "In the short run, high inflation can still hurt stocks.",
                    ),
                ],
                "try": "Open the Macro tab, read today's CPI inflation number, and compare it with the interest rate on "
                "your own savings account. Is your real return positive?",
            },
            {
                "id": "index-funds",
                "title": "Index funds and fees",
                "cards": [
                    "An index fund buys every company in an index, like the S&P 500, so you own a slice of hundreds of "
                    "businesses in one purchase. You get the market's return minus a small fee.",
                    "Over long periods, most professionally managed funds have trailed their index after fees. That's "
                    "why low-cost index funds are the core holding for many investors.",
                    "Fees are charged every year as a percentage of your money, the 'expense ratio'. They compound "
                    "just like returns: $10,000 growing at 7% for 30 years becomes about $76,000; at 6% (a 1% fee) it "
                    "becomes about $57,000.",
                ],
                "takeaway": "Check the expense ratio before you buy any fund. Small percentages become big dollars.",
                "questions": [
                    Q(
                        "What does an S&P 500 index fund own?",
                        [
                            "The 500 fastest-growing stocks",
                            "All 500 companies in the index, weighted by size",
                            "500 stocks picked by a manager",
                            "Bonds from 500 companies",
                        ],
                        1,
                        "It mirrors the index, so the biggest companies make up the biggest share.",
                    ),
                    Q(
                        "Fund A charges 0.05% a year and Fund B charges 1.00%. Both track the same index. Over 30 years:",
                        [
                            "They end up the same",
                            "Fund B ends up noticeably ahead",
                            "Fund A ends up noticeably ahead",
                            "Fees don't compound",
                        ],
                        2,
                        "Same holdings, but Fund B loses an extra ~0.95% every year, and that gap compounds.",
                    ),
                    Q(
                        "What is an expense ratio?",
                        [
                            "A one-time fee when you buy",
                            "The yearly fee as a percentage of your investment",
                            "The fund's profit margin",
                            "The tax you owe on gains",
                        ],
                        1,
                        "It's taken out of the fund's assets every year, so you never see a bill, only lower returns.",
                    ),
                ],
                "try": "Look up the expense ratio of one fund you own or are considering (it's on the fund's page on any "
                "brokerage or on Yahoo Finance). Is it under 0.2%?",
            },
            {
                "id": "dca",
                "title": "Dollar-cost averaging",
                "cards": [
                    "Dollar-cost averaging means investing the same amount on a schedule, say $100 every month, "
                    "whatever the market is doing. When prices are low your $100 buys more shares; when high, fewer.",
                    "It removes the hardest decision in investing: when to buy. Nobody times the market reliably, and "
                    "waiting for the 'right moment' often means never starting.",
                    "One nuance: if you already have a lump sum, investing it all at once has historically come out "
                    "ahead more often than not, because markets rise more years than they fall. Dollar-cost averaging "
                    "trades a little expected return for less regret.",
                ],
                "takeaway": "Automate a fixed monthly amount. Consistency beats timing.",
                "questions": [
                    Q(
                        "You invest $100 a month. The price is $50 in month 1 and $25 in month 2. How many shares do you own?",
                        ["4", "6", "3", "8"],
                        1,
                        "$100 ÷ $50 = 2 shares, then $100 ÷ $25 = 4 shares. Total 6. Lower prices bought you more.",
                    ),
                    Q(
                        "What problem does dollar-cost averaging mainly solve?",
                        [
                            "It guarantees a profit",
                            "It removes the need to time the market",
                            "It avoids all taxes",
                            "It makes stocks less volatile",
                        ],
                        1,
                        "It can't guarantee gains, but it takes timing, and emotion, out of the decision.",
                    ),
                    Q(
                        "With a lump sum ready to invest, what has historically won more often?",
                        [
                            "Investing it all at once",
                            "Spreading it over a year",
                            "Waiting for a crash",
                            "Keeping it in cash",
                        ],
                        0,
                        "Markets rise more often than they fall, so earlier money usually has more time to grow.",
                    ),
                ],
                "try": "If you invest, check whether your contributions are automatic. If not, write down the amount and "
                "day of the month you'd commit to.",
            },
        ],
    },
    {
        "title": "Reading a stock",
        "blurb": "What a share really is, and the handful of numbers that explain a company.",
        "lessons": [
            {
                "id": "expectations",
                "title": "Prices move on expectations",
                "cards": [
                    "A stock price is the market's best guess of a company's future, already baked in. News moves the "
                    "price only when it's different from what investors expected.",
                    "That's why a company can report record profits and fall: investors expected even more. And a "
                    "company can report a loss and rise, if it was smaller than feared.",
                    "When you read 'stock falls despite strong earnings', translate it to 'strong, but not as strong "
                    "as the price assumed'.",
                ],
                "takeaway": "Ask 'better or worse than expected?', not 'good or bad?'",
                "questions": [
                    Q(
                        "A company beats earnings estimates but the stock falls 6%. The most likely reason:",
                        [
                            "The report was fake",
                            "Investors expected even more, or guidance disappointed",
                            "The market was closed",
                            "Beating estimates is bad news",
                        ],
                        1,
                        "The price already assumed great results. Anything short of the hope gets sold.",
                    ),
                    Q(
                        "A struggling company loses less money than feared. What often happens?",
                        [
                            "The stock falls because it lost money",
                            "The stock can rise",
                            "Trading is halted",
                            "Nothing, losses never matter",
                        ],
                        1,
                        "Relative to low expectations, 'less bad' is good news.",
                    ),
                    Q(
                        "What's already 'priced in' to a stock?",
                        [
                            "Only last year's results",
                            "What investors collectively expect about the future",
                            "Nothing until the next report",
                            "Only the dividend",
                        ],
                        1,
                        "The price reflects the consensus view; surprises relative to it are what move it.",
                    ),
                ],
                "try": "Open the Stock Lab, pick a stock, and click an earnings label on the price chart. Did the stock "
                "rise or fall, and was EPS above or below the estimate?",
            },
            {
                "id": "market-cap",
                "title": "Market cap, not share price",
                "cards": [
                    "Share price alone tells you nothing about size. A $40 stock can be a bigger company than a $400 "
                    "stock. What matters is market capitalization: share price × number of shares.",
                    "Market cap is what the whole company is worth to the market. It's the number to compare when you "
                    "ask 'which company is bigger?' or 'is this priced like a giant or a startup?'",
                    "A 'cheap' $5 stock isn't cheap if the company has billions of shares and little profit. Price per "
                    "share is just how the pie is sliced.",
                ],
                "takeaway": "Compare companies by market cap and valuation, never by share price.",
                "questions": [
                    Q(
                        "Company A: 1B shares at $50. Company B: 100M shares at $300. Which is worth more?",
                        ["A ($50B vs $30B)", "B, because its price is higher", "They're equal", "Can't tell"],
                        0,
                        "A: 1B × $50 = $50B. B: 100M × $300 = $30B.",
                    ),
                    Q(
                        "A stock splits 2-for-1: you now have twice the shares at half the price. Your investment is worth:",
                        ["Twice as much", "Half as much", "The same", "It depends on the dividend"],
                        2,
                        "A split slices the same pie into more pieces. Market cap doesn't change.",
                    ),
                    Q(
                        "A $3 stock is:",
                        [
                            "Always a bargain",
                            "Not necessarily cheap; check its market cap and earnings",
                            "Always risky",
                            "Guaranteed to grow",
                        ],
                        1,
                        "Cheap or expensive depends on value relative to profits, not the sticker price per share.",
                    ),
                ],
                "try": "In the Stock Lab, compare the market caps of two companies you know (try COST and TSLA). Which "
                "is bigger, and does that match their share prices?",
            },
            {
                "id": "margins",
                "title": "Revenue, profit and margins",
                "cards": [
                    "Revenue is everything customers pay. Profit is what's left after costs. A company can grow revenue "
                    "fast and still lose money if costs grow faster.",
                    "Margins turn this into percentages. Operating margin = operating profit ÷ revenue: how many cents "
                    "of each sales dollar the business keeps after running costs.",
                    "High, stable margins usually mean pricing power: customers keep paying even when prices rise. "
                    "Compare margins within an industry; software and grocery stores are different worlds.",
                ],
                "takeaway": "Growth is only good if it's profitable growth. Check the margin.",
                "questions": [
                    Q(
                        "Revenue is $200M and operating profit is $50M. What is the operating margin?",
                        ["25%", "40%", "4%", "150%"],
                        0,
                        "$50M ÷ $200M = 25%. The business keeps 25¢ of every sales dollar after running costs.",
                    ),
                    Q(
                        "Which usually signals pricing power?",
                        [
                            "Margins that hold up even when costs rise",
                            "Revenue that falls every year",
                            "Margins that swing wildly",
                            "Lots of debt",
                        ],
                        0,
                        "If a company can pass higher costs on to customers, its margins stay steady.",
                    ),
                    Q(
                        "Why compare margins only within the same industry?",
                        [
                            "Industries have very different cost structures",
                            "Margins are secret",
                            "All companies have the same margin",
                            "Margins don't matter",
                        ],
                        0,
                        "A grocer with a 3% margin can be excellent; a software company with 3% would be struggling.",
                    ),
                ],
                "try": "In the Stock Lab scorecard, find a company whose operating margin is higher than its peers. "
                "What do you think lets it keep more of each dollar?",
            },
            {
                "id": "earnings-reports",
                "title": "Reading an earnings report",
                "cards": [
                    "Four times a year, public companies report results. The headline numbers are revenue and earnings "
                    "per share (EPS), each compared with analysts' estimates.",
                    "Guidance, the company's forecast for the next quarter or year, often matters more than the "
                    "results. Prices look forward, so a lowered outlook can sink a stock after a strong quarter.",
                    "The fastest way to read one: (1) revenue vs. estimate, (2) EPS vs. estimate, (3) guidance raised, "
                    "kept, or cut, (4) how the stock reacts the next morning.",
                ],
                "takeaway": "Read results, then guidance. The outlook usually drives the reaction.",
                "questions": [
                    Q(
                        "EPS was $1.10 versus a $1.00 estimate. That's:",
                        ["A 10% beat", "A 10% miss", "In line", "A 1.1% beat"],
                        0,
                        "($1.10 − $1.00) ÷ $1.00 = 10% above the estimate.",
                    ),
                    Q(
                        "A company beats this quarter but cuts next year's guidance. The stock most likely:",
                        ["Rises sharply", "Falls", "Doesn't move", "Is delisted"],
                        1,
                        "The future matters more to the price than the quarter that just ended.",
                    ),
                    Q(
                        "What is 'guidance'?",
                        [
                            "Advice from regulators",
                            "The company's own forecast for coming periods",
                            "An analyst's rating",
                            "The dividend policy",
                        ],
                        1,
                        "Management tells investors what it expects, and the market reprices around it.",
                    ),
                ],
                "try": "Pick a company you use every day and look up when it reports next (Yahoo Finance shows "
                "'Earnings Date'). Write down one number you'll check when it does.",
            },
        ],
    },
    {
        "title": "Cheap or expensive?",
        "blurb": "Valuation in practice: what you're really paying for.",
        "lessons": [
            {
                "id": "pe",
                "title": "The P/E ratio",
                "cards": [
                    "P/E = share price ÷ earnings per share. It's how many dollars you pay for $1 of the company's "
                    "annual profit. A P/E of 20 means you pay $20 for each $1 of earnings.",
                    "A high P/E isn't automatically bad: investors pay more for companies they expect to grow fast or "
                    "that feel safe. A low P/E isn't automatically good: the business may be shrinking.",
                    "P/Es only mean something compared with something: the company's peers, its own history, or the "
                    "overall market.",
                ],
                "takeaway": "Never judge a P/E alone. Compare it with peers.",
                "questions": [
                    Q(
                        "A stock trades at $90 and earned $4.50 per share. What is its P/E?",
                        ["20", "4.5", "40.5", "94.5"],
                        0,
                        "$90 ÷ $4.50 = 20. You pay $20 for every $1 of annual profit.",
                    ),
                    Q(
                        "Two similar companies: one at 15× earnings, one at 35×. The 35× company is most likely:",
                        ["Expected to grow faster", "Definitely overpriced", "Smaller", "Paying a bigger dividend"],
                        0,
                        "Investors pay up for expected growth. Whether that's justified is the real question.",
                    ),
                    Q(
                        "A P/E of 6 on a company whose profits are falling every year could be:",
                        ["A guaranteed bargain", "A value trap: cheap for a reason", "Impossible", "A growth stock"],
                        1,
                        "Low multiples can reflect real problems. Cheap needs a reason to stop being cheap.",
                    ),
                ],
                "try": "In the Stock Lab, look at the forward P/E peer chart for any company. Is it above or below the "
                "peer median, and can you think of a reason why?",
            },
            {
                "id": "growth-premium",
                "title": "Paying for growth",
                "cards": [
                    "Trailing P/E uses the last year's earnings; forward P/E uses expected earnings for the next year. "
                    "For a fast grower, forward P/E is much lower because profits are expected to rise.",
                    "The PEG ratio divides P/E by the growth rate to adjust for that. A P/E of 30 with 30% growth "
                    "(PEG 1) can be more reasonable than a P/E of 15 with 5% growth (PEG 3).",
                    "The catch: growth forecasts are guesses. If growth slows, a high-multiple stock can fall twice: "
                    "earnings come in lower, and investors pay a lower multiple for them.",
                ],
                "takeaway": "Growth justifies a premium only if it actually shows up.",
                "questions": [
                    Q(
                        "Price $120, trailing EPS $4, expected EPS next year $6. Forward P/E?",
                        ["30", "20", "24", "6"],
                        1,
                        "$120 ÷ $6 = 20. Trailing P/E is $120 ÷ $4 = 30.",
                    ),
                    Q(
                        "Stock A: P/E 30, growth 30%. Stock B: P/E 15, growth 5%. Which has the lower PEG?",
                        ["A (PEG 1.0)", "B (PEG 3.0)", "They're equal", "PEG can't be calculated"],
                        0,
                        "A: 30 ÷ 30 = 1.0. B: 15 ÷ 5 = 3.0. A is cheaper relative to its growth.",
                    ),
                    Q(
                        "Why can a high-P/E stock fall so hard when growth slows?",
                        [
                            "Earnings fall and the multiple shrinks too",
                            "Dividends stop",
                            "It gets delisted",
                            "High-P/E stocks never fall",
                        ],
                        0,
                        "Lower earnings × a lower P/E = a double hit to the price.",
                    ),
                ],
                "try": "In the Stock Lab scorecard, compare a company's trailing and forward P/E. A big gap means the "
                "market expects earnings to grow a lot. Do you believe it?",
            },
            {
                "id": "priced-in",
                "title": "What's priced in?",
                "cards": [
                    "Instead of asking 'what is this stock worth?', flip it: 'what growth does today's price assume?' "
                    "That's a reverse DCF, and it's one of the most useful questions in investing.",
                    "If the price only makes sense with 20% growth for a decade and the company is growing 10%, "
                    "you're betting it speeds up. If the price implies 3% and the company grows 12%, the market may be "
                    "too pessimistic.",
                    "It turns a vague feeling ('seems expensive') into a specific belief you can check against the "
                    "company's actual results.",
                ],
                "takeaway": "Before buying, write down the growth you'd need to believe.",
                "questions": [
                    Q(
                        "A reverse DCF says the price implies 25% yearly growth. The company grew 8% last year. That suggests:",
                        [
                            "The market expects a big acceleration",
                            "The stock is obviously cheap",
                            "Growth doesn't matter",
                            "The DCF is broken",
                        ],
                        0,
                        "You'd need growth to roughly triple for the price to make sense. That's a high bar.",
                    ),
                    Q(
                        "What does a reverse DCF take as given?",
                        ["The growth rate", "Today's price", "Next year's dividend", "The analyst target"],
                        1,
                        "It starts from the price and solves for the growth that justifies it.",
                    ),
                    Q(
                        "If the implied growth is well below what the company is actually achieving:",
                        [
                            "The market may be too pessimistic",
                            "The stock must be overpriced",
                            "The company is shrinking",
                            "It's a guaranteed buy",
                        ],
                        0,
                        "It's a starting point for research, not a guarantee. Ask why the market is so doubtful.",
                    ),
                ],
                "try": "Open the Analyst Desk → Trade Journal → Price target builder, enter a company, and read 'What's priced in?'. "
                "Is the implied growth a high bar or a low one?",
            },
            {
                "id": "traps",
                "title": "Value traps and hype",
                "cards": [
                    "A value trap is a stock that looks cheap (low P/E, high dividend) but keeps getting cheaper "
                    "because the business is declining. The low price is a warning, not a gift.",
                    "The opposite trap is hype: paying any price because a story is exciting. Even great companies "
                    "can be bad investments if you pay too much.",
                    "The fix for both is the same: connect the price to the business. What are earnings doing, what "
                    "growth is priced in, and what would have to change for the price to be right?",
                ],
                "takeaway": "Cheap needs a catalyst; exciting needs a sane price.",
                "questions": [
                    Q(
                        "A stock has a 9% dividend yield and falling earnings. The biggest risk is:",
                        ["The dividend gets cut", "The yield is too low", "It grows too fast", "Too many buyers"],
                        0,
                        "An unusually high yield often means the market doubts the dividend can last.",
                    ),
                    Q(
                        "A great company at a very high price is:",
                        ["Always a great investment", "Possibly a poor investment", "Impossible", "Always a short"],
                        1,
                        "Returns depend on the price you pay, not just the quality of the business.",
                    ),
                    Q(
                        "What helps you avoid a value trap?",
                        [
                            "Buying the lowest P/E in every sector",
                            "Checking whether earnings are stable or growing",
                            "Ignoring the business",
                            "Only buying stocks under $10",
                        ],
                        1,
                        "If earnings keep falling, a low multiple can still be too high.",
                    ),
                ],
                "try": "Find a stock in the Stock Lab with a P/E below its peers. Check its revenue and earnings growth: "
                "is it cheap for a reason?",
            },
        ],
    },
    {
        "title": "Placing a trade",
        "blurb": "The mechanics: orders, exits, sizing and costs.",
        "lessons": [
            {
                "id": "orders",
                "title": "Market vs. limit orders",
                "cards": [
                    "Every stock has a bid (the most a buyer will pay) and an ask (the least a seller will take). The "
                    "gap is the spread, a small cost you pay every time you trade.",
                    "A market order buys or sells right now at the best available price. It guarantees the trade, not "
                    "the price.",
                    "A limit order only fills at your price or better. It guarantees the price, not the trade. Limit "
                    "orders protect you in fast markets and thinly traded stocks.",
                ],
                "takeaway": "Use limit orders when the price matters more than speed.",
                "questions": [
                    Q(
                        "Which order guarantees the price you get?",
                        ["Market order", "Limit order", "Both", "Neither"],
                        1,
                        "A limit order won't fill at a worse price than you set, but it might not fill at all.",
                    ),
                    Q(
                        "Bid $49.95, ask $50.05. What's the spread?",
                        ["$0.10", "$0.05", "$100", "$50"],
                        0,
                        "$50.05 − $49.95 = $0.10. Buying and selling instantly would cost about that per share.",
                    ),
                    Q(
                        "You place a limit buy at $45 on a $50 stock. When does it fill?",
                        ["Immediately", "Only if the price falls to $45 or below", "At the close", "Never"],
                        1,
                        "Your order waits until a seller accepts $45 or less.",
                    ),
                ],
                "try": "Look up any stock's bid and ask on a quote page. Is the spread a penny or much wider? Wider "
                "spreads usually mean fewer shares trade.",
            },
            {
                "id": "exits",
                "title": "Planning your exit",
                "cards": [
                    "The most important decision happens before you buy: what would make you sell? Write down a "
                    "target (where you'd take profits or reassess) and a stop (where you admit you're wrong).",
                    "A stop-loss order sells automatically if the price falls to your level. It turns into a market "
                    "order when triggered, so in a sudden crash you can sell below your stop.",
                    "The best stops are tied to your thesis ('I'm wrong if margins fall below 60%'), not just a "
                    "random percentage.",
                ],
                "takeaway": "Decide your exit while you're calm, before the money is at risk.",
                "questions": [
                    Q(
                        "You buy at $100 with a stop at $90. What's your planned maximum loss per share?",
                        ["$10 (10%)", "$90", "$1", "Unlimited"],
                        0,
                        "$100 − $90 = $10. In a gap down it could be more, because a stop becomes a market order.",
                    ),
                    Q(
                        "When a stop-loss is triggered, it becomes:",
                        ["A limit order at your stop price", "A market order", "Cancelled", "A buy order"],
                        1,
                        "It sells at the next available price, which may be below your stop in a fast drop.",
                    ),
                    Q(
                        "Which is the strongest reason to sell?",
                        [
                            "The stock dipped 3% today",
                            "Your 'I'm wrong if' condition happened",
                            "A friend sold",
                            "You're bored",
                        ],
                        1,
                        "Selling because your thesis broke is a decision; selling on a dip is usually a reaction.",
                    ),
                ],
                "try": "Open the Analyst Desk → Trade Journal and write a thesis, target and stop for one stock you like, even if you "
                "don't own it.",
            },
            {
                "id": "sizing",
                "title": "How much to buy",
                "cards": [
                    "Position sizing is deciding how much money goes into each idea. It matters as much as picking: "
                    "one oversized mistake can undo many good calls.",
                    "A common rule: size each position so that hitting your stop costs only a small, fixed share of "
                    "your portfolio, often 1–2%.",
                    "The math: risk amount ÷ distance to your stop = position size. With $10,000 and a 1% risk "
                    "($100), a stop 10% below entry means a $1,000 position.",
                ],
                "takeaway": "Decide how much you're willing to lose, then work backward to the position size.",
                "questions": [
                    Q(
                        "$5,000 portfolio, 1% risk per trade, stop 10% below entry. Position size?",
                        ["$500", "$50", "$5,000", "$1,000"],
                        0,
                        "1% of $5,000 = $50 at risk. $50 ÷ 10% = $500 position.",
                    ),
                    Q(
                        "If your stop is further away (20% instead of 10%), the position should be:",
                        ["Bigger", "Smaller", "The same", "Zero"],
                        1,
                        "Same dollars at risk over a bigger distance means fewer shares.",
                    ),
                    Q(
                        "Why size positions at all?",
                        [
                            "To guarantee profits",
                            "So no single mistake can sink you",
                            "Brokers require it",
                            "To pay less tax",
                        ],
                        1,
                        "Sizing caps the damage from the ideas that don't work out, and some won't.",
                    ),
                ],
                "try": "In the Analyst Desk → Trade Journal, check 'How concentrated is your risk?'. Is any one position more than its "
                "fair share of the risk?",
            },
            {
                "id": "costs-taxes",
                "title": "Costs and taxes",
                "cards": [
                    "Trading isn't free even with zero commissions: you pay the spread, and frequent trading tends to "
                    "lower returns because of costs and mistimed decisions.",
                    "In the US, gains on investments held more than a year are taxed as long-term capital gains, "
                    "usually at lower rates than gains on investments held a year or less.",
                    "Tax-advantaged accounts (like IRAs and 401(k)s) let investments grow without yearly taxes on "
                    "gains. Rules and limits change, so check the current ones.",
                ],
                "takeaway": "Hold longer, trade less, and use tax-advantaged accounts where you can.",
                "questions": [
                    Q(
                        "You sell a stock you've held for 8 months at a profit. In the US, that's usually:",
                        ["A short-term gain", "A long-term gain", "Tax-free", "A loss"],
                        0,
                        "Held one year or less = short-term, typically taxed like regular income.",
                    ),
                    Q(
                        "Which tends to lower long-run returns?",
                        [
                            "Holding index funds for years",
                            "Frequent trading",
                            "Automatic contributions",
                            "Low expense ratios",
                        ],
                        1,
                        "Every trade has costs, and frequent traders often buy high and sell low.",
                    ),
                    Q(
                        "What's a key benefit of tax-advantaged retirement accounts?",
                        [
                            "Guaranteed returns",
                            "Gains aren't taxed every year",
                            "No stock market risk",
                            "Unlimited contributions",
                        ],
                        1,
                        "Avoiding yearly taxes on gains lets more of your money compound.",
                    ),
                ],
                "try": "If you have a brokerage account, check whether it's a regular (taxable) account or a "
                "tax-advantaged one, and how long you've held each position.",
            },
        ],
    },
    {
        "title": "Building a portfolio",
        "blurb": "Combining investments so one bad bet can't sink you.",
        "lessons": [
            {
                "id": "diversification",
                "title": "Diversification",
                "cards": [
                    "Diversification means owning things that don't all move together. When one falls, others may "
                    "hold up, so the whole portfolio swings less.",
                    "Correlation measures how alike two investments move, from −1 (opposite) to +1 (identical). Five "
                    "tech stocks with 0.9 correlation are barely more diversified than one.",
                    "True diversification mixes sectors, company sizes, countries and asset types like bonds, not just "
                    "a longer list of similar names.",
                ],
                "takeaway": "Count your bets by what drives them, not by how many tickers you own.",
                "questions": [
                    Q(
                        "Which pair is most diversifying?",
                        ["Two chip stocks", "A chipmaker and a utility", "Two AI funds", "Two big banks"],
                        1,
                        "Different businesses with different drivers tend to have lower correlation.",
                    ),
                    Q(
                        "A correlation of +0.95 between two stocks means they:",
                        ["Move almost identically", "Move in opposite directions", "Are unrelated", "Never fall"],
                        0,
                        "Near +1 means they rise and fall together. Owning both adds little diversification.",
                    ),
                    Q(
                        "You own 10 stocks, all large US tech companies. You're:",
                        ["Fully diversified", "Concentrated in one theme", "Holding bonds", "Market neutral"],
                        1,
                        "Ten names, one bet: they'll mostly move together.",
                    ),
                ],
                "try": "In the Analyst Desk → Trade Journal risk section, compare 'share of money' with 'share of risk'. Is one "
                "holding driving most of the swings?",
            },
            {
                "id": "allocation",
                "title": "Stocks, bonds and your time horizon",
                "cards": [
                    "Asset allocation is how you split money between stocks, bonds and cash. It drives most of a "
                    "portfolio's ups and downs, more than which individual stocks you pick.",
                    "Stocks grow more over long periods but can drop 30–50% in a bad year. Bonds grow less but are "
                    "usually steadier. Cash is stable but loses to inflation.",
                    "The longer until you need the money, the more ups and downs you can ride out, which is why "
                    "younger investors often hold more in stocks.",
                ],
                "takeaway": "Money you need soon shouldn't be in stocks.",
                "questions": [
                    Q(
                        "You need money for a down payment on a home in 18 months. The most suitable place for it is usually:",
                        ["Volatile growth stocks", "Cash or short-term bonds", "Crypto", "A single stock"],
                        1,
                        "A 30% drop right before you need it would be a disaster. Short horizons call for stability.",
                    ),
                    Q(
                        "What drives most of a portfolio's overall swings?",
                        [
                            "Which brokerage you use",
                            "The mix of stocks, bonds and cash",
                            "The day you trade",
                            "The number of tickers",
                        ],
                        1,
                        "A 90% stock portfolio behaves very differently from a 40% stock portfolio.",
                    ),
                    Q(
                        "Why can a 20-year-old usually hold more stocks than a 60-year-old?",
                        [
                            "Stocks are safer for young people",
                            "More time to recover from downturns",
                            "Young people pay no tax",
                            "Older people can't buy stocks",
                        ],
                        1,
                        "A long horizon gives the market time to recover from crashes.",
                    ),
                ],
                "try": "Write down when you'll need each pot of your money (1 year, 5 years, 30 years). Would each "
                "survive a 40% stock market drop?",
            },
            {
                "id": "rebalancing",
                "title": "Rebalancing",
                "cards": [
                    "Over time, winners grow into a bigger share of your portfolio, and you end up taking more risk "
                    "than you chose. Rebalancing brings the mix back to your targets.",
                    "It means selling some of what's done well and buying what's lagged: a built-in way to sell high "
                    "and buy low without having to predict anything.",
                    "Most people rebalance on a schedule (once a year) or when a holding drifts more than a few "
                    "percentage points from its target.",
                ],
                "takeaway": "Pick target weights and restore them once a year.",
                "questions": [
                    Q(
                        "Your target is 60% stocks / 40% bonds. After a rally it's 75% / 25%. Rebalancing means:",
                        [
                            "Buying more stocks",
                            "Selling some stocks and buying bonds",
                            "Doing nothing",
                            "Selling everything",
                        ],
                        1,
                        "Trim what's grown back to 60% and add to bonds back to 40%.",
                    ),
                    Q(
                        "Why rebalance at all?",
                        [
                            "To keep your risk at the level you chose",
                            "To chase the best performer",
                            "Because it's required by law",
                            "To avoid all losses",
                        ],
                        0,
                        "Without it, a strong run quietly turns a moderate portfolio into an aggressive one.",
                    ),
                    Q(
                        "Rebalancing naturally makes you:",
                        [
                            "Buy high, sell low",
                            "Sell what's risen and buy what's fallen",
                            "Trade every day",
                            "Hold only cash",
                        ],
                        1,
                        "It's a rules-based version of 'buy low, sell high'.",
                    ),
                ],
                "try": "Look at how your own holdings (or the example journal) are weighted today. If you set targets, "
                "how far has each drifted?",
            },
            {
                "id": "drawdowns",
                "title": "Surviving drawdowns",
                "cards": [
                    "A drawdown is a fall from a peak. The S&P 500 has had many 20%+ drops and a few near 50%. They "
                    "are normal, not signs the system is broken.",
                    "Losses are lopsided: after a 50% loss you need a 100% gain to get back to even. That's why "
                    "avoiding huge losses matters more than chasing huge gains.",
                    "Many of the market's best days come shortly after its worst ones. Selling in a panic often "
                    "means missing the rebound.",
                ],
                "takeaway": "Expect big drops in advance so you don't sell at the bottom.",
                "questions": [
                    Q(
                        "A stock falls 50%. What gain does it need to get back to its old price?",
                        ["50%", "100%", "75%", "25%"],
                        1,
                        "$100 → $50 is −50%. $50 → $100 is +100%.",
                    ),
                    Q(
                        "Big market drops of 20% or more are:",
                        [
                            "Extremely rare, once a century",
                            "A normal part of investing",
                            "Impossible today",
                            "Always followed by more drops",
                        ],
                        1,
                        "They've happened many times and the market has recovered from each so far, sometimes slowly.",
                    ),
                    Q(
                        "Why is panic-selling after a crash costly?",
                        [
                            "You often miss the rebound days",
                            "It's illegal",
                            "Brokers charge double",
                            "Prices can't go lower",
                        ],
                        0,
                        "Some of the strongest days cluster right after the worst ones.",
                    ),
                ],
                "try": "Open the Stock Lab drawdown chart for a stock you like. What was its worst drop, and how would "
                "you have felt holding through it?",
            },
        ],
    },
    {
        "title": "Reading the economy",
        "blurb": "How interest rates, inflation and the cycle move stock prices.",
        "lessons": [
            {
                "id": "fed-rates",
                "title": "The Fed and interest rates",
                "cards": [
                    "The Federal Reserve sets a short-term interest rate that ripples into mortgages, car loans and "
                    "corporate borrowing. It raises rates to cool inflation and cuts them to support growth.",
                    "Higher rates hurt stocks in two ways: borrowing costs rise and profits slow, and safe bonds start "
                    "paying more, so investors demand more from stocks.",
                    "Fast-growing companies whose profits are mostly in the future get hit hardest, because "
                    "higher rates shrink what that distant money is worth today.",
                ],
                "takeaway": "When rates jump, expect growth stocks and rate-sensitive sectors to feel it most.",
                "questions": [
                    Q(
                        "The Fed usually raises interest rates to:",
                        ["Boost stock prices", "Cool down inflation", "Weaken the dollar", "Pay off debt"],
                        1,
                        "Higher rates slow borrowing and spending, which eases price pressure.",
                    ),
                    Q(
                        "Which tends to be hit hardest by rising rates?",
                        ["High-growth tech stocks", "Cash", "Short-term Treasury bills", "Nothing changes"],
                        0,
                        "Their value rests on profits far in the future, which higher rates discount more heavily.",
                    ),
                    Q(
                        "Why do higher bond yields compete with stocks?",
                        [
                            "Bonds become a more attractive safe alternative",
                            "Bonds are illegal to sell",
                            "Stocks stop paying dividends",
                            "They don't compete",
                        ],
                        0,
                        "If a safe bond pays 5%, a risky stock has to offer a lot more to be worth it.",
                    ),
                ],
                "try": "Open the Macro tab, step 3. Is the Fed's rate above or below inflation right now? What does "
                "the dashboard call the stance?",
            },
            {
                "id": "inflation-data",
                "title": "Inflation day",
                "cards": [
                    "Every month the government releases the Consumer Price Index (CPI). Markets care less about the "
                    "number itself than about how it compares with expectations.",
                    "A hotter-than-expected CPI suggests the Fed will keep rates high, so bond yields often rise and "
                    "stocks often fall that day. A cooler reading usually does the opposite.",
                    "Core CPI strips out volatile food and energy prices. The Fed watches it closely for the "
                    "underlying trend.",
                ],
                "takeaway": "On CPI day, watch the surprise versus expectations, then watch bond yields.",
                "questions": [
                    Q(
                        "CPI comes in hotter than expected. Stocks most often:",
                        [
                            "Rise, because inflation is good",
                            "Fall, as rate-cut hopes fade",
                            "Don't react",
                            "Close for the day",
                        ],
                        1,
                        "Hot inflation means rates stay higher for longer, which weighs on valuations.",
                    ),
                    Q(
                        "Why does the Fed watch core inflation?",
                        [
                            "It includes only food",
                            "It removes volatile food and energy to show the trend",
                            "It's always lower",
                            "It's the stock market index",
                        ],
                        1,
                        "Gas and grocery prices swing a lot; core shows what's happening underneath.",
                    ),
                    Q(
                        "What usually matters most to markets on data days?",
                        [
                            "The number vs. what was expected",
                            "Whether the number is even",
                            "The day of the week",
                            "Last year's number only",
                        ],
                        0,
                        "Expectations are already priced in; surprises move prices.",
                    ),
                ],
                "try": "Look up the date of the next CPI release (the Bureau of Labor Statistics publishes a schedule) "
                "and check the Macro tab's inflation chart that week.",
            },
            {
                "id": "yield-curve",
                "title": "The yield curve",
                "cards": [
                    "The yield curve compares interest rates on short-term and long-term government bonds. Normally "
                    "long-term bonds pay more, because you're locking money up longer.",
                    "When short-term rates rise above long-term ones, the curve is 'inverted'. It means investors "
                    "expect the Fed to cut rates later, usually because they expect the economy to weaken.",
                    "Inversions have come before most US recessions, but the lag is long and variable, and there "
                    "have been false alarms. Treat it as a warning light, not a countdown.",
                ],
                "takeaway": "An inverted curve says 'be careful', not 'sell everything tomorrow'.",
                "questions": [
                    Q(
                        "The 3-month bill yields 5% and the 10-year yields 4%. The curve is:",
                        ["Normal", "Inverted", "Flat", "Broken"],
                        1,
                        "Short-term rates above long-term rates = inverted.",
                    ),
                    Q(
                        "An inverted yield curve has historically signaled:",
                        [
                            "Higher inflation tomorrow",
                            "Higher recession risk ahead",
                            "A stock market boom",
                            "Nothing at all",
                        ],
                        1,
                        "It's preceded most recessions, though often by a year or more.",
                    ),
                    Q(
                        "Why shouldn't you treat an inversion as an exact sell signal?",
                        [
                            "The lag is long and there are false alarms",
                            "It never happens",
                            "It's illegal to trade on",
                            "It only matters for bonds",
                        ],
                        0,
                        "The 2022–23 inversion was deep and long, and no recession followed right away.",
                    ),
                ],
                "try": "Check the Macro tab's recession warning lights. Is the yield curve light clear, watch or warning?",
            },
            {
                "id": "cycle",
                "title": "Sectors through the cycle",
                "cards": [
                    "Different sectors lead at different stages of the economy. Early in a recovery, cyclicals like "
                    "financials, industrials and consumer discretionary often lead.",
                    "When growth slows, defensives like utilities, consumer staples and health care tend to hold up "
                    "better, because people keep buying electricity, toothpaste and medicine.",
                    "Watching which sectors lead tells you what investors expect about the economy, often before the "
                    "data confirms it.",
                ],
                "takeaway": "Leadership tells you the market's mood: cyclicals = confident, defensives = cautious.",
                "questions": [
                    Q(
                        "Utilities and consumer staples are leading the market. Investors are most likely feeling:",
                        [
                            "Very confident about growth",
                            "Cautious about the economy",
                            "Excited about tech",
                            "Nothing, it's random",
                        ],
                        1,
                        "Money moving to steady earners usually signals worry about growth.",
                    ),
                    Q(
                        "Which is a cyclical sector?",
                        ["Utilities", "Consumer discretionary", "Consumer staples", "Health care"],
                        1,
                        "Spending on cars, travel and restaurants rises and falls with the economy.",
                    ),
                    Q(
                        "Why do staples hold up in slowdowns?",
                        ["People still buy essentials", "They pay no tax", "The Fed buys them", "They never fall"],
                        0,
                        "Demand for everyday necessities barely changes when the economy weakens.",
                    ),
                ],
                "try": "Open Sector Rotation and look at the risk-appetite line. Are cyclicals beating defensives "
                "right now?",
            },
        ],
    },
    {
        "title": "Mind games",
        "blurb": "The biggest risk in investing is usually the investor.",
        "lessons": [
            {
                "id": "loss-aversion",
                "title": "Loss aversion",
                "cards": [
                    "Research suggests losses feel roughly twice as painful as equal gains feel good. That asymmetry "
                    "quietly drives bad decisions.",
                    "It makes people hold losing stocks too long ('I'll sell when it gets back to even') and sell "
                    "winners too early ('lock it in before it goes away').",
                    "The price you paid is irrelevant to the stock. The only question is whether you'd buy it today "
                    "at today's price.",
                ],
                "takeaway": "Ask 'would I buy this today?', not 'am I up or down?'",
                "questions": [
                    Q(
                        "'I'll sell once it gets back to what I paid.' This is an example of:",
                        ["Loss aversion", "Diversification", "Rebalancing", "Dollar-cost averaging"],
                        0,
                        "Your purchase price is an emotional anchor, not information about the company.",
                    ),
                    Q(
                        "Loss aversion tends to make investors:",
                        [
                            "Sell winners too early and hold losers too long",
                            "Trade less",
                            "Buy more bonds",
                            "Ignore the news",
                        ],
                        0,
                        "Avoiding the pain of 'realizing' a loss keeps bad positions alive.",
                    ),
                    Q(
                        "The best question when deciding whether to keep a losing stock:",
                        [
                            "What did I pay?",
                            "Would I buy it at today's price?",
                            "What did my friends do?",
                            "How long have I held it?",
                        ],
                        1,
                        "The decision should look forward, at the business and the price, not back at your cost.",
                    ),
                ],
                "try": "Look at one position you own (or one in the example journal). Ignoring what you paid, would you "
                "buy it today at this price?",
            },
            {
                "id": "confirmation",
                "title": "Confirmation bias",
                "cards": [
                    "Once we own something, we naturally look for news that says we're right and skip news that says "
                    "we're wrong. That's confirmation bias.",
                    "The antidote is to deliberately look for the best argument against your position. If you can't "
                    "state the bear case, you don't fully understand the stock.",
                    "Writing down your view before big news (like earnings) keeps you honest, because memory "
                    "rewrites itself after the fact.",
                ],
                "takeaway": "For every stock you own, be able to argue the other side.",
                "questions": [
                    Q(
                        "You only read bullish articles about a stock you own. That's:",
                        ["Confirmation bias", "Diversification", "Good research", "Rebalancing"],
                        0,
                        "Seeking agreeing information while ignoring the rest.",
                    ),
                    Q(
                        "Which habit best fights confirmation bias?",
                        [
                            "Reading only analyst upgrades",
                            "Writing the strongest case against your position",
                            "Checking the price more often",
                            "Following one source",
                        ],
                        1,
                        "Arguing the other side forces you to weigh the evidence you'd rather skip.",
                    ),
                    Q(
                        "Why write your expectations down before earnings?",
                        [
                            "So you can compare honestly afterwards",
                            "Brokers require it",
                            "To get better prices",
                            "It changes the results",
                        ],
                        0,
                        "After the fact, it's easy to believe you 'knew it all along'.",
                    ),
                ],
                "try": "In the Analyst Desk → Trade Journal → Thesis log, add a note on one stock: the single biggest thing that could "
                "go wrong.",
            },
            {
                "id": "fomo",
                "title": "FOMO and chasing",
                "cards": [
                    "Fear of missing out pushes people to buy after a stock has already soared, often near the top, "
                    "because everyone around them is making money.",
                    "A stock that's up 80% in three months has to deliver even better news to justify its new price. "
                    "The easy gains may already be gone.",
                    "A rule that helps: never buy on the same day you first hear about a stock. Give yourself time to "
                    "check what's priced in.",
                ],
                "takeaway": "If you're buying because it went up, stop and check what's priced in first.",
                "questions": [
                    Q(
                        "A stock doubled in two months and it's all over social media. FOMO says:",
                        [
                            "Buy now before it goes higher",
                            "Wait and check the valuation",
                            "Short it immediately",
                            "Ignore all stocks",
                        ],
                        0,
                        "That urge is the bias. The better move is to check what the new price assumes.",
                    ),
                    Q(
                        "After a huge run, a stock needs ___ to keep rising:",
                        ["Even better news than before", "No news at all", "A stock split", "Lower earnings"],
                        0,
                        "The higher price already reflects great expectations; it needs to beat them.",
                    ),
                    Q(
                        "A simple rule to resist chasing:",
                        [
                            "Never buy on the day you first hear about a stock",
                            "Always buy the top gainer",
                            "Only buy at the open",
                            "Follow the crowd",
                        ],
                        0,
                        "A cooling-off period turns an impulse into a decision.",
                    ),
                ],
                "try": "Look at the biggest up-move label on any Stock Lab chart. Did the stock keep rising afterwards? "
                "Check 'Did it stick?'.",
            },
            {
                "id": "process",
                "title": "Process over outcome",
                "cards": [
                    "A good decision can lose money and a bad one can make money, at least for a while. Luck is loud "
                    "in the short run.",
                    "Judge yourself on process: did you have a thesis, a valuation check, a planned exit and a "
                    "sensible size? Over many decisions, good process wins.",
                    "That's why investors keep journals. Reviewing your reasoning, not just your returns, is how you "
                    "actually get better.",
                ],
                "takeaway": "Grade the decision, not the result. Keep a journal.",
                "questions": [
                    Q(
                        "You bought a stock on a tip with no research, and it rose 30%. This was:",
                        ["A good process", "A good outcome from a weak process", "A bad outcome", "Proof tips work"],
                        1,
                        "The result was lucky; repeating that process will eventually hurt.",
                    ),
                    Q(
                        "What should you review most after a trade?",
                        [
                            "Only the profit or loss",
                            "Your reasoning and whether it held up",
                            "The broker's fees",
                            "What the stock did after you sold",
                        ],
                        1,
                        "Checking your thesis against reality is how your process improves.",
                    ),
                    Q(
                        "Why keep an investing journal?",
                        [
                            "To remember your reasoning honestly",
                            "It's required",
                            "It improves returns automatically",
                            "To impress others",
                        ],
                        0,
                        "A written record beats memory, which tends to flatter us.",
                    ),
                ],
                "try": "Open the Analyst Desk → Trade Journal and review one position's thesis. Is it still true? Add a dated note "
                "either way.",
            },
        ],
    },
]

LESSONS = [dict(lesson, unit=u, unit_title=unit["title"]) for u, unit in enumerate(UNITS) for lesson in unit["lessons"]]
BY_ID = {lesson["id"]: lesson for lesson in LESSONS}
