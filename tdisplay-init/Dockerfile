# nosemgrep: dockerfile.security.missing-user.missing-user
# Init container: REQUER root pra mkdir/cp em volume bind-mount com ownership
# root (${APP_DATA_DIR}). Compose force `user: "0"` + restart: "no" + only
# runs uma vez. Padrão init container Umbrel.
FROM alpine:3
USER 0
WORKDIR /seed
COPY umbrel-store-checkout/camarigor-tdisplay-stack/telegraf-broker.conf .
COPY umbrel-store-checkout/camarigor-tdisplay-stack/telegraf-router.conf .
COPY umbrel-store-checkout/camarigor-tdisplay-stack/nginx.conf .
COPY tdisplay-init/seed.sh /seed.sh
RUN chmod +x /seed.sh
ENTRYPOINT ["/seed.sh"]
CMD ["/app-data"]
