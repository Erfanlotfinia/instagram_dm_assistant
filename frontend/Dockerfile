FROM node:22-alpine AS runtime

WORKDIR /app
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
