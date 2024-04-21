FROM python:3.9-alpine
WORKDIR /home/opc/docker/python
# requests 모듈 설치
RUN pip install requests PyJWT
RUN pip install schedule
#ADD upbit.py .
ADD api_request_test.py .

CMD ["python3", "main.py"]