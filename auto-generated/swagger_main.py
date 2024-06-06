"""
A module for generating class-based representations of Swagger definitions.

This module utilizes a class-based approach to extract attributes from Swagger definitions
and translate them into specific attributes of Python objects. Its main functionality
involves reading the API definition, extracting relevant information, and transforming it
into a Python module for seamless integration within Lambda functions.

Author: Vishnuhasan Ravi
Version: 1.0
Since: Jan 2024
"""
import json
import os


class Parameter:
    """
    A class representing a parameter with metadata.

    This class is used to define parameters with metadata such as name, value,
    required status, and type. It provides a convenient way to organize and
    manage parameters in various applications.

    Attributes:
        name (str): The name of the parameter.
        _value (Any): The value of the parameter.
        required (bool): A boolean indicating whether the parameter is required.
        type_ (str): The type of the parameter.
        type_map (dict): A dictionary mapping parameter types to corresponding Python types.

    Example:
        >>> param = Parameter(name='param_name', value=10, required=True, type_='integer')
    """

    def __init__(self, name, value, required, type_):
        self.name = name
        self._value = value
        self.required = required
        self.type_ = type_
        self.type_map = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': bool,
            'array': list,
            'object': dict
        }

    def __repr__(self):
        if str(self).startswith('_'):
            return self.name
        else:
            return self.value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self.validate_type(new_value)
        self._value = new_value

    def validate_type(self, value):
        """
            Method to validate the type of the value that is
        being set to the python objects.

        Raise:
           - TypeError: Invalid type error, when specific type does not match.
        """
        if not isinstance(value, self.type_map[self.type_]):
            raise TypeError(
                f"Invalid type '{type(value).__name__}' for '{self.name}', "
                f"Expected '{self.type_map[self.type_].__name__}'.")

    def set_value(self, value):
        self.validate_type(value)
        self.value = value


def generate_parameter(param_name: str, param_schema: dict) -> tuple:
    """
        Generate class code attributes for parameter swagger definition.

    Args:
        param_name (str): The name of the parameter.
        param_schema (dict): The schema of the parameter.

    Returns:
        :return : A tuple containing the parameter code and metadata code.

    """
    param_required = param_name in param_schema.get("required", [])
    param_type = param_schema.get('type', '')
    param_description = param_schema.get('description', '')
    param_value = None
    if param_description:
        param_description = f"""{param_description}"""
        return (f'data.get(\'{param_name}\')',
                f'Parameter(name="{param_name}", value=None, required={param_required}, type_="{param_type}")')
    else:
        return (f'data.get(\'{param_name}\')',
                f'Parameter(name="{param_name}", value=None, required={param_required}, type_="{param_type}")')

def generate_response_class_code(nested_class_response_text: str, response_attributes_text: str, ms_suffix: str):
    class_template = ''
    if nested_class_response_text.strip():
        class_template += f'''
class ResponseNestedAttributes:
    {nested_class_response_text}
'''
    
    class_template += f'''
class ResponseObject_{ms_suffix}:

    def __init__(self, data: Union[dict, list]):
        """Response object attributes"""
        if isinstance(data, dict):
            self._set_value(data)
        elif isinstance(data, list):
            self._handle_list_response(data)
    
    def _set_value(self, data: dict):
        """set values for attributes from a dictionary"""
        {response_attributes_text}
    def _handle_list_response(self, data_list: dict):
        self.instances = [ResponseObject_{ms_suffix}(item) for item in data_list]
    '''
    return class_template

