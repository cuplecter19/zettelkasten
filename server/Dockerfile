# 저장소 루트를 빌드 컨텍스트로 사용한다:
#   docker build -f server/Dockerfile -t zettelkasten-sync .
FROM python:3.11-slim

WORKDIR /app

# 서버 소스와 공용 스키마를 복사한다(스키마는 db/ 에 위치).
COPY server/ /app/
COPY db/schema_shared.sql /app/db/schema_shared.sql

RUN pip install --no-cache-dir -r requirements_server.txt
RUN mkdir -p /opt/zettelkasten/pdfs

EXPOSE 8000
CMD ["uvicorn", "main_server:app", "--host", "0.0.0.0", "--port", "8000"]
