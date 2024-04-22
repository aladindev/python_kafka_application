FROM python:3.9-alpine
WORKDIR /home/opc/docker/python

# 필요한 모듈 설치
RUN pip install requests PyJWT schedule

# librdkafka 설치
RUN apk update && apk add --no-cache \
    gcc \
    g++ \
    libc-dev \
    librdkafka-dev \
    python3-dev

# confluent-kafka 설치
RUN pip install confluent-kafka

# api_request_upbit.py 파일과 api_request_scheduler.py 파일 복사
COPY ./apps/upbit/scheduler/routers/api_request_upbit.py /home/opc/docker/python/apps/upbit/scheduler/routers/api_request_upbit.py
COPY ./apps/upbit/scheduler/api_request_scheduler.py /home/opc/docker/python/apps/upbit/scheduler/api_request_scheduler.py

# PYTHONPATH 환경 변수 설정
ENV PYTHONPATH "${PYTHONPATH}:/home/opc/docker/python"
# docker run 컨테이너 구동 시 -e 인자 전달로 override.
ENV KAFKA_SERVER_ADDRESS=localhost:9091

# 스케줄러 직접 실행으로 변경 main->api_request_scheduler.py
CMD ["python3", "/home/opc/docker/python/apps/upbit/scheduler/api_request_scheduler.py"]
