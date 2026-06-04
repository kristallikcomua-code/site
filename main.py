#!/usr/bin/env python3
import os, subprocess, sys

service = os.environ.get("SERVICE_TYPE", "web")

if service == "bot":
    subprocess.run([sys.executable, "inventory/bot.py"])
else:
    subprocess.run([sys.executable, "inventory/app.py"])
