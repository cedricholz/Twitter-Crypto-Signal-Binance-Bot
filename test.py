from binance.websockets import BinanceSocketManager
import binance_utils
import time
from twisted.internet import reactor

binance = binance_utils.get_binance_account()

count = 1



def do():
    def process_message(msg):
        global count
        count += 1

        print(count)

        print("message type: {}".format(msg['e']))
        print(msg)
        price = msg['p']
        print("CURRENT PRICE: " + price + "\n")

        reactor.stop()

    bm = BinanceSocketManager(binance)

    conn_key = bm.start_trade_socket('XLMBTC', process_message)
    bm.run()

    print("Done")

do()