def  generate_class_code(
        file_name: str, attributes_text: str, nested_classes_text: str,
        end_point: str, nested_class_param_text='', parameter_text='',
        ms_suffix="MS") -> str:
    """
    Generate a class code from the given text for creating it as a new Python module.

    Args:
        class_name (str): The name of the class.
        file_name (str): The name of the file.
        attributes_text (str): Text containing class attributes.
        nested_classes_text (str): Text containing nested class definitions.
        end_point (str): The endpoint of the class.
        parameter_text (str, optional): Text containing parameter definitions. Defaults to ''.
        response_template (dict, optional): Template for the response. Defaults to {}.

    Returns:
        :return: class_template: The generated class template.

    """
    if not parameter_text:
        parameter_text = 'pass'
    if not attributes_text:
        attributes_text = 'pass'
    class_template = ''
    class_template += f'''"""An auto-generated module for {end_point} endpoint,which helps us to get its parameters and 
request body attributes as python objects.
"""
from typing import Union
'''

    if nested_classes_text.strip():
        class_template += f'''
class RequestNestedAttributes:
    {nested_classes_text}
'''

    class_template += f'''
class RequestBody:
    def __init__(self, data: dict):
        """Request body object attributes."""
        """Note: Meta attribute variables are prepended with _."""
        {attributes_text}
    {nested_class_param_text}
class ParameterObject:
    def __init__(self, data: dict):
        """Parameter object attributes."""
        """Note: Meta attribute variables are prepended with _."""
        {parameter_text}
        
class RequestObject_{ms_suffix}:
    def __init__(self, data: dict):
        """Request object attributes"""
        self.body = data.get('body')
        self.params = data.get('params')

    def get_{file_name}_request_body(self):
        return RequestBody(self.body)

    def get_{file_name}_parameter(self):
        return ParameterObject(self.params)
'''
    return class_template


