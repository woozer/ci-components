# Match the Playwright Java dependency in the sample integration-tests module.
FROM maven@sha256:4f82a03a7d6679281952d628131299b1be88d7030a49c6a2b7d2ba2642e44e3e AS java
FROM mcr.microsoft.com/playwright/java:v1.62.0-noble@sha256:8c3c9d7c611c24ec695fd396aad1f1957bb4943a429687ea269e3c63b3e6c0bd
COPY --from=java /opt/java/openjdk /opt/java/openjdk
COPY --from=java /usr/share/maven /usr/share/maven
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:/usr/share/maven/bin:${PATH}"
