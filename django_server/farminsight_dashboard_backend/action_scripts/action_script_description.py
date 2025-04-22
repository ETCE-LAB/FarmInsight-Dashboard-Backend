from typing import NamedTuple, List
from enum import Enum


'''
The type of a field needs to be correctly validated the same as any rules applying to the field!  
'''
class FieldType(Enum):
    INTEGER = 'int'
    STRING = 'str'

class FieldDescription(NamedTuple):
    name: str
    type: FieldType
    rules: List[object]

class ValidHttpEndpointRule(NamedTuple):
    pass

class ActionScriptDescription(NamedTuple):
    action_script_class_id:str
    name: str
    '''
    Fields are inputs by the user and are stored as a json dict in the additionalInformation DB column
    '''
    fields: List[FieldDescription]
