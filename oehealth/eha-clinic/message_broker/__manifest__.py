# -*- coding: utf-8 -*-
{
    'name': "Message Broker",

    'summary': """
        Message Broker for Microservice implmentation""",

    'description': """
        Message Broker for Microservice implmentation. This will ensure that CRUD operations are managed succesfully and communicated to
        a message broker. Brokers supported are Apache Kafka, Rabbit MQ, Redis etc.
    """,

    'author': "EHA Clinics Ltd.",
    'website': "http://www.eha.ng",

    'category': 'Micro Service',
    'version': '0.1',
    'application': True,
    'external_dependencies': {
        'python': [
            'avro',
            'confluent-kafka',
            'sentry-sdk',
        ]
    },
    'depends': [
        'base',
        'mail',
        'eha_multi_branch',
        'slack_service',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/broker_views.xml',
        'views/rule_views.xml',
    ],
}
