# GPN21 Tron Racer
A bot for the GPN21 Tron Racer game.

The game viewer was accessible at
https://gpn-tron.duckdns.org:3000 but is now offline.

The code for the server side is available at
https://github.com/freehuntx/gpn-tron

This Bot uses some simple heuristics to find safe and promising moves, and then runs some minmaxing to find the best move.

## Requirements
- Python 3.9
- setuptools
- pybind11
- c++ compiler

## Installation
```bash
pip3 install . 
```

## Usage
```bash
python3 Tron.py
```
