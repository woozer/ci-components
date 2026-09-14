ARG NODE_IMAGE
ARG MAVEN_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${MAVEN_IMAGE}
COPY --from=node /usr/local/bin/node /usr/local/bin/node
RUN node --version && mvn --version
