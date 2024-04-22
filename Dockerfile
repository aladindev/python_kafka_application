FROM python:3.9-alpine
WORKDIR /home/opc/docker/python

# 필요한 모듈 설치
RUN pip install requests PyJWT schedule
RUN pip install confluent-kafka

# api_request_upbit.py 파일과 api_request_scheduler.py 파일 복사
COPY ./apps/upbit/scheduler/routers/api_request_upbit.py /home/opc/docker/python/apps/upbit/scheduler/routers/api_request_upbit.py
COPY ./apps/upbit/scheduler/api_request_scheduler.py /home/opc/docker/python/apps/upbit/scheduler/api_request_scheduler.py

# PYTHONPATH 환경 변수 설정
ENV PYTHONPATH "${PYTHONPATH}:/home/opc/docker/python"

CMD ["python3", "/home/opc/docker/python/apps/upbit/scheduler/api_request_scheduler.py"]
