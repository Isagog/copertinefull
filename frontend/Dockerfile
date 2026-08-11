# Base image for Node.js
FROM node:20-alpine AS base

# Install pnpm. The version comes from the "packageManager" field in
# package.json — without that pin corepack resolves to whatever pnpm is
# newest at build time, which is how this image stopped building: pnpm 11
# cannot be loaded by the corepack bundled in node:20-alpine.
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build application
RUN pnpm build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# The image is self-contained: the old mema3 compose supplied
# `command: ["node", "server.js"]` and the three env vars below, so the image
# could not be run without that file. Under Dokploy the compose carries no
# `command:` and no `environment:` (the x-app anchor forbids it), so the
# defaults have to live here.
#
# HOSTNAME=0.0.0.0 is not cosmetic: Next's standalone server binds localhost by
# default, which inside a container means nothing outside it — including Traefik
# — can reach the port.
EXPOSE 3000
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
