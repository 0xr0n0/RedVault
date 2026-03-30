#!/bin/sh
# Generate self-signed certificate if it doesn't exist
if [ ! -f /etc/nginx/ssl/selfsigned.crt ]; then
    echo "🔐 Generating self-signed certificate..."
    export http_proxy="${HTTP_PROXY:-}" https_proxy="${HTTPS_PROXY:-}"
    apk add --no-cache openssl || { echo "❌ Failed to install openssl"; exit 1; }
    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/selfsigned.key \
        -out /etc/nginx/ssl/selfsigned.crt \
        -subj "/C=US/ST=Local/L=Local/O=RedVault/CN=localhost"
    echo "✅ Certificate generated."
fi

exec nginx -g 'daemon off;'
