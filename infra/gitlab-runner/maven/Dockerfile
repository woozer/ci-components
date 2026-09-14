ARG MAVEN_IMAGE
FROM ${MAVEN_IMAGE}
# only-script Maven Wrapper must extract the exact checksum-pinned ZIP archive.
RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip \
    && rm -rf /var/lib/apt/lists/*
