FROM node:22-alpine
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm install
COPY server.ts ldap.ts ./
COPY delegation/ ./delegation/
RUN npm run build
CMD ["node", "dist/server.js"]
