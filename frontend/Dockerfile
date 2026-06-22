FROM node:22-alpine AS base

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS development

COPY . .
EXPOSE 5173
# Re-run install on start so named node_modules volumes pick up new deps from package.json.
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0 --port 5173"]

FROM base AS build

ARG VITE_API_BASE_URL=
ARG VITE_LANDING_URL=
ARG VITE_PUBLIC_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_LANDING_URL=$VITE_LANDING_URL \
    VITE_PUBLIC_API_BASE_URL=$VITE_PUBLIC_API_BASE_URL

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS production

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/health || exit 1
