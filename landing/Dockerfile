FROM node:22-alpine AS runtime

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV LANDING_PORT=5174
EXPOSE 5174

CMD ["sh", "-c", "npm run dev -- --host 0.0.0.0 --port ${LANDING_PORT}"]
