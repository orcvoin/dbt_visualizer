FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    graphviz \
    graphviz-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY generate_scheme.py .
COPY app.py .

ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8082"]