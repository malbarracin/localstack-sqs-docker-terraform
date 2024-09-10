FROM eclipse-temurin:21-jre-alpine
VOLUME /tmp
COPY *.jar app.jar
ENTRYPOINT ["sh", "-c", "java ${JAVA_OPTS} -jar /app.jar"]
