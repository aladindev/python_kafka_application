import requests

def get_upbit_price(market):
    """
    Upbit에서 특정 마켓의 현재 가격을 조회합니다.
    
    :param market: 조회할 마켓의 코드 (예: KRW-BTC)
    :return: 현재 가격 정보
    """
    url = f"https://api.upbit.com/v1/ticker?markets={market}"
    response = requests.get(url)
    
    if response.status_code == 200:
        result = response.json()
        if result:
            return result[0]['trade_price']
        else:
            return "결과가 없습니다."
    else:
        return "API 요청에 실패했습니다."

# 예제 사용 방법
market_code = "KRW-BTC"  # KRW-BTC 마켓 코드
price = get_upbit_price(market_code)
print(f"{market_code}의 현재 가격: {price} KRW")