import subprocess
import os


subprocess.run(["python3", "apps/upbit/scheduler/routers/api_request_upbit.py"])
subprocess.run(["python3", "apps/upbit/scheduler/api_request_scheduler.py"])
