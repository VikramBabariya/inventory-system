# ------------------------------------------------------
# STAGE 1: The Builder (Node.js)
# This stage installs dependencies and compiles React
# ------------------------------------------------------
FROM node:24.13-alpine as builder

WORKDIR /app

# Copy package files first (to cache npm install)
COPY package.json package-lock.json ./
RUN npm ci 

# Copy source code and build
COPY . .
RUN npm run build

# ------------------------------------------------------
# STAGE 2: The Runner (Nginx)
# This stage is tiny. It only has the final files.
# ------------------------------------------------------
FROM nginx:alpine as runner

# Copy the custom config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the "dist" folder from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 (Standard Web Port)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]