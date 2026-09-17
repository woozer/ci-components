ARG NODE_IMAGE
ARG MAVEN_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${MAVEN_IMAGE}
COPY --from=node /usr/local/bin/node /usr/local/bin/node
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/sonar_report.py /opt/ci/sonar_report.py
RUN node --version && mvn --version && python3 -m py_compile /opt/ci/sonar_report.py
