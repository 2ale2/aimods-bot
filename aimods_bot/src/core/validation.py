def _get_type_map():
    """
    Returns a mapping of string type names to Python types.

    Returns:
        dict: A dictionary mapping type names to their corresponding Python types.
    """
    return {
        "str": str,
        "int": int,
        "bool": bool,
        "float": float,
        "dict": dict,
        "list": list
    }


def validate_structure(data, raw_template):
    """
    Validates the structure of the provided data against a template.

    Args:
        data: The data to validate.
        raw_template: The template to validate against.

    Returns:
        list: A list of validation error messages.
    """
    type_map = _get_type_map()
    template = _deserialize_template(raw_template, type_map)
    return _check_structure(data, template)


def _deserialize_template(template_json, type_map):
    """
    Converts type strings in the template to actual Python types.

    Args:
        template_json: The template JSON structure.
        type_map: A mapping of type names to Python types.

    Returns:
        The deserialized template with Python types.
    """
    if isinstance(template_json, dict):
        if "type" in template_json:
            t = template_json["type"]
            if isinstance(t, str) and t in type_map:
                template_json["type"] = type_map[t]
        return {k: _deserialize_template(v, type_map) for k, v in template_json.items()}
    return template_json


def _check_structure(data, template, path=""):
    """
    Recursively checks the structure of data against a template.

    Args:
        data: The data to validate.
        template: The template to validate against.
        path: The current path in the data structure for error reporting.

    Returns:
        list: A list of validation error messages.
    """
    errors = []
    for key, rule in template.items():
        full_path = f"{path}{key}"
        if key not in data:
            errors.append(f"Missing key: {full_path}")
            continue

        value = data[key]
        is_field_definition = isinstance(rule, dict) and "type" in rule and set(rule.keys()) <= {"type", "allowed"}

        if isinstance(rule, dict) and not is_field_definition:
            if not isinstance(value, dict):
                errors.append(f"{full_path} should be a dict")
            else:
                errors.extend(_check_structure(value, rule, full_path + "."))
        else:
            expected_type = rule['type']
            allowed_values = rule.get('allowed')

            if expected_type is int:
                if not (isinstance(value, int) and not isinstance(value, bool)):
                    errors.append(f"{full_path} should be a real integer, got {type(value).__name__}")
            elif not isinstance(value, expected_type):
                errors.append(f"{full_path} should be of type {expected_type.__name__}, got {type(value).__name__}")
            elif allowed_values and value not in allowed_values:
                errors.append(f"{full_path} has invalid value '{value}', allowed: {allowed_values}")
    return errors
