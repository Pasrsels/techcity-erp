import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICES_FILE = os.path.join(BASE_DIR, 'data', 'services.json')
TYPES_FILE = os.path.join(BASE_DIR, 'data', 'types.json')

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def get_services_with_details():
    services = load_json(SERVICES_FILE)
    types = load_json(TYPES_FILE)
    type_dict = {type_['id']: type_ for type_ in types}

    for service in services:
        type_data = type_dict.get(service['type_id'])
        if type_data:
            service.update(type_data)
    return services

