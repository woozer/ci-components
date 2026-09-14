# Build assets with npm ci && npm run build before building this image.
ARG BASE_IMAGE=nginxinc/nginx-unprivileged:stable-alpine@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
FROM ${BASE_IMAGE}
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY dist/animals-ui/browser/ /usr/share/nginx/html/
ENV BACKEND_URL=http://hello-world:8080 \
    NGINX_ENVSUBST_OUTPUT_DIR=/tmp \
    NGINX_ENVSUBST_FILTER=^BACKEND_URL$
EXPOSE 8080
