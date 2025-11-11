FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY streamlit_app.py /app/streamlit_app.py
EXPOSE 8501
CMD ["streamlit","run","/app/streamlit_app.py","--server.port","8501","--server.address","0.0.0.0"]
