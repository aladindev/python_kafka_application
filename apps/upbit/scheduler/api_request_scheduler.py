import sys
import os
import routers.api_request_upbit as api_request_upbit
import schedule
import time
import json

from confluent_kafka import Producer

# 환경변수에서 카프카 서버 주소 가져오기
kafka_server = os.getenv('KAFKA_SERVER_ADDRESS', 'default_server_address') #server  -> docker 
# Kafka producer configuration 환경변수 전달 
conf = {'bootstrap.servers': kafka_server}
producer = Producer(**conf)

def delivery_report(err, msg):
    """ 콜백 함수: 메시지 전송 결과를 보고합니다. """
    if err is not None:
        print('Message delivery failed:', err)
    else:
        print('Message delivered to', msg.topic(), msg.partition())

def job():
    market_codes = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    prices = api_request_upbit.get_upbit_prices(market_codes)
    for market_code in market_codes:
        price_info = prices.get(market_code, '정보 없음')
        print(f"{market_code}의 현재 가격: {price_info} KRW")

        # 카프카에 메시지 전송
        key = market_code.encode('utf-8')  # Key를 바이트로 인코딩
        value = json.dumps({'price': price_info}).encode('utf-8')  # Value를 JSON 문자열로 변환 후 바이트로 인코딩
        producer.produce('coin-real-time-price', key=key, value=value, callback=delivery_report)
    
    # 모든 메시지가 전송되었는지 확인
    producer.flush()

schedule.every(20).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)

