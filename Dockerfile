FROM python:3.9-alpine
WORKDIR /home/opc/docker/python

# 필요한 모듈 설치
RUN pip install requests PyJWT
RUN pip install schedule

# api_request_upbit.py 파일 복사
# 호스트의 파일 위치를 첫 번째 인자로, 컨테이너 내의 대상 위치를 두 번째 인자로 설정합니다.
COPY ./apps/upbit/scheduler/routers/api_request_upbit.py /home/opc/docker/python/apps/upbit/scheduler/routers/api_request_upbit.py
COPY ./apps/upbit/scheduler/api_request_scheduler.py /home/opc/docker/python/apps/upbit/scheduler/api_request_scheduler.py

# main.py 파일 추가
ADD main.py .

CMD ["python3", "main.py"]