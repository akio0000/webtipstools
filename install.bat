@echo off
git clone https://github.com/akio0000/webtipstools.git
cd webtipstools
python -m venv venv
call venv\scripts\activate
python -m pip install --upgrade pip
pip install streamlit

echo @echo off > run.bat
echo cd /d %%~dp0 >> run.bat
echo call venv\Scripts\activate >> run.bat
echo streamlit run main.py >> run.bat
echo pause >> run.bat

streamlit run main.py
