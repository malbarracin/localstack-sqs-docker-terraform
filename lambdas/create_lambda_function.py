import json
import boto3
import os
from datetime import datetime
import uuid

def lambda_handler(event, context):
    try:
        # Inicializamos Variables
        path = event['path']
        print("Event: ", event)
        print("Path: ", path)

        # Obtener el timestamp en formato ISO 8601
        timestamp = datetime.now().isoformat()

        # Verificar el contenido de requestContext
        print("RequestContext: ", event.get('requestContext'))

        # Obtener el eventId, generar uno si no existe
        eventId = event.get('requestContext', {}).get('requestId', str(uuid.uuid4()))
        print("EventId: ", eventId)

        errors = [
            {
                "code": "500",
                "message": "System Events Unavailable"
            }
        ]

        error = {
            "timestamp": timestamp,
            "path": path,
            "description": "System Events Unavailable",
            "errors": errors
        }
        bodyResponseErrorStr = json.dumps(error)

        # Conectar a DynamoDB
        try:
            dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('DYNAMODB_ENDPOINT', 'http://host.docker.internal:4566'))
            table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'messages'))
            print("Conectado a DynamoDB...")
        except Exception as e:
            print("Error conectando a DynamoDB:", e)
            return {
                "isBase64Encoded": 'false',
                "statusCode": 500,
                "body": bodyResponseErrorStr
            }

        # Obtener el cuerpo del evento
        print(json.dumps(event['body']))
        objeto_json = json.loads(event['body'])
        print(json.dumps(objeto_json))

        eventId = event['requestContext']['requestId']
        print("EventId: ", eventId)

        # Crear el timestamp actual en formato ISO 8601
        creationDate = datetime.now().isoformat()

        statusHistoryPending = [{
            "creationDate": creationDate,
            "status": "PENDING",
            "stage": "INITIAL"
        }]

        # Crear el cuerpo del mensaje para DynamoDB
        bodyDynamoDB = {
            "eventId": eventId,
            "creationDate": creationDate,  # Ya es un string, no necesita isoformat()
            "apiRequest": json.dumps(objeto_json),
            "retries": 0,
            "statusHistory": statusHistoryPending
        }

        print("BodyDynamoDB Pending: ", bodyDynamoDB)

        try:
            # Insertar el nuevo registro en la tabla DynamoDB
            response = table.put_item(Item=bodyDynamoDB)
            print("DynamoDB Insert Response: ", response)
        except Exception as e:
            print("Error insertando en DynamoDB:", e)
            return {
                "isBase64Encoded": 'false',
                "statusCode": 500,
                "body": bodyResponseErrorStr
            }

        # Obtener el endpoint URL desde las variables de entorno
        endpoint_url = os.environ.get('ENDPOINT_URL', 'http://host.docker.internal:4566')
        queue_name = os.environ['QUEUE_NAME']

        # Crear el cliente de SQS
        sqs = boto3.client('sqs', endpoint_url=endpoint_url, region_name='us-east-1')

        # Obtener la URL de la cola
        queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']

        # Enviar el mensaje a la cola SQS con el ID del registro en DynamoDB
        message_body = {
            "dynamodb_record_id": eventId,
            "event": event
        }
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageGroupId="default",
            MessageDeduplicationId=eventId  # Usa un ID único para la deduplicación
        )

        # Actualizar el estado en DynamoDB (opcional)
        try:
            table.update_item(
                Key={'eventId': eventId},
                UpdateExpression="SET #status = :new_status",
                ExpressionAttributeNames={"#status": "statusHistory"},
                ExpressionAttributeValues={":new_status": [{"creationDate": creationDate, "status": "INIT", "stage": "PROCESSED"}]}
            )
            print("Registro en DynamoDB actualizado con el estado 'INIT'")
        except Exception as e:
            print("Error actualizando el registro en DynamoDB:", e)

        return {
            'isBase64Encoded': False,
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Message sent to SQS and DynamoDB record created',
                'sqs_response': response,
                'dynamodb_record_id': eventId
            })
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'isBase64Encoded': False,
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': str(e)
            })
        }
