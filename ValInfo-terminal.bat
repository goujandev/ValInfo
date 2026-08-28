@echo off
title ValInfo
cd /d "%~dp0"
python -m valinfo live
if errorlevel 1 pause
