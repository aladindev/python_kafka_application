import sys
import os

# 현재 스크립트의 위치를 기준으로 모듈 경로를 설정합니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.join(current_dir, 'apps/upbit/scheduler/routers')
sys.path.append(module_path)

import routers.api_request_upbit as api_request_upbit
import schedule
import time

def job():
    market_codes = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    prices = api_request_upbit.get_upbit_prices(market_codes)
    for market_code in market_codes:
        print(f"{market_code}의 현재 가격: {prices.get(market_code, '정보 없음')} KRW")

schedule.every(10).seconds.do(job)

while True:
    print("scheduler start")
    schedule.run_pending()
    time.sleep(1)