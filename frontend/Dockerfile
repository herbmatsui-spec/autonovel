# AutoNovel Frontend Dockerfile
# Step 62: dev は vite、production は nginx で静的配信。

# ---- base: 共通ビルド ----
FROM node:20-slim AS base
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund --legacy-peer-deps
COPY . .

# ---- dev: 開発サーバ ----
FROM base AS dev
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- builder: 本番ビルド ----
FROM base AS builder
RUN npm run build

# ---- production: nginx 配信 ----
FROM nginx:1.27-alpine AS production
# ビルド成果物を nginx の公開ディレクトリへ配置
COPY --from=builder /app/dist /usr/share/nginx/html
# バックエンドへの逆プロキシ設定 (docker-compose 環境では network alias "backend" を利用)
RUN printf 'server {\n\
  listen 80;\n\
  server_name _;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
\n\
  location / {\n\
    try_files $uri /index.html;\n\
  }\n\
\n\
  location ~ ^/(easy_mode|api|editor|graph|health|metrics|plots|episodes|books|tasks) {\n\
    proxy_pass http://backend:8200;\n\
    proxy_http_version 1.1;\n\
    proxy_set_header Upgrade $http_upgrade;\n\
    proxy_set_header Connection "upgrade";\n\
    proxy_set_header Host $host;\n\
    proxy_set_header X-Real-IP $remote_addr;\n\
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
    proxy_set_header X-Forwarded-Proto $scheme;\n\
    proxy_read_timeout 86400s;\n\
    proxy_send_timeout 86400s;\n\
  }\n\
}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
