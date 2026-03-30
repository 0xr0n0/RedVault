FROM node:20-alpine

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
RUN if [ -n "$HTTP_PROXY" ]; then \
      npm config set proxy "$HTTP_PROXY" && \
      npm config set https-proxy "${HTTPS_PROXY:-$HTTP_PROXY}"; \
    fi

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
