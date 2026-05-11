# =============================================================================
# PlantOps Frontend Dockerfile
# =============================================================================
# Vite + React + TypeScript
# =============================================================================

# ---------------------------------------------------------------------------
# Base stage
# ---------------------------------------------------------------------------
FROM node:20-alpine AS base

WORKDIR /app

# ---------------------------------------------------------------------------
# Dependencies stage
# ---------------------------------------------------------------------------
FROM base AS deps

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# ---------------------------------------------------------------------------
# Development stage
# ---------------------------------------------------------------------------
FROM base AS development

ENV NODE_ENV=development
ENV VITE_API_BASE_URL=http://localhost:8000/api

COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# ---------------------------------------------------------------------------
# Build stage
# ---------------------------------------------------------------------------
FROM base AS build

ENV NODE_ENV=production

COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./

RUN npm run build

# ---------------------------------------------------------------------------
# Production stage (served via nginx)
# ---------------------------------------------------------------------------
FROM nginx:alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY infra/nginx/frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
