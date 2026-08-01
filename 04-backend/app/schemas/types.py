from decimal import Decimal
from typing import Any, Callable, Dict
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler

class StrictDecimalFormat:
    """
    Custom Pydantic type that wraps Decimal,
    enforcing that the input is NOT a float,
    and serializes to a string with a fixed number of decimal places.
    """
    def __init__(self, decimal_places: int):
        self.decimal_places = decimal_places

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            self.validate,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                self.serialize, return_schema=core_schema.str_schema()
            )
        )

    def validate(self, v: Any) -> Decimal:
        if isinstance(v, float):
            raise ValueError("Float input is strictly forbidden. Use Decimal or string.")
        try:
            return Decimal(v)
        except Exception:
            raise ValueError(f"Invalid decimal format: {v}")

    def serialize(self, v: Decimal) -> str:
        # e.g. "0.00" or "0.0000"
        return f"{v:.{self.decimal_places}f}"
        
    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> Dict[str, Any]:
        schema = handler(core_schema)
        schema.update(type="string", format="decimal")
        return schema

from typing import Annotated

# Global type annotations for use in schemas
Money = Annotated[Decimal, StrictDecimalFormat(decimal_places=2)]
Ratio = Annotated[Decimal, StrictDecimalFormat(decimal_places=4)]
Rate = Annotated[Decimal, StrictDecimalFormat(decimal_places=8)]
