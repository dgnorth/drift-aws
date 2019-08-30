# Lambda Proxy Integrations in API Gateway

Below is an example of the contents of *event* and *context* parameters in a Python lambda handler for an API Gateway.

## API GW call using private lambda

### Example of *drift-apirouter* calling a proxy lambda:

```json
{
    "event": {
        "resource": "/",
        "path": "/",
        "httpMethod": "GET",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9,is;q=0.8,zh-CN;q=0.7,zh;q=0.6",
            "Cache-Control": "max-age=0",
            "Host": "u9mg6eu01d.execute-api.eu-west-1.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
            "x-amzn-cipher-suite": "ECDHE-RSA-AES128-GCM-SHA256",
            "x-amzn-vpc-id": "vpc-6458d901",
            "x-amzn-vpce-config": "1",
            "x-amzn-vpce-id": "vpce-05d0829ef39b4d2b8",
            "X-Forwarded-For": "10.50.2.99",
            "X-Forwarded-Host": "dg-bobo.dg-api.com",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
            "X-Real-IP": "153.92.155.138",
            "X-Script-Name": "/drift"
        },
        "multiValueHeaders": {
            "Accept": [
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
            ],
            "Accept-Encoding": [
                "gzip, deflate, br"
            ],
            "Accept-Language": [
                "en-US,en;q=0.9,is;q=0.8,zh-CN;q=0.7,zh;q=0.6"
            ],
            "Cache-Control": [
                "max-age=0"
            ],
            "Host": [
                "u9mg6eu01d.execute-api.eu-west-1.amazonaws.com"
            ],
            "Upgrade-Insecure-Requests": [
                "1"
            ],
            "User-Agent": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36"
            ],
            "x-amzn-cipher-suite": [
                "ECDHE-RSA-AES128-GCM-SHA256"
            ],
            "x-amzn-vpc-id": [
                "vpc-6458d901"
            ],
            "x-amzn-vpce-config": [
                "1"
            ],
            "x-amzn-vpce-id": [
                "vpce-05d0829ef39b4d2b8"
            ],
            "X-Forwarded-For": [
                "10.50.2.99"
            ],
            "X-Forwarded-Host": [
                "dg-bobo.dg-api.com"
            ],
            "X-Forwarded-Port": [
                "443"
            ],
            "X-Forwarded-Proto": [
                "https"
            ],
            "X-Real-IP": [
                "153.92.155.138"
            ],
            "X-Script-Name": [
                "/drift"
            ]
        },
        "queryStringParameters": null,
        "multiValueQueryStringParameters": null,
        "pathParameters": null,
        "stageVariables": null,
        "requestContext": {
            "resourceId": "cygui3v0qi",
            "resourcePath": "/",
            "httpMethod": "GET",
            "extendedRequestId": "Q-bp5HPxjoEFmnQ=",
            "requestTime": "26/Nov/2018:15:09:25 +0000",
            "path": "/dev",
            "accountId": "092475124519",
            "protocol": "HTTP/1.1",
            "stage": "dev",
            "domainPrefix": "u9mg6eu01d",
            "requestTimeEpoch": 1543244965750,
            "requestId": "435ab1a9-f18d-11e8-b5d3-fdcc613854fa",
            "identity": {
                "cognitoIdentityPoolId": null,
                "cognitoIdentityId": null,
                "vpceId": "vpce-05d0829ef39b4d2b8",
                "cognitoAuthenticationType": null,
                "userArn": null,
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
                "accountId": null,
                "caller": null,
                "sourceIp": "10.50.2.99",
                "accessKey": null,
                "vpcId": "vpc-6458d901",
                "cognitoAuthenticationProvider": null,
                "user": null
            },
            "domainName": "u9mg6eu01d.execute-api.eu-west-1.amazonaws.com",
            "apiId": "u9mg6eu01d"
        },
        "body": null,
        "isBase64Encoded": false
    },
    "context": {
        "aws_request_id": "435b7522-f18d-11e8-a977-8751f2607bbf",
        "log_group_name": "/aws/lambda/just_a_test",
        "log_stream_name": "2018/11/26/[$LATEST]6d13904cc8494c95b5e69d6f8e5d9b34",
        "function_name": "just_a_test",
        "memory_limit_in_mb": "128",
        "function_version": "$LATEST",
        "invoked_function_arn": "arn:aws:lambda:eu-west-1:092475124519:function:just_a_test",
        "client_context": null,
        "identity": "<CognitoIdentity object>"
    }
}
```




