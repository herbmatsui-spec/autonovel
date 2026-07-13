FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install packages inside the container
RUN npm install --no-audit --no-fund

# Copy the rest of the source code
COPY . .

EXPOSE 5173

# Start the Vite dev server bound to 0.0.0.0
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
