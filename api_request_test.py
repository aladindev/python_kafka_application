import requests, schedule, time


# venv 가상환경 구성 
def get_upbit_prices(market_codes):
    markets = ",".join(market_codes)  # 마켓 코드를 콤마로 구분된 문자열로 변환
    url = f"https://api.upbit.com/v1/ticker?markets={markets}"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json()
        return {result['market']: result['trade_price'] for result in results}
    return "API 요청에 실패했습니다."

market_codes = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]  # 조회할 마켓 코드 배열
prices = get_upbit_prices(market_codes)
for market_code in market_codes:
    print(f"{market_code}의 현재 가격: {prices.get(market_code, '정보 없음')} KRW")
