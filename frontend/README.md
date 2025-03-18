# TrendPup Frontend

Chat interface for the TrendPup AI assistant.

## Features

- Real-time chat with AI assistant
- WebSocket communication with backend agent
- Responsive UI using Tailwind CSS

## Getting Started

1. Install dependencies:

```bash
pnpm install
```

2. Build the application:

```bash
pnpm build
```

3. Start the production server:

```bash
pnpm start
```

Or run in development mode:

```bash
pnpm dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

## WebSocket Communication

The frontend communicates with the backend agent via WebSocket connection on port 8080. Make sure the backend server is running before starting the frontend.

## Configuration

- `next.config.js`: Next.js configuration
- `tailwind.config.js`: Tailwind CSS configuration
- `postcss.config.js`: PostCSS configuration

## Running the Server

TrendPup uses Next.js with nginx for HTTPS and WebSocket proxying:

1. **Start the Next.js server:**
   ```bash
   # Build and start the server
   pnpm run build
   pnpm start
   ```
   This will start Next.js on port 3000.

2. **Access the app:**
   The application is available at https://trendpup.duckdns.org

## Nginx Configuration

The application runs behind nginx which:
- Handles HTTPS/SSL encryption
- Proxies HTTP requests to the Next.js server on port 3000
- Proxies WebSocket connections at `/ws` to the backend WebSocket server on port 8080

```nginx
# Main configuration at /etc/nginx/sites-enabled/trendpup.conf
server {
    listen 443 ssl;
    server_name trendpup.duckdns.org;

    # Frontend proxy
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```
