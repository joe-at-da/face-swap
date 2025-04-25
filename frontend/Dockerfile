FROM node:18-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the application
# RUN npm run build  # Uncomment for production build

# Expose port
EXPOSE 3000

# Command to run the application in development mode
CMD ["npm", "run", "dev"]
