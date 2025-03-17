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
