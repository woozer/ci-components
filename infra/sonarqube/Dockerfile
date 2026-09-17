ARG NODE_IMAGE
ARG MAVEN_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${MAVEN_IMAGE}
COPY --from=node /usr/local/bin/node /usr/local/bin/node
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/report_api.py scripts/sonar_report.py scripts/dependency_report.py /opt/ci/
RUN node --version && mvn --version && python3 -m compileall -q /opt/ci
