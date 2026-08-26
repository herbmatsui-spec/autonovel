FROM node:22-alpine AS dev

WORKDIR /app

COPY package*.json ./
RUN npm install --legacy-peer-deps --no-audit --no-fund

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build Stage (コンパイル確認 & 成果物生成)
FROM base AS builder
COPY . .
RUN rm -rf /app/node_modules && npm cache clean --force && npm install --legacy-peer-deps --no-audit --no-fund
RUN npm run build

# Production Stage (Nginx)
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]