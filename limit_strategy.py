import utils
import time
import tweepy
import binance_utils
from binance.websockets import BinanceSocketManager
from twisted.internet import reactor
import traceback

"""

Monitors someone's tweets for specific words.
If it contains those words, it then looks for a coin symbol in the
tweet and buys it if it can be bought on binance. Then
waits to sell the coin at a profit.

"""

# Get twitter id's from http://gettwitterid.com
twitter_user_ids_to_follow = ['759916693']
twitter, auth = utils.get_twitter_account()

binance = binance_utils.get_binance_account()
binance_coins = binance_utils.get_binance_buyable_coins(binance)

ignored_coins = utils.get_ignored_coins()

words_to_look_for = utils.get_words_to_look_for()

seconds_before_checking_binance = 30

one_minute_in_milliseconds = 60000

##################

# Buying Variables
# 1 means 1%

##################

# Percent above current sell price to place buy order
buy_order_overprice_percent = 0

# Cancel buy order if it hasn't sold and the price is this percent more than your order.
buy_order_cap_percent = 3

###################

# Selling Variables
# 1 means 1%

###################

# Desired percentage profit
sell_order_desired_percentage_profit = .01

# Percent below current price to place sell order, must be negative
sell_order_underprice_percent = -.01

# Percent dropped below last price after we have reached our goal, must be negative
# making it time to sell
sell_percent_down_to_sell = -1

"""

Puts in a buy order at a price that is limit_buy_order_percent above the current price
Then waits until the order has been filled.

"""


def handle_buying(market):
    status, bought_price, order_id, amount_bought = binance_utils.limit_buy_from_binance(binance, market,
                                                                                         buy_order_overprice_percent)

    if amount_bought > 0:
        utils.print_and_write_to_logfile("WAITING FOR BUY ORDER TO BE FILLED")

        cancel_price = bought_price * (1 + buy_order_cap_percent / 100)

        while status != 'FILLED':
            order = binance.get_order(
                symbol=market,
                orderId=order_id)

            status = order['status']

            amount_bought = float(order['executedQty'])

            if status == "FILLED":
                utils.print_and_write_to_logfile("ORDER FILLED")
                break

            cur_price = binance_utils.get_most_recent_sell_order_price(binance, market)

            if cur_price > cancel_price:
                utils.print_and_write_to_logfile(
                    "CANCELING ORDER: PRICE WENT UP TOO MUCH BEFORE ORDER WENT THROUGH. CUR PRICE: " + cur_price)
                result = binance.cancel_order(
                    symbol=market,
                    orderId=order_id)
                print(result)
                break

            time.sleep(seconds_before_checking_binance)

    if amount_bought > 0:
        utils.print_and_write_to_logfile("BUY ORDER HAS BEEN FILLED")

    return bought_price, amount_bought


def print_trade_data(price_bought, cur_price, max_price, percent_from_max, percent_from_bought):
    formatted_cur_price = f'{cur_price:.6f}'
    formatted_bought_price = f'{price_bought:.6f}'
    formatted_max_price = f'{max_price:.6f}'

    utils.print_and_write_to_logfile("\n" + "************** NEW TRADE **************")
    utils.print_and_write_to_logfile("PRICE BOUGHT " + str(formatted_bought_price))
    utils.print_and_write_to_logfile("CUR PRICE " + formatted_cur_price)
    utils.print_and_write_to_logfile("MAX PRICE " + str(formatted_max_price))
    utils.print_and_write_to_logfile("PERCENT FROM MAX: " + str(percent_from_max))
    utils.print_and_write_to_logfile("PERCENT FROM BOUGHT PRICE: " + str(percent_from_bought) + "\n")


# These variables need to be global so they
# work in the wait to sell stream

max_price = 0
reached_goal = False
percentage_change = 0
price_bought = 0
cur_price = 0


