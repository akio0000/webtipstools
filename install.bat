@echo off
git clone https://github.com/akio0000/webtipstools.git
cd webtipstools
python -m venv venv
call venv\scripts\activate
python -m pip install --upgrade pip
pip install streamlit
streamlit run main.py
