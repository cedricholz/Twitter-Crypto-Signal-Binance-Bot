from binance.client import Client
import json
import math
import utils


def get_binance_account():
    with open("binance_secrets.json") as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()

    return Client(secrets['key'], secrets['secret'])


def get_total_binance_bitcoin(binance):
    accounts = binance.get_account()['balances']
    for coin in accounts:
        if coin['asset'] == 'BTC':
            total_bitcoin = float(coin['free'])
            total_bitcoin = total_bitcoin - .001 * total_bitcoin
            return total_bitcoin
    return 0


"""

Goes through the buy orders and returns the
price of the first one that can be bought
with the amount that you have.

"""


def get_cur_price_from_large_enough_buy_order(binance, market, amount_bought):
    buy_orders = binance.get_order_book(symbol=market)['bids']

    for order in buy_orders:
        trade_amount = float(order[1])

        if trade_amount > amount_bought:
            trade_price = float(order[0])
            return trade_price


def get_most_recent_buy_order_price(binance, market):
    buy_orders = binance.get_order_book(symbol=market)['bids']

    first_order = buy_orders[0]
    trade_price = float(first_order[0])

    return trade_price


def get_most_recent_sell_order_price(binance, market):
    sell_orders = binance.get_order_book(symbol=market)['asks']

    first_order = sell_orders[0]
    trade_price = float(first_order[0])

    return trade_price


def get_binance_buyable_coins(binance):
    buyable_coins = {}
    products = binance.get_products()
    for coin in products['data']:
        market_currency = coin['quoteAssetName']
        if market_currency == "Bitcoin":
            market = coin['symbol']
            symbol = coin['baseAsset']
            full_name = coin['baseAssetName'].lower()

            buyable_coins[symbol.lower()] = (market, full_name)
            buyable_coins[full_name] = (market, full_name)
    return buyable_coins


###########

# BUYING #

###########


################### MARKET BUYING ###################

"""

Goes through the sell order book and
takes the price of the first order that
is selling the full amount that you can buy.
Returns the price and amount you can buy.

"""


def get_market_binance_amount_to_buy_and_order_rate(binance, market, total_bitcoin,
                                                    market_max_buy_percent_from_first_order):
    tickers = binance.get_exchange_info()['symbols']

    ticker = [ticker for ticker in tickers if ticker['symbol'] == market][0]

    constraints = ticker['filters'][1]

    minQty = float(constraints['minQty'])
    maxQty = float(constraints['maxQty'])
    stepSize = float(constraints['stepSize'])

    sell_orders = binance.get_order_book(symbol=market)['asks']

    initial_price = float(sell_orders[0][0])

    for order in sell_orders:
        order_rate = float(order[0])

        if utils.percent_change(initial_price, order_rate) < market_max_buy_percent_from_first_order:

            order_quantity = float(order[1])

            amount_to_buy = total_bitcoin / order_rate

            constrained_amount_to_buy = math.floor((1 / stepSize) * amount_to_buy) * stepSize
            if amount_to_buy < order_quantity and minQty < constrained_amount_to_buy < maxQty:
                return constrained_amount_to_buy, order_rate
        else:
            return 0
    return 0


"""

Uses all available bitcoin to buy
a coin at market value

"""


def market_buy_from_binance(binance, market, market_max_buy_percent_from_first_order):
    total_bitcoin = get_total_binance_bitcoin(binance)

    amount, order_price = get_market_binance_amount_to_buy_and_order_rate(binance, market, total_bitcoin,
                                                                          market_max_buy_percent_from_first_order)

    if amount == 0:
        utils.print_and_write_to_logfile("INSUFFICIENT FUNDS")
        return False, order_price, amount

    order = binance.order_market_buy(
        symbol=market,
        quantity=amount)

    if order['status'] == 'FILLED':
        utils.print_and_write_to_logfile("SUCCESSFUL ORDER ON BINANCE")
        utils.print_and_write_to_logfile("MARKET: " + market)
        utils.print_and_write_to_logfile("AMOUNT: " + str(amount))
        utils.print_and_write_to_logfile("TOTAL: " + str(total_bitcoin))
        return True, order_price, amount

    else:
        return False, order_price, amount


################### LIMIT BUYING ###################


"""

Calculates the desired price we could like to buy at,
then determines how many coins can be bought at that price.

"""


