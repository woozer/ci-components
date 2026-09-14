FROM docker:29.7.2-cli

RUN apk add --no-cache python3 py3-yaml git openssh-client curl openssl
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python3"]
