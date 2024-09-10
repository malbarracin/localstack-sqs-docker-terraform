provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true  # No requiere ID de cuenta
  endpoints {
    dynamodb       = "http://host.docker.internal:4566"
    apigateway     = "http://host.docker.internal:4566"
    sqs            = "http://host.docker.internal:4566"
    lambda         = "http://host.docker.internal:4566"
  }
}

# Crear la tabla DynamoDB
resource "aws_dynamodb_table" "messages" {
  name         = "messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "eventId"

  attribute {
    name = "eventId"
    type = "S"
  }
}

# Crear la cola SQS FIFO sin redrive policy
resource "aws_sqs_queue" "message_queue" {
  name       = "message-to-sqs.fifo"
  fifo_queue = true
}

# Output para obtener la URL de la cola SQS
output "sqs_queue_url" {
  value = aws_sqs_queue.message_queue.id
}


# Crear la función Lambda para enviar mensajes a SQS
resource "aws_lambda_function" "my_lambda" {
  function_name = "myLambda"
  runtime       = "python3.8"
  handler       = "create_lambda_function.lambda_handler"
  filename      = "../lambdas/create_lambda_function.zip"  # Ruta a tu archivo ZIP Lambda

  role = "arn:aws:iam::000000000000:role/lambda-role"  # ARN ficticio para satisfacer a Terraform

  environment {
    variables = {
      QUEUE_NAME    = "message-to-sqs.fifo"
      ENDPOINT_URL  = "http://host.docker.internal:4566"
    }
  }

  timeout = 30
}


# Crear el API Gateway
resource "aws_api_gateway_rest_api" "my_api" {
  name        = "MyAPI"
  description = "API para enviar mensajes a la cola SQS mediante Lambda"
}

# Crear un recurso /send-message en API Gateway
resource "aws_api_gateway_resource" "send_message_resource" {
  rest_api_id = aws_api_gateway_rest_api.my_api.id
  parent_id   = aws_api_gateway_rest_api.my_api.root_resource_id
  path_part   = "send-message"
}

# Crear el método POST para el recurso /send-message
resource "aws_api_gateway_method" "post_send_message" {
  rest_api_id   = aws_api_gateway_rest_api.my_api.id
  resource_id   = aws_api_gateway_resource.send_message_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

# Integrar el método POST con la función Lambda
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.my_api.id
  resource_id = aws_api_gateway_resource.send_message_resource.id
  http_method = aws_api_gateway_method.post_send_message.http_method
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = aws_lambda_function.my_lambda.invoke_arn
}

# Añadir permisos para que API Gateway invoque Lambda
resource "aws_lambda_permission" "apigateway_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.my_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:000000000000:${aws_api_gateway_rest_api.my_api.id}/*/POST/send-message"
}

# Desplegar el API Gateway en el stage 'test'
resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.my_api.id
  stage_name  = "test"

  depends_on = [
    aws_api_gateway_integration.lambda_integration,
    aws_api_gateway_method.post_send_message
  ]
}

# Output para obtener la URL del API
output "api_url" {
  value = "http://localhost:4566/restapis/${aws_api_gateway_rest_api.my_api.id}/test/_user_request_/send-message"
}