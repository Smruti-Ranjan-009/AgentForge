FROM python:3.11-slim

WORKDIR /workspace
COPY . /workspace
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

ENV BACKEND_URL=http://localhost:8000
CMD ["bash"]
