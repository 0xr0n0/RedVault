FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Configure apt proxy if provided via build args
ARG HTTP_PROXY
ARG HTTPS_PROXY
RUN if [ -n "$HTTP_PROXY" ]; then \
      echo "Acquire::http::Proxy \"$HTTP_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf && \
      echo "Acquire::https::Proxy \"${HTTPS_PROXY:-$HTTP_PROXY}\";" >> /etc/apt/apt.conf.d/proxy.conf; \
    fi

# Install system deps: psycopg2, pandoc (markdown→typst), curl/xz for typst download
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev pandoc curl xz-utils fonts-liberation2 && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/apt/apt.conf.d/proxy.conf

# Install Typst (PDF typesetting engine)
ARG TYPST_VERSION=0.12.0
ARG TARGETARCH=amd64
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then TYPST_ARCH="x86_64-unknown-linux-musl"; \
    elif [ "$ARCH" = "arm64" ]; then TYPST_ARCH="aarch64-unknown-linux-musl"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi && \
    curl -fsSL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${TYPST_ARCH}.tar.xz" \
      -o /tmp/typst.tar.xz && \
    tar xf /tmp/typst.tar.xz -C /tmp && \
    cp /tmp/typst-${TYPST_ARCH}/typst /usr/local/bin/ && \
    chmod +x /usr/local/bin/typst && \
    rm -rf /tmp/typst*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