class DynamicClassGenerator:
    """
        Class which helps us to generate python class level attributes from the
    given json data for dot notation level object reference.
      In addition to that, it also prepares a response structure,
    which is being used for validating the response data from lambda handler.
    """

    def __init__(self, json_data: dict):
        self.json_data = json_data
        self.package_path = f"{os.path.dirname(__file__)}"
        self.response_template = {}

    def get_parameter_module(self, attributes: list, classes_list: list, parameters: list):
        """
            Method to get parameter module with using parameter class
        """
        for attr_name in classes_list:
            attributes.append(f'self.{attr_name} = {attr_name}(data.get(\'{attr_name}\'))')
            for param in parameters:
                if param['in'] == 'query':
                    attributes.append(f'self.{param["name"]} = data.get(\'{param["name"]}\')')

    def parse_parameters(self, parameters: dict, attributes: list):
        """
        Method to parse parameters for parameter objects.
    """
        for param in parameters:
            name_str = param['name']
            name = param["name"].replace('-', '_')
            required = param.get("required", False)
            param_type = param["schema"]["type"]
            value = None
            attributes.append(f'self.{name} = data.get(\'{name_str}\')')

    def generate_parameter_module(self, nested_class_param_text: str, attributes_param_text: str, file_name: str,
                                  class_name: str, end_point: str, response: dict, ms_suffix='MS'): 
        if not attributes_param_text:
            attributes_param_text = 'pass'
        class_template = f'''"""An automated module for {end_point} endpoint,\nwhich helps us to get its parameters as \npython objects.\n"""
from typing import Union

{nested_class_param_text}
class ParameterObject:

    def __init__(self, data: dict):
        """Parameter object attributes.
        Note: Meta attribute variables are prepended with _."""
        {attributes_param_text}

    def __repr__(self):
        return "\\n".join([str(attr) for attr in self.__dict__.values()])


class RequestObject_{ms_suffix}:
    def __init__(self, data: dict):
        """Request object attributes"""
        self.body = data.get('body')
        self.params = data.get('params')

    def get_{file_name}_parameter(self):
        return ParameterObject(self.params)
{self.generate_response_class_code(class_name, response)}
'''

        package_path = f"{os.path.dirname(__file__)}"
        with open(os.path.join(package_path, f"{file_name}.py"), "w") as f:
            f.write(class_template)

    def simplify_swagger_definition(self, schema: dict) -> dict:
        """
        Method to simplify the swagger definition's response template for
    dynamic process of out-response.

    Args:
        schema: dict level schema definition.

    Returns:
        :return: Response out-payload dict.
    """
        result = {}
        if 'properties' in schema:
            for prop_name, prop_schema in schema['properties'].items():
                if "$ref" in prop_schema:
                    ref = prop_schema["$ref"]
                    resolver_dict = self.resolve_reference(ref)
                    if 'properties' in prop_schema:
                        resolver_dict['properties'].update(prop_schema.get('properties', {}))
                    result[prop_name] = self.simplify_swagger_definition(resolver_dict)
                elif prop_schema.get('type', '') == 'object':
                    result[prop_name] = self.simplify_swagger_definition(prop_schema)
                elif prop_schema.get('type', '') == 'array' and 'items' in prop_schema:
                    items_schema = prop_schema['items']
                    if "$ref" in items_schema:
                        ref = items_schema["$ref"]
                        result[prop_name] = [self.simplify_swagger_definition(self.resolve_reference(ref))]
                    else:
                        result[prop_name] = [self.simplify_swagger_definition(items_schema)]
                else:
                    result[prop_name] = prop_schema.get('type', '')
        elif 'items' in schema and schema.get('type', '') == 'array':
            result = []
            items_schema = schema['items']
            if "$ref" in items_schema:
                ref = items_schema["$ref"]
                result.append(self.simplify_swagger_definition(self.resolve_reference(ref)))
            else:
                result.append(self.simplify_swagger_definition(items_schema))
        return result

    def generate_classes(self):
        """
        Method to generate python objects for request, response and parameter
    attributes from the swagger definition.
    """
        for path, methods in self.json_data.get('paths', {}).items():
            for method, details in methods.items():
                file_name = '_'.join(
                    val.replace('{', '').replace('}', '').replace('-', '_') for val in path[1:].split('/'))
                if len(methods.keys()) > 1:
                    file_name = f'{file_name}_{method}'
                file_name = file_name.lower()
                class_name = self.generate_class_name(file_name)
                attributes_param_text = nested_class_param_text = parameter_text = ''
                if 'responses' in details:
                    response_content = details['responses']['200']['content']['application/json']
                    schema = {}
                    if 'schema' in response_content and '$ref' not in response_content['schema']:
                        schema = response_content['schema']
                    else:
                        response_schema = response_content['schema']['$ref']
                        schema = self.resolve_reference(response_schema)
                    response_template = self.simplify_swagger_definition(schema)
                    response_template = json.dumps(response_template, indent=2)
                if 'parameters' in details:
                    attributes = []
                    classes_list = []
                    nested_class_param_text = self.get_nested_param_class_code(details['parameters'], classes_list)
                    self.get_parameter_module(attributes, classes_list, details['parameters'])
                    parameter_text = '\n        '.join(attributes)
                if 'requestBody' in details and 'responses' in details:
                    request_body = details['requestBody']['content']['application/json']['schema']
                    self.end_point = path
                    class_code = self.generate_class_code(
                        class_name, file_name, request_body, nested_class_param_text, parameter_text)
                    schema = details['responses']['200']['content']['application/json']['schema']
                    class_response_code = self.generate_response_class_code(class_name, schema)
                    class_code += class_response_code
                    file_path = f'{os.path.dirname(__file__)}/{file_name}.py'
                    with open(file_path, 'w') as module_file:
                        module_file.write(class_code)
                else:
                    if 'requestBody' in details:
                        request_body = details['requestBody']['content']['application/json']['schema']
                        self.end_point = path
                        class_code = self.generate_class_code(
                            class_name, file_name, request_body, nested_class_param_text, parameter_text)
                        file_path = f'{os.path.dirname(__file__)}/{file_name}.py'
                        with open(file_path, 'w') as module_file:
                            module_file.write(class_code)
                    if method == 'get' and 'requestBody' not in details:
                        ms_suffix = self.json_data.get('info', {}).get('suffix', 'MS')
                        if 'responses' in details:
                            response = details['responses']['200']['content']['application/json']['schema']
                        self.generate_parameter_module(
                            nested_class_param_text, parameter_text, file_name, class_name, path, response, ms_suffix)

    def generate_class_name(self, file_name: str) -> str:
        """
        Method to generate class from the path-converted filename.

    Args:
        file_name: string represented filename.
    """
        return ''.join(part.capitalize() for part in file_name.split('_'))

    def resolve_reference(self, reference: str) -> str:
        """
        Method to get the nested data schema object from the schema object name.

    Args:
        reference: string represented schema name.

    Example:
        >> "$ref": "#/components/schemas/scheme-object"
    """
        ref_name = reference.split("/")[-1]

        return self.json_data['components']['schemas'][ref_name]
    
    def itr_properties(self, class_name: str, schema: dict, class_attributes: dict, nested_classes: dict, prefix_var: str) -> None: 
        if 'properties' in schema:
            for _, child_schema in schema['properties'].items():
                if '$ref' in child_schema:
                    properties = self.resolve_reference(child_schema['$ref'])['properties']
                    self.parse_properties(properties, class_attributes, nested_classes, class_name, prefix_var=prefix_var)
                elif 'properties' in child_schema:
                    self.parse_properties(
                        child_schema["properties"], class_attributes,
                        nested_classes, class_name, prefix_var=prefix_var)
            items_schema = schema['items']
            schema = self.resolve_reference(items_schema['$ref'])
            self.parse_properties(schema['properties'], class_attributes, nested_classes, class_name, prefix_var=prefix_var)
        
        else:
            nested_class_name = schema['$ref'].split("/")[-1]
            nested_class_name = nested_class_name.replace('-', '_')
            iter_val = f'{nested_class_name}_'
            schema = self.resolve_reference(schema['$ref'])
            if schema['type'] == "array" and 'items' in schema:
                if '$ref' in schema['items']:
                    items_schema = schema['items']
                    schema = self.resolve_reference(items_schema['$ref'])
                else:
                    schema = schema['items']
                    self.parse_properties(schema["properties"], class_attributes, nested_classes, class_name, prefix_var=prefix_var)
                # self.parse_properties(schema["properties"], class_attributes, nested_classes, class_name)
            self.parse_properties(schema["properties"], class_attributes, nested_classes, class_name, prefix_var=prefix_var)
    
    def generate_class_code(
            self, class_name: str, file_name: str, schema: dict, nested_class_param_text: str,
            parameter_str: str = '') -> str:
        """
        Method to generate class code based on the objects retrieval from the swagger definition.
    """
        class_attributes = {}
        nested_classes = {}
        var = "RequestNestedAttributes"
        self.itr_properties(class_name, schema, class_attributes, nested_classes, var)
        attributes_text = ""
        for attr_name, attr_value in class_attributes.items():
            attributes_text += f'self.{attr_name} = {attr_value}\n        '

        nested_classes_text = ""
        for nested_class_name, nested_class_code in nested_classes.items():
            nested_classes_text += f'\n{nested_class_code}'

        ms_suffix = self.json_data.get('info', {}).get('suffix', 'MS')  # Microservice Prefix Code
        class_template = generate_class_code(
            file_name, attributes_text, nested_classes_text,
            self.end_point, parameter_text=parameter_str, nested_class_param_text=nested_class_param_text,
            ms_suffix=ms_suffix)
        return class_template
            
    def generate_response_class_code(self, class_name: str, schema: dict) -> str:
        class_attributes = {}
        nested_classes = {}
        var = "ResponseNestedAttributes"
        self.itr_properties(class_name, schema, class_attributes, nested_classes, var)
        
        response_attributes_text = ""
        for attr_name, attr_value in class_attributes.items():
            response_attributes_text += f'self.{attr_name} = {attr_value}\n        '

        nested_class_response_text = ""
        for nested_class_name, nested_class_code in nested_classes.items():
            nested_class_response_text += f'\n{nested_class_code}'
        ms_suffix = self.json_data.get('info', {}).get('suffix', 'MS')  # Microservice Prefix Code
        class_template = generate_response_class_code(nested_class_response_text, response_attributes_text, ms_suffix=ms_suffix)
        return class_template

    def nested_param_class_list(self, parameters: dict, classes_list: list) -> None:
        """
        Get the class list from parameter based on the key 'in'

    Args:
        parameters (dict)
        classes_list (list)

    Returns:
        _type_: None
    """
        for attribute in parameters:
            if attribute['in'] not in classes_list and attribute['in'] != 'query':
                classes_list.append(attribute['in'])
        return None

    def generate_nested_init(self, attributes_dict: dict) -> str:
        """
        Generate child level class code attributes.

    Args:
        attributes_dict (dict): Dictionary containing attributes.

    Returns:
        str: The generated initialization template.

    """
        init_template = ''
        for key, value in attributes_dict.items():
            if isinstance(value, str):
                init_template += f'self.{key} = {value}\n            '
            else:
                init_template += f'self.{key} = data.get(\'{attributes_dict[key].name}\')        '

        return init_template

    def get_nested_param_class_code(self, parameters, classes_list: list) -> str:
        """
        Get the nested class code string.

    Args:
        nested_class_name (str): The name of the nested class.
        nested_class_code (str): The code of the nested class.

    Returns:
        str: The nested class code.

    """
        self.nested_param_class_list(parameters, classes_list)
        nested_param_classes_text = ""
        for class_name in classes_list:
            parameters_list = []
            for param in parameters:
                nested_class_name = class_name
                if class_name in param['in']:
                    parameters_list.append(param)
            attributes = []
            self.parse_parameters(parameters_list, attributes)
            attributes_text = '\n        '.join(attributes)
            classes_text = f'''
class {nested_class_name}:

    def __init__(self, data: dict):
        """Note: Meta attribute variables are prepended with _."""\n
        {attributes_text}

    def __repr__(self):
        return self.__class__.__name__
'''
            nested_param_classes_text += classes_text + '\n'
        return nested_param_classes_text

    def get_nested_class_code(self, nested_class_name: str, nested_class_code: str) -> str:
        """
        Get the nested class code string.

    Args:
        nested_class_name (str): The name of the nested class.
        nested_class_code (str): The code of the nested class.

    Returns:
        str: The nested class code.

    """
        return f'''
    class {nested_class_name}:

        def __init__(self, data: dict):
            """Note: Meta attribute variables are prepended with _."""\n
            data = data if data else {{}}
            {nested_class_code}
        def __repr__(self):
            return self.__class__.__name__

        def __iter__(self):
            # This method returns an iterator object
            # In this case, we'll return an iterator over a tuple of attributes
            for key, value in vars(self).items():
                yield key, value 
'''

    def parse_properties(
            self, properties: dict, class_attributes: dict,
            nested_classes: dict, class_name: str,suffix: str="", prefix_var: str="") -> None:
        """
        Iterate over the direct/indirect nested Swagger definitions for generating
        Python class attributes for its dot notation object reference from the lambdas.

    Args:
        properties (dict): Dictionary of properties.
        class_attributes (dict): Dictionary to store class attributes.
        nested_classes (dict): Dictionary to store nested classes.
        class_name (str): The name of the class.
        suffix (str): suffix for class names. Defaults to "".
    """ 
        for prop_name, prop_schema in properties.items():
            if '$ref' in prop_schema:
                nested_class_name = prop_name
                nested_attributes = {}
                iter_val = prop_name[:-1]
                properties = self.resolve_reference(prop_schema['$ref'])['properties']
                self.parse_properties(properties, nested_attributes, nested_classes,
                                  class_name, nested_class_name, prefix_var)
                nested_class_code = self.generate_nested_init(nested_attributes)
                nested_classes[nested_class_name] = self.get_nested_class_code(
                    nested_class_name, nested_class_code)
                class_attributes[prop_name] = f'{nested_class_name}()'
            if prop_schema.get('type', '') == "object" and 'properties' in prop_schema:
                nested_class_name = prop_name
                nested_attributes = {}
                iter_val = f"{prop_name}_"
                self.parse_properties(prop_schema["properties"], nested_attributes, nested_classes, class_name,
                                      nested_class_name, prefix_var)
                nested_class_code = self.generate_nested_init(nested_attributes)
                nested_classes[nested_class_name] = self.get_nested_class_code(
                    nested_class_name, nested_class_code)
                class_attributes[
                    prop_name] = f'[{prefix_var}.{nested_class_name}({iter_val}) for {iter_val} in data.get(\'{prop_name}\')] if isinstance(data.get(\'{prop_name}\'), list) else []'
                class_attributes[f'{prop_name}_data'] = f"data.get('{prop_name}')"

            elif prop_schema.get('type', '') == "array" and "items" in prop_schema:
                items_schema = prop_schema["items"]
                if not items_schema:
                    class_attributes[prop_name] = f"data.get('{prop_name}')"
                elif '$ref' in items_schema:
                    nested_class_name = prop_name
                    nested_attributes = {}
                    iter_val = f"{prop_name}_"
                    properties = self.resolve_reference(items_schema['$ref'])['properties']
                    self.parse_properties(properties, nested_attributes, nested_classes, class_name,
                                          nested_class_name, prefix_var)
                    nested_class_code = self.generate_nested_init(nested_attributes)
                    nested_classes[nested_class_name] = self.get_nested_class_code(
                        nested_class_name, nested_class_code)
                    class_attributes[
                        prop_name] = f'[{prefix_var}.{nested_class_name}({iter_val}) for {iter_val} in data.get(\'{prop_name}\')] if isinstance(data.get(\'{prop_name}\'), list) else []'
                    class_attributes[f'{prop_name}_data'] = f"data.get('{prop_name}')"
                    
                elif items_schema["type"] == "object":
                    nested_class_name = prop_name
                    nested_attributes = {}
                    self.parse_properties(items_schema["properties"], nested_attributes, nested_classes, class_name,
                                          nested_class_name, prefix_var)
                    nested_class_code = self.generate_nested_init(nested_attributes)
                    iter_val = f"{prop_name}_"
                    nested_classes[nested_class_name] = self.get_nested_class_code(
                        nested_class_name, nested_class_code)
                    class_attributes[
                        prop_name] = f'[{prefix_var}.{nested_class_name}({iter_val}) for {iter_val} in data.get(\'{prop_name}\')] if isinstance(data.get(\'{prop_name}\'), list) else []'
                    class_attributes[f'{prop_name}_data'] = f"data.get('{prop_name}')"
                else:
                    param_code, param_meta_code = generate_parameter(prop_name, items_schema)
                    class_attributes[prop_name] = param_code

            else:
                param_code, param_meta_code = generate_parameter(prop_name, prop_schema)
                if class_attributes.get(prop_name, '').endswith('()'):
                    class_attributes[prop_name] = f"{prefix_var}.{prop_name}(data.get('{prop_name}'))"
                else:
                    class_attributes[prop_name] = param_code

        nested_classes_text = ""
        for nested_class_name, nested_class_code in nested_classes.items():
            nested_classes_text += f'\n{nested_class_code}'


def get_api_definition() -> dict:
    """
    Method to get the json data from the given swagger definition.

    Returns:
        dict: Extracted json data from swagger definition.
    """
    file_path = f'{os.path.dirname(__file__)}/swagger_definition.json'
    with open(file_path, 'r') as file:
        data = json.load(file)

    return data


if __name__ == '__main__':
    json_data_collection = get_api_definition()
    generator = DynamicClassGenerator(json_data_collection)
    generator.generate_classes()

    print("Successfully created modules for provided swagger definition.")