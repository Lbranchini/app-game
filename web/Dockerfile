# syntax=docker/dockerfile:1.6
# Dev-mode container: runs Vite with HMR. Compose mounts src/ on top so a
# host edit reflects immediately in the browser.
FROM node:20-alpine

WORKDIR /app

# Copy manifests first so npm install caches when only sources change.
COPY package.json ./
RUN npm install

COPY . ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
