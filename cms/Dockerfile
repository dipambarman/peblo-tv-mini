FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Run in development mode to match the docker-compose setup
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
