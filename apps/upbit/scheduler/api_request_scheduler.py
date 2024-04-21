# start
import apps.upbit.routers.api_request_upbit as api_request_upbit
import schedule
import time

def job():
    market_codes = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    prices = get_upbit_prices(market_codes)
    for market_code in market_codes:
        print(f"{market_code}의 현재 가격: {prices.get(market_code, '정보 없음')} KRW")

schedule.every(10).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)