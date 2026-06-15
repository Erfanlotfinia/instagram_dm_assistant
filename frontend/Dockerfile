FROM node:22-alpine AS runtime

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
# Re-run install on start so named node_modules volumes pick up new deps from package.json.
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0 --port 5173"]