## API GW call using public lambda

### 'event' parameter

```json
{
  "resource": "/{proxy+}",
  "path": "/hi",
  "httpMethod": "GET",
  "headers": {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,is;q=0.8,zh-CN;q=0.7,zh;q=0.6",
    "cache-control": "max-age=0",
    "cookie": "pN=15; s_pers=%20s_vnum%3D1544122842493%2526vn%253D3%7C1544122842493%3B%20s_invisit%3Dtrue%7C1543098144265%3B%20s_nr%3D1543096344268-Repeat%7C1550872344268%3B; s_sess=%20s_cc%3Dtrue%3B%20s_sq%3D%3B",
    "Host": "5fsrdz4c2i.execute-api.eu-west-1.amazonaws.com",
    "upgrade-insecure-requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
    "X-Amzn-Trace-Id": "Root=1-5bfbeb90-8aeb6bcee9411996d4d01bb8",
    "X-Forwarded-For": "153.92.155.138",
    "X-Forwarded-Port": "443",
    "X-Forwarded-Proto": "https"
  },
  "multiValueHeaders": {
    "accept": [
      "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    ],
    "accept-encoding": [
      "gzip, deflate, br"
    ],
    "accept-language": [
      "en-US,en;q=0.9,is;q=0.8,zh-CN;q=0.7,zh;q=0.6"
    ],
    "cache-control": [
      "max-age=0"
    ],
    "cookie": [
      "pN=15; s_pers=%20s_vnum%3D1544122842493%2526vn%253D3%7C1544122842493%3B%20s_invisit%3Dtrue%7C1543098144265%3B%20s_nr%3D1543096344268-Repeat%7C1550872344268%3B; s_sess=%20s_cc%3Dtrue%3B%20s_sq%3D%3B"
    ],
    "Host": [
      "5fsrdz4c2i.execute-api.eu-west-1.amazonaws.com"
    ],
    "upgrade-insecure-requests": [
      "1"
    ],
    "User-Agent": [
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36"
    ],
    "X-Amzn-Trace-Id": [
      "Root=1-5bfbeb90-8aeb6bcee9411996d4d01bb8"
    ],
    "X-Forwarded-For": [
      "153.92.155.138"
    ],
    "X-Forwarded-Port": [
      "443"
    ],
    "X-Forwarded-Proto": [
      "https"
    ]
  },
  "queryStringParameters": null,
  "multiValueQueryStringParameters": null,
  "pathParameters": {
    "proxy": "hi"
  },
  "stageVariables": null,
  "requestContext": {
    "resourceId": "6hif7j",
    "resourcePath": "/{proxy+}",
    "httpMethod": "GET",
    "extendedRequestId": "Q-G-hGV6DoEFZKg=",
    "requestTime": "26/Nov/2018:12:48:16 +0000",
    "path": "/dev/hi",
    "accountId": "092475124519",
    "protocol": "HTTP/1.1",
    "stage": "dev",
    "domainPrefix": "5fsrdz4c2i",
    "requestTimeEpoch": 1543236496123,
    "requestId": "8b102d55-f179-11e8-a11e-c5c62484157a",
    "identity": {
      "cognitoIdentityPoolId": null,
      "accountId": null,
      "cognitoIdentityId": null,
      "caller": null,
      "sourceIp": "153.92.155.138",
      "accessKey": null,
      "cognitoAuthenticationType": null,
      "cognitoAuthenticationProvider": null,
      "userArn": null,
      "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
      "user": null
    },
    "domainName": "5fsrdz4c2i.execute-api.eu-west-1.amazonaws.com",
    "apiId": "5fsrdz4c2i"
  },
  "body": null,
  "isBase64Encoded": false
}
```


### 'context' parameter

```json
{
	"aws_request_id": "a6f3a757-f17a-11e8-9181-db24872f67f0",
	"log_group_name": "/aws/lambda/just_a_test",
	"log_stream_name": "2018/11/26/[$LATEST]6ea248e3e6094d7297935a2bb3c71e2d",
	"function_name": "just_a_test",
	"memory_limit_in_mb": "128",
	"function_version": "$LATEST",
	"invoked_function_arn": "arn:aws:lambda:eu-west-1:092475124519:function:just_a_test",
	"client_context": null,
	"identity": "<__main__.CognitoIdentity object at 0x7fec3e09fda0>"
}
```