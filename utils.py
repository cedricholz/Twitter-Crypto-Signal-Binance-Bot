import json
from datetime import datetime
import tweepy
from tweepy import OAuthHandler
import urllib


def get_set_from_file(filename):
    with open(filename, 'r') as f:
        file_contents = json.loads(f.read())

    return set(file_contents)


def get_ignored_coins():
    return get_set_from_file('ignored_coins.txt')


def get_words_to_look_for():
    return get_set_from_file('words_to_look_for.txt')


def contains_words_to_look_for(status_text, words_to_look_for):
    lower_status = status_text.lower()
    for word in words_to_look_for:
        if word in lower_status:
            return True
    return False


def get_coin_name_in_text(status_text, ignored_coins, binance_coins):
    lower_status = status_text.lower()
    for symbol in binance_coins:
        pound_symbol_coin = "#" + symbol
        dollar_symbol_coin = "$" + symbol

        if symbol not in ignored_coins and (pound_symbol_coin in lower_status or dollar_symbol_coin in lower_status):
            return symbol
    return None


def query_url(url_addr):
    with urllib.request.urlopen(url_addr) as url:
        return json.loads(url.read().decode())


def get_twitter_account():
    with open("twitter_secrets.json") as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()

    consumer_key = secrets['consumer_key']
    consumer_secret = secrets['consumer_secret']
    access_token = secrets['access_token_key']
    access_secret = secrets['access_token_secret']

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)

    return tweepy.API(auth), auth


def get_date_time():
    now = datetime.now()
    return "%s:%s:%s %s/%s/%s" % (now.hour, now.minute, now.second, now.month, now.day, now.year)


def print_and_write_to_logfile(log_text):
    timestamp = '[' + get_date_time() + '] '
    log_text = timestamp + log_text
    if log_text is not None:
        print(log_text)

        with open('logs.txt', 'a') as myfile:
            myfile.write(log_text + '\n')


def percent_change(bought_price, cur_price):
    if bought_price == 0:
        return 0

    return 100 * (cur_price - bought_price) / bought_price
