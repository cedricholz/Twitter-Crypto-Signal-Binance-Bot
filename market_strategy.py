import utils
import time
import traceback
import time
import tweepy
import binance_utils

"""

Monitors someone's tweets for specific words.
If it contains those words, it then looks for a coin symbol in the
tweet and buys it if it can be bought on binance. Then
waits to sell the coin at a profit.

"""

utils.print_and_write_to_logfile('STARTING...')

# Get twitter id's from http://gettwitterid.com
twitter_user_ids_to_follow = ['759916693']
twitter, auth = utils.get_twitter_account()

binance = binance_utils.get_binance_account()
binance_coins = binance_utils.get_binance_buyable_coins(binance)

ignored_coins = utils.get_ignored_coins()

words_to_look_for = utils.get_words_to_look_for()

seconds_before_checking_binance_price = 30

# .05 is 5%
desired_gain_percent = .05

# .03 is 3%
market_max_buy_percent_from_first_order = .03

one_minute_in_milliseconds = 60000


def sell_after_pecentage_gain(bought_price, market, amount):
    sold = False

    while not sold:
        cur_price = binance_utils.get_cur_price_from_large_enough_buy_order(binance, market, amount)
        if utils.percent_change(bought_price, cur_price) > desired_gain_percent:
            sold = binance_utils.market_sell_on_binance(binance, market)
        if not sold:
            time.sleep(seconds_before_checking_binance_price)


class MyStreamListener(tweepy.StreamListener):

    # Called when there is a new status
    def on_status(self, status):
        tweet_time = int(status.timestamp_ms)
        cur_time = int(round(time.time() * 1000))

        # Tweets will queue wile we are waiting to sell
        # and we don't want to buy on old data
        if cur_time - tweet_time < one_minute_in_milliseconds:

            if utils.contains_words_to_look_for(status.text, words_to_look_for):
                coin_name = utils.get_coin_name_in_text(status.text, ignored_coins, binance_coins)

                if coin_name:

                    utils.print_and_write_to_logfile(coin_name + " in tweet: " + status.text)
                    market = binance_coins[coin_name][0]
                    bought, bought_price, amount = binance_utils.market_buy_from_binance(binance, market,
                                                                                         market_max_buy_percent_from_first_order)

                    if bought:
                        sell_after_pecentage_gain(bought_price, market, amount)


# Begin Listening for new Tweets
streamListener = MyStreamListener()
stream = tweepy.Stream(auth, streamListener)
stream.filter(follow=twitter_user_ids_to_follow)
