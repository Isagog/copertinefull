# copertine-images — nginx serving the cover archive off a Docker volume.
#
# On mema3 this job was done by a `location /images/` block in the host
# dev.isagog.com vhost, aliased straight at /home/mema/code/copertinefull/images.
# Under Dokploy there is no host vhost — Traefik is the only ingress and it
# routes to containers, so the static files need a server of their own.
#
# The config is BAKED IN rather than bind-mounted from the deployment repo on
# purpose: Dokploy re-clones that repo on every deploy, and a bind mount taken
# against the old directory keeps resolving to the now-unlinked inode. That
# failure is documented in isagog-platform-dokploy/.claude/temporal.md — it is
# how Temporal's dynamic config silently stopped applying.
FROM nginx:1.29-alpine

COPY images.conf /etc/nginx/conf.d/default.conf

# Read-only rootfs friendly: nginx needs these to exist and be writable, and
# the compose file mounts tmpfs over them.
RUN mkdir -p /var/cache/nginx /var/run \
    && chown -R nginx:nginx /var/cache/nginx

EXPOSE 80
