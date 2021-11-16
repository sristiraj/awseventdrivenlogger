Lambda takes one environment variable: NOTIFY_CONFIG_PATH
This is path where the notification json should be placed

The framework works on job (glue/lambda) - Mapping to notification json - which maps to cloud watch alarm - which is tagged to cloudwatch log metric on a log group 
