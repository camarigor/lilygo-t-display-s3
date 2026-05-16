FROM alpine:3
WORKDIR /seed
COPY umbrel-store-checkout/camarigor-tdisplay-stack/telegraf-broker.conf .
COPY umbrel-store-checkout/camarigor-tdisplay-stack/telegraf-router.conf .
COPY umbrel-store-checkout/camarigor-tdisplay-stack/nginx.conf .
COPY tdisplay-init/seed.sh /seed.sh
RUN chmod +x /seed.sh
ENTRYPOINT ["/seed.sh"]
CMD ["/app-data"]
