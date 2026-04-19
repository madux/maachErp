import requests

def get_key_schema(schema_registry_url, schema_registry_api_key, schema_registry_api_secret, topic):
    url = '%s/subjects/%s-key/versions/latest' % (
        schema_registry_url, topic)
    res = requests.get(url, auth=(
        schema_registry_api_key, schema_registry_api_secret))
    schema = res.json().get("schema")
    return schema

def get_value_schema(schema_registry_url, schema_registry_api_key, schema_registry_api_secret, topic):
    url = '%s/subjects/%s-value/versions/latest' % (
        schema_registry_url, topic)
    res = requests.get(url, auth=(
        schema_registry_api_key, schema_registry_api_secret))
    schema = res.json().get("schema")
    return schema