from binance.websockets import BinanceSocketManager
import binance_utils


binance = binance_utils.get_binance_account()



def process_message(msg):
    print("message type: {}".format(msg['e']))
    print(msg)
    price = msg['p']
    print("CURRENT PRICE: " + price + "\n")


bm = BinanceSocketManager(binance)
# start any sockets here, i.e a trade socket
conn_key = bm.start_trade_socket('XLMBTC', process_message)
# then start the socket manager
bm.start()