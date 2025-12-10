FROM node:20-alpine

# Install Playwright system dependencies
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    && rm -rf /var/cache/apk/*

# Set up user for security
RUN addgroup -g 1001 -S playwright && \
    adduser -S playwright -u 1001

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci --only=production

# Install Playwright browsers
RUN npx playwright install chromium --with-deps

# Copy source code
COPY src/ ./src/

# Build the application
RUN npm run build

# Create profiles directory
RUN mkdir -p /app/profiles && chown -R playwright:playwright /app/profiles

# Switch to non-root user
USER playwright

# Expose port for debugging
EXPOSE 9222

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "console.log('OK')"

# Run the application
CMD ["npm", "start"]