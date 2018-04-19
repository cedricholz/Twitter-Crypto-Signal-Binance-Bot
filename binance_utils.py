from binance.client import Client
import json
import math
import utils


max_buy_percent_from_first_order = 3


def get_binance_account():
    with open("binance_secrets.json") as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()

    return Client(secrets['key'], secrets['secret'])


"""

Goes through the sell order book and
takes the price of the first order that
is selling the full amount that you can buy.
Returns the price and amount you can buy.

"""


def get_binance_amount_to_buy_and_order_rate(binance, market, total_bitcoin):
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

        if utils.percent_change(initial_price, order_rate) < max_buy_percent_from_first_order:

            order_quantity = float(order[1])

            amount_to_buy = total_bitcoin / order_rate

            constrained_amount_to_buy = math.floor((1 / stepSize) * amount_to_buy) * stepSize
            if amount_to_buy < order_quantity and minQty < constrained_amount_to_buy < maxQty:
                return constrained_amount_to_buy, order_rate
        else:
            return 0
    return 0


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
price of the first one that wants to buy at least
as much as you have.

"""


def get_cur_price(binance, market, amount_bought):
    buy_orders = binance.get_order_book(symbol=market)['bids']

    for order in buy_orders:
        trade_amount = float(order[1])

        if trade_amount > amount_bought:
            trade_price = float(order[0])
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


"""

Uses all available bitcoin to buy
a coin.

"""


def buy_from_binance(binance, market):
    total_bitcoin = get_total_binance_bitcoin(binance)

    amount, order_price = get_binance_amount_to_buy_and_order_rate(binance, market, total_bitcoin)

    if amount == 0:
        utils.print_and_write_to_logfile("INSUFFICIENT FUNDS OR BUY ORDER TOO HIGH")
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


def get_binance_amount_to_sell(binance, symbol, market):
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

Sells all of a coin for bitcoin

"""


def sell_on_binance(binance, market):
    symbol = market.split("BTC")[0]

    amount = get_binance_amount_to_sell(binance, symbol, market)

    if amount > 0:
        order = binance.order_market_sell(
            symbol=market,
            quantity=amount)

        if order['status'] == 'FILLED':
            utils.print_and_write_to_logfile("SELL ORDER ON BINANCE")
            utils.print_and_write_to_logfile("MARKET: " + market)
            utils.print_and_write_to_logfile("AMOUNT" + str(amount))
            return True
        else:
            utils.print_and_write_to_logfile("SELL ORDER ON BINANCE UNSUCCESSFUL")
    else:
        utils.print_and_write_to_logfile("NOT ENOUGH COIN TO MAKE SELL ORDER")
        return False
