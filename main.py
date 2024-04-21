import subprocess
import os


#subprocess.run(["python3", "apps/upbit/scheduler/routers/api_request_upbit.py"])
result = subprocess.run(["python3", "apps/upbit/scheduler/api_request_scheduler.py"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)