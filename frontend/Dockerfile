FROM node:20-alpine AS builder
WORKDIR /app

# Cache dependencies unless package metadata changes.
COPY package*.json ./
RUN npm ci

# Copy app sources after installing deps.
COPY . .

ARG NEXT_PUBLIC_API_HOST
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_HOST=$NEXT_PUBLIC_API_HOST \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
