#!/usr/bin/env python

import os
import json
import logging
import boto3
from dotenv import load_dotenv, find_dotenv

# environment variables
load_dotenv(find_dotenv())
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
DISPATCHER = os.getenv('dispatcherLambda')

logger = logging.getLogger(__name__)


def get_client(client='s3'):
    return boto3.client(client,
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                        )


def uri_parser(uri):
    """ Split S3 URI into bucket, key, filename """
    if uri[0:5] != 's3://':
        raise Exception('Invalid S3 uri %s' % uri)

    uri_obj = uri.replace('s3://', '').split('/')

    return {
        'bucket': uri_obj[0],
        'key': '/'.join(uri_obj[1:]),
        'filename': uri_obj[-1]
    }


def mkdirp(path):
    """ Recursively make directory """
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def download(uri, path=''):
    """ Download object from S3 """
    s3_uri = uri_parser(uri)
    fout = os.path.join(path, s3_uri['filename'])
    logger.debug("Downloading %s as %s" % (uri, fout))
    mkdirp(path)

    s3 = get_client()

    with open(fout, 'wb') as data:
        s3.download_fileobj(
            Bucket=s3_uri['bucket'],
            Key=s3_uri['key'],
            Fileobj=data
        )
    return fout


def download_json(uri):
    """ Download object from S3 as JSON """
    logger.debug("Downloading %s as JSON" % (uri))
    s3 = get_client()
    s3_uri = uri_parser(uri)
    response = s3.get_object(Bucket=s3_uri['bucket'], Key=s3_uri['key'])
    return json.loads(response['Body'].read())


def upload(filename, uri):
    """ Upload object to S3 uri (bucket + prefix), keeping same base filename """
    logger.debug("Uploading %s to %s" % (filename, uri))
    s3 = get_client()
    s3_uri = uri_parser(uri)
    bname = os.path.basename(filename)
    uri_out = 's3://%s' % os.path.join(s3_uri['bucket'], os.path.join(s3_uri['key'], bname))
    with open(filename, 'rb') as data:
        s3.upload_fileobj(data, s3_uri['bucket'], os.path.join(s3_uri['key'], bname))
    return uri_out


def list(uri):
    """ Get list of objects within bucket and path """
    logger.debug("Listing contents of %s" % uri)
    s3 = get_client()
    s3_uri = uri_parser(uri)
    response = s3.list_objects_v2(Bucket=s3_uri['bucket'], Prefix=s3_uri['key'])

    filenames = []
    if 'Contents' in response.keys():
        for file in response['Contents']:
            filenames.append(os.path.join('s3://%s' % s3_uri['bucket'], file['Key']))
    return filenames


def delete(uri):
    """ Remove an item from S3 """
    logger.debug('Deleting %s' % uri)
    s3 = get_client()
    s3_uri = uri_parser(uri)
    # TODO - parse response and return success/failure
    try:
        res = s3.delete_object(Bucket=s3_uri['bucket'], Key=s3_uri['key'])
        return True
    except Exception as e:
        return False


def exists(uri):
    """ Check if this URI exists on S3 """
    logger.debug('Checking existence of %s' % uri)
    s3 = get_client()
    s3_uri = uri_parser(uri)
    try:
        s3.get_object(Bucket=s3_uri['bucket'], Key=s3_uri['key'])
        return True
    except Exception as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return False
        else:
            raise


def invoke_lambda(payload, lambda_name=DISPATCHER):
    """ Invoke Lambda function with payload """
    client = get_client('lambda')
    logger.debug('Invoking %s with payload: %s' % (lambda_name, json.dumps(payload)))
    result = client.invoke(
        FunctionName=lambda_name,
        InvocationType='Event',
        Payload=json.dumps(payload),
    )
    return result
