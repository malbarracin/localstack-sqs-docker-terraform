package io.event.listener.config;

import java.net.URI;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Collection;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.messaging.Message;

import io.awspring.cloud.sqs.config.SqsMessageListenerContainerFactory;
import io.awspring.cloud.sqs.listener.acknowledgement.AcknowledgementResultCallback;
import io.awspring.cloud.sqs.listener.acknowledgement.handler.AcknowledgementMode;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.sqs.SqsAsyncClient;

@Configuration
public class SqsConfig {

	private static final Logger LOGGER = LoggerFactory.getLogger(SqsConfig.class);


	@Bean
	@Profile("localstack")
	SqsAsyncClient sqsAsyncClient() {
		return SqsAsyncClient.builder()
				.endpointOverride(URI.create("http://localhost:4566")) // Apunta a LocalStack
				.region(Region.US_EAST_1)
				.credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("test", "test")))
				.build();
	}

	@Bean
	SqsMessageListenerContainerFactory<Object> defaultSqsListenerContainerFactory(SqsAsyncClient sqsAsyncClient) {
		return SqsMessageListenerContainerFactory.builder()
				.configure(options -> options.acknowledgementMode(AcknowledgementMode.MANUAL)
						.acknowledgementInterval(Duration.ofSeconds(3)) 
						.acknowledgementThreshold(0))
				.acknowledgementResultCallback(new AckResultCallback()).sqsAsyncClient(sqsAsyncClient).build();
	}

	static class AckResultCallback implements AcknowledgementResultCallback<Object> {

		@Override
		public void onSuccess(Collection<Message<Object>> messages) {
			LOGGER.info("Ack with success at {}", OffsetDateTime.now());
		}

		@Override
		public void onFailure(Collection<Message<Object>> messages, Throwable t) {
			LOGGER.error("Ack with fail", t);
		}
	}
}