def get_limit_binance_amount_to_buy_and_price(binance, market, total_bitcoin, limit_buy_order_percent):
    tickers = binance.get_exchange_info()['symbols']

    ticker = [ticker for ticker in tickers if ticker['symbol'] == market][0]

    constraints = ticker['filters'][1]

    minQty = float(constraints['minQty'])
    maxQty = float(constraints['maxQty'])
    stepSize = float(constraints['stepSize'])

    sell_orders = binance.get_order_book(symbol=market)['asks']

    most_recent_order_price = float(sell_orders[0][0])

    desired_buy_price = float(most_recent_order_price * (1 + limit_buy_order_percent / 100))

    desired_buy_price_formatted = f'{desired_buy_price:.6f}'

    amount_to_buy = total_bitcoin / float(desired_buy_price_formatted)

    constrained_amount_to_buy = math.floor((1 / stepSize) * amount_to_buy) * stepSize
    if minQty < constrained_amount_to_buy < maxQty:
        return constrained_amount_to_buy, desired_buy_price_formatted

    return 0, 0


def limit_buy_from_binance(binance, market, limit_buy_order_percent):
    total_bitcoin = get_total_binance_bitcoin(binance)

    amount, order_price = get_limit_binance_amount_to_buy_and_price(binance, market, total_bitcoin,
                                                                    limit_buy_order_percent)
    utils.print_and_write_to_logfile("ATTEMPTING TO BUY " + str(amount) + " OF " + market + " FOR" + str(total_bitcoin) + " BTC")
    if amount > 0:
        try:
            order = binance.order_limit_buy(
                symbol=market,
                quantity=amount,
                price=order_price)


        except:
            utils.print_and_write_to_logfile("ERROR MAKING BUY")
            print(order)
            return "", 0, "", 0

        utils.print_and_write_to_logfile(
            "LIMIT BOUGHT " + str(amount) + " OF " + market + " FOR " + str(total_bitcoin) + " BTC ON BINANCE")

        order_id = order['orderId']

        x = binance.get_order(
            symbol=market,
            orderId=order_id)

        status = order['status']

        return status, float(order_price), order_id, amount

    utils.print_and_write_to_logfile("INSUFFICIENT FUNDS")
    return "", 0, "", 0


###########

# SELLING #

###########


################### MARKET SELLING ##################

def get_market_binance_amount_to_sell(binance, symbol, market):
    tickers = binance.get_exchange_info()['symbols']

    ticker = [ticker for ticker in tickers if ticker['symbol'] == market][0]

    constraints = ticker['filters'][1]

    minQty = float(constraints['minQty'])
    maxQty = float(constraints['maxQty'])
    stepSize = float(constraints['stepSize'])

    accounts = binance.get_account()['balances']
    for coin in accounts:
        if coin['asset'] == symbol:
            amount_held = float(coin['free'])
            amount_to_sell = math.floor((1 / stepSize) * amount_held) * stepSize

            if minQty < amount_to_sell < maxQty:
                return amount_to_sell
            return 0
    return 0


"""

Sells all of a coin for bitcoin at market value

"""


def market_sell_on_binance(binance, market):
    symbol = market.split("BTC")[0]

    amount = get_market_binance_amount_to_sell(binance, symbol, market)

    if amount > 0:
        order = binance.order_market_sell(
            symbol=market,
            quantity=amount)

        if order['status'] == 'FILLED':
            utils.print_and_write_to_logfile("MARKET SELL ORDER ON BINANCE")
            utils.print_and_write_to_logfile("MARKET: " + market)
            utils.print_and_write_to_logfile("AMOUNT" + str(amount))
            return True
        else:
            utils.print_and_write_to_logfile("SELL ORDER ON BINANCE UNSUCCESSFUL")
    else:
        utils.print_and_write_to_logfile("NOT ENOUGH COIN TO MAKE SELL ORDER")
        return False


################### LIMIT SELLING ##################


"""

Puts in a sell order at a percent:
limit_sell_order_desired_percentage_profit
Greater than the bought price.

"""


def limit_sell_on_binance(binance, market, amount_bought, baseline_price, limit_sell_order_desired_percentage_profit):
    symbol = market.split("BTC")[0]

    sell_price = baseline_price * (1 + limit_sell_order_desired_percentage_profit / 100)
    formatted_sell_price = f'{sell_price:.6f}'

    order = binance.order_limit_sell(
        symbol=market,
        quantity=amount_bought,
        price=formatted_sell_price)

    utils.print_and_write_to_logfile(
        "LIMIT SELLING " + str(amount_bought) + " OF " + market + " AT " + str(formatted_sell_price))

    utils.print_and_write_to_logfile("LIMIT SELL ORDER ON BINANCE")
    utils.print_and_write_to_logfile("MARKET: " + market)
    utils.print_and_write_to_logfile("AMOUNT" + str(amount_bought))

    status = order['status']
    order_id = order['orderId']

    return status, order_id
