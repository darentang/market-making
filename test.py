import asyncio
from binance import AsyncClient, BinanceSocketManager
from pprint import pprint

async def main():
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    # start any sockets here, i.e a trade socket
    ts = bm.depth_socket("BNBBTC", depth=10, interval=100)
    # then start receiving messages
    async with ts as tscm:
        while True:
            res = await tscm.recv()
            pprint(res)

    await client.close_connection()

if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())