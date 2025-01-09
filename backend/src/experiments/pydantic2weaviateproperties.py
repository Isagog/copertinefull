from datetime import date
import importlib.util
import inspect
import logging
import sys
from typing import Any, Dict, List, Type

from pydantic import BaseModel
from weaviate.classes.config import DataType, Tokenization

# Configure logging
logger = logging.getLogger(__name__)

# Constants
EXPECTED_ARGS = 2
USAGE_MSG = "Usage: python script.py <path_to_pydantic_models_file>"

def load_pydantic_models(file_path: str) -> List[Type[BaseModel]]:
    """Load Pydantic model classes from a Python file."""
    spec = importlib.util.spec_from_file_location("dynamic_module", file_path)
    if not spec or not spec.loader:
        error_msg = "Could not load module from {}"
        raise ImportError(error_msg.format(file_path))

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    models = []
    for _name, obj in inspect.getmembers(module):
        if (inspect.isclass(obj) and
            issubclass(obj, BaseModel) and
            obj != BaseModel):
            models.append(obj)

    return models

def get_field_extra(field) -> Dict[str, Any]:
    """Extract field extra attributes safely handling Pydantic v2 deprecation."""
    extra = {}
    if hasattr(field, "json_schema_extra") and field.json_schema_extra:
        extra = field.json_schema_extra
    elif hasattr(field, "field_info") and hasattr(field.field_info, "extra"):
        extra = field.field_info.extra
    return extra

def get_weaviate_data_type(python_type) -> DataType:
    """Map Python/Pydantic types to Weaviate DataType."""
    type_mapping = {
        str: DataType.TEXT,
        int: DataType.INT,
        float: DataType.NUMBER,
        bool: DataType.BOOL,
        date: DataType.DATE,
    }
    return type_mapping.get(python_type, DataType.TEXT)

def convert_model_to_properties(model: Type[BaseModel]) -> List[Dict[str, Any]]:
    """Convert a Pydantic model to a list of Weaviate property configurations."""
    properties = []

    for field_name, field in model.model_fields.items():
        prop_config = {
            "name": field_name,
            "description": field.description or "",
            "dataType": [get_weaviate_data_type(field.annotation).value],
        }

        extra = get_field_extra(field)

        if extra.get("we_tok") == "FIELD":
            prop_config["tokenization"] = Tokenization.FIELD.value

        if "we_search" in extra:
            prop_config["indexSearchable"] = extra["we_search"]

        if "we_filter" in extra:
            prop_config["indexFilterable"] = extra["we_filter"]

        properties.append(prop_config)

    return properties

def format_property_str(prop: Dict[str, Any]) -> str:
    """Format a single property as a string."""
    lines = []
    lines.append("    Property(")
    lines.append(f'        name="{prop["name"]}",')
    lines.append(f'        description="{prop["description"]}",')
    lines.append(f"        data_type=DataType.{DataType(prop['dataType'][0]).name},")

    if "tokenization" in prop:
        lines.append(f"        tokenization=Tokenization.{Tokenization(prop['tokenization']).name},")

    if "indexSearchable" in prop:
        lines.append(f"        index_searchable={prop['indexSearchable']},")

    if "indexFilterable" in prop:
        lines.append(f"        index_filterable={prop['indexFilterable']},")

    lines.append("    ),")
    return "\n".join(lines)

def main(file_path: str):
    """Main function to process the file and output Weaviate properties."""
    try:
        models = load_pydantic_models(file_path)

        if not models:
            logger.warning("No Pydantic models found in the file.")
            return

        for model in models:
            logger.info("Properties for model %s:", model.__name__)
            properties = convert_model_to_properties(model)

            properties_str = ['"properties": [']
            for prop in properties:
                properties_str.append(format_property_str(prop))
            properties_str.append("]")

            logger.info("\n".join(properties_str))

    except Exception:
        logger.exception("Error processing file")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    if len(sys.argv) != EXPECTED_ARGS:
        logger.error(USAGE_MSG)
        sys.exit(1)

    main(sys.argv[1])