def wait_until_time_to_sell(market):
    utils.print_and_write_to_logfile("WAITING UNTIL TIME TO SELL")

    def process_message(msg):
        global max_price
        global reached_goal
        global percentage_change
        global price_bought
        global cur_price

        cur_price = float(msg['p'])

        percent_from_max = utils.percent_change(max_price, cur_price)
        percent_from_bought = utils.percent_change(price_bought, cur_price)

        # COMMENT THIS LINE OUT IF YOU DON'T WANT TOO MUCH DATA
        print_trade_data(price_bought, cur_price, max_price, percent_from_max, percent_from_bought)

        if reached_goal == False and percent_from_bought >= sell_order_desired_percentage_profit:
            reached_goal = True
            utils.print_and_write_to_logfile("REACHED PRICE GOAL")

        if percent_from_max < sell_percent_down_to_sell and reached_goal == True:
            utils.print_and_write_to_logfile("PERCENT DOWN FROM PEAK: " + str(percent_from_max) + ". TIME TO SELL")
            try:
                reactor.stop()
            except:
                print("REACTOR ALREADY STOPPED")

        max_price = max(cur_price, max_price)

    bm = BinanceSocketManager(binance)
    conn_key = bm.start_trade_socket(market, process_message)
    bm.run()


"""

Waits until the price has gone up

limit_sell_order_desired_percentage_profit

percent and then dropped

limit_sell_percent_down_to_sell

percent. Then puts in a sell order for

sell_order_underprice_percent

less than the current price.

"""


def handle_selling(bought_price, market, amount_bought):
    global max_price
    global reached_goal
    global percentage_change
    global price_bought
    global cur_price

    percentage_change = 0
    reached_goal = False
    max_price = bought_price
    price_bought = bought_price

    wait_until_time_to_sell(market)

    status, order_id = binance_utils.limit_sell_on_binance(binance, market, amount_bought, cur_price,
                                                           sell_order_underprice_percent)
    amount_sold = 0
    utils.print_and_write_to_logfile("WAITING FOR SELL ORDER TO GO THROUGH")
    while status != 'FILLED':
        cur_price = binance_utils.get_most_recent_buy_order_price(binance, market)

        order = binance.get_order(
            symbol=market,
            orderId=order_id)

        status = order['status']
        float(order['executedQty'])

        percent_change = utils.percent_change(bought_price, cur_price)

        time.sleep(seconds_before_checking_binance)
    utils.print_and_write_to_logfile(market + " SOLD")


class MyStreamListener(tweepy.StreamListener):

    # Called when there is a new status
    def on_status(self, status):
        try:
            tweet_time = int(status.timestamp_ms)
            cur_time = int(round(time.time() * 1000))

            # Tweets will queue while we are waiting to sell
            # and we don't want to buy on old data. Also don't take
            # tweets that are replies.
            if cur_time - tweet_time < one_minute_in_milliseconds and not status.in_reply_to_screen_name:

                if utils.contains_words_to_look_for(status.text, words_to_look_for):

                    coin_name = utils.get_coin_name_in_text(status.text, ignored_coins, binance_coins)

                    if coin_name:
                        utils.print_and_write_to_logfile(coin_name + " in Tweet: " + status.text)
                        market = binance_coins[coin_name][0]

                        bought_price, amount_bought = handle_buying(market)

                        if amount_bought > 0:
                            handle_selling(bought_price, market, amount_bought)
        except Exception as e:
            utils.print_and_write_to_logfile(traceback.format_exc())

    def on_exception(self, exception):
        print("Exception", exception)
        print("Restarting Stream...")
        return


# Begin Listening for new Tweets
utils.print_and_write_to_logfile("AWAITING TWEETS...")

while True:
    try:
        streamListener = MyStreamListener()
        stream = tweepy.Stream(auth, streamListener, timeout=600)
        stream.filter(follow=twitter_user_ids_to_follow)
    except Exception as e:
        utils.print_and_write_to_logfile("Restarting Stream...")
        utils.print_and_write_to_logfile(e.message)
