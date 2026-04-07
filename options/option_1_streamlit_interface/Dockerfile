FROM python:3.12-slim

WORKDIR /app

COPY options/option_1_streamlit_interface/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY options/option_1_streamlit_interface/streamlit_app.py .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
