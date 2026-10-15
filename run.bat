@echo off
title MITM-DomainFronting and Serverless Controller
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred while running the application.
    pause
)
