FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install streamlit pandas psycopg[binary] pillow

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
