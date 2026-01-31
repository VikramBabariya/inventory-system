# frontend/Dockerfile
# Base image - using full Node version (Heavy)
FROM node:24.13

# Set working directory
WORKDIR /app

# Copy package files first (for caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose the Vite default port
EXPOSE 5173

# Start the dev server
CMD ["npm", "run", "dev", "--", "--host"]