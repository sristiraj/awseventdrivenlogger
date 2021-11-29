import json
import boto3
import os
import logging
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import base64
import gzip


aws_region = os.environ.get('AWS_REGION')
notify_config_path =  os.environ.get('NOTIFY_CONFIG_PATH')

s3_bucket_index = notify_config_path.replace("s3://","").find("/")
s3_bucket = notify_config_path[5:s3_bucket_index+5]
s3_key = notify_config_path[s3_bucket_index+6:]
ses_client = boto3.client('ses',region_name=aws_region)
s3 = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def exception_handler(e):
    # exception to status code mapping goes here...
    status_code = e.response['ResponseMetadata']['HTTPStatusCode']
    return {
        'HTTPStatusCode': status_code,
        'error_message': json.dumps(str(e))
    }
    
def response_handler(response):
    status_code = response['ResponseMetadata']['HTTPStatusCode']
    return {
         'HTTPStatusCode': status_code,
         'error_message': "",
         'body' : json.dumps(str(response))
    }

def details(payload):
    message = ""
    log_events = payload['logEvents']
    logger.debug(payload)
    loggroup = payload['logGroup']
    logstream = payload['logStream']
    logger.debug(f'LogGroup: {loggroup}')
    logger.debug(f'Logstream: {logstream}')
    logger.debug(log_events)
    for log_event in log_events:
        message += log_event['message']
    logger.debug('Message: %s' % message.split("\n"))
    return loggroup, logstream, message    

def send_email_notification(content):
    
    response = ""
    try:
        content_notify = content["awslogs"]["data"]
        print(content_notify)
        compressed_payload = base64.b64decode(content_notify)
        uncompressed_payload = gzip.decompress(compressed_payload)
        log_payload = json.loads(uncompressed_payload)
        print(log_payload)
        lgroup, lstream, message = details(log_payload)

        # bucket = s3.Bucket(s3_bucket)
        # objs = list(bucket.objects.filter(Prefix=s3_key))
        objs = s3.list_objects(Bucket=s3_bucket, Prefix=s3_key)
        print(objs)
        for obj in objs["Contents"]:
            bucket = s3_bucket
            key = obj["Key"]
            if "." in key:
                content_object = s3.get_object(Bucket=s3_bucket, Key=key)
                try:
                    file_content = content_object['Body'].read().decode('utf-8')
                    json_content = json.loads(file_content)
                except Exception as e:
                    json_content = {"service_arn":"unknown-json"}
                    pass
                
                if json.loads(message)["service_arn"]==json_content["ServiceArn"]:
                    
                    email_subject = "Automated notification mail: AWS Data Jobs: "+ json_content["ServiceArn"]
                    print(email_subject)
                    receipient_email = json_content["ReceiverEmail"]
                    sender_email = json_content["SenderEmail"]
                    receipient_emails = ", ".join(json_content["ReceiverEmail"])
                    
                    logger.info("************************Send email notification method - Begin****************************")
            
                    BODY_HTML = """\
                    <html>
                    <head>
                    <style> 
                      table, th, td {{ border: 1px solid black; border-collapse: collapse; }}
                      th, td {{ padding: 5px; }}
                    </style>
                    </head>
                    <body>
                    <p>This is auto generated email. Please do not reply back.</p>
                    <table border="1">
                    """
                    BODY_HTML += "<tr><td>"+message+"</td></tr>"
                    BODY_HTML += "</table></body></html>"
            
                    print(f"***********************Body HTML is {BODY_HTML}**************************")
                    
                    print(f"****************email subject is {email_subject}")
                    print(f"****************sender_email is {sender_email}")
                    print(f"****************receipient_email is {receipient_emails}")
                   
                    # Create a multipart/mixed parent container.
                    msg = MIMEMultipart('mixed')
                    
                    
                    # Add subject, from and to lines.
                    msg['Subject'] = email_subject
                    msg['From'] = sender_email
                    msg['To'] = ", ".join(receipient_email)
            
                    # Create a multipart/alternative child container.
                    msg_body = MIMEMultipart('alternative')
                    # The character encoding for the email.
                    CHARSET = "utf-8"
                    BODY_HTML = BODY_HTML.replace("{","[")
                    BODY_HTML = BODY_HTML.replace("}","]")
                    BODY_HTML = BODY_HTML.format(tablefmt="html")
                    # Encode the HTML content and set the character encoding. This step is
                    # necessary if you're sending a message with characters outside the ASCII range.
                    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)        
                    # Add the text and HTML parts to the child container.
                    msg_body.attach(htmlpart)
                    
                    # Attach the multipart/alternative child container to the multipart/mixed
                    # parent container.
                    msg.attach(msg_body)
                    
                    #print(f"*******Type is {type(subject_area_receipient_email)}****************************")
                    #print("msg is: " + str(msg))
                    try:
                        #Provide the contents of the email.
                        response = ses_client.send_raw_email(
                            Source=sender_email,
                            Destinations=receipient_email,
                            RawMessage={'Data':msg.as_string()}
                            )
                        
                    # Display an error if something goes wrong.	
                    except ClientError as e:
                        logger.error(f"**************************[Failed] in send_email_notification {str(e)} ***********************")
                        raise e
                    else:
                        print(f"**********************************Email sent! Message ID: {response['MessageId']} ***********************************")

    except Exception as e:
        logger.error("**************************[Failed] in send_email_notification ***********************")
        raise Exception("***********************************Failed send_email_notification: " + str(e))
    return response_handler(response)


def lambda_handler(event, context):
    message_dict = {}
    notification_dict = {}
    item_dict = {}
    print(f"********Event is {event}************")
    
    response = send_email_notification(event)
            
    return {"result":response}
      

    
