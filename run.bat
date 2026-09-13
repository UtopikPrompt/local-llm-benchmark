@echo off
REM
REM Launch the Local LLM Benchmark dashboard from the project root.
REM
REM Windows launcher. The POSIX `run` script (sh) is used on Linux and macOS.
REM
REM Usage:
REM   run                       # dashboard on 127.0.0.1:8000
REM   run --host 0.0.0.0 --port 8000
REM   run --config config.yaml --serve
REM
REM Any flags are forwarded to `python -m local_llm_benchmark`, which defaults
REM to 127.0.0.1:8000 when none are given.
REM

cd /d "%~dp0"
python -m local_llm_benchmark %*
