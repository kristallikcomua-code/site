#!/usr/bin/env python3
# Entry point for Telegram bot (Railway worker service)
import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
subprocess.run([sys.executable, "inventory/bot.py"])
