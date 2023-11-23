FROM bitnami/kafka:3.1

USER 0
COPY kafka/server.properties /opt/bitnami/kafka/config/server.properties
RUN chmod 664 /opt/bitnami/kafka/config/server.properties
USER 1001
