FROM node:22-alpine AS base

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS development

ENV LANDING_PORT=5174
COPY . .
EXPOSE 5174
# Re-run install on start so named node_modules volumes pick up new deps from package.json.
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0 --port ${LANDING_PORT}"]

FROM base AS build

ARG VITE_FRONTEND_URL=
ENV VITE_FRONTEND_URL=$VITE_FRONTEND_URL

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS production

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/health || exit 1
