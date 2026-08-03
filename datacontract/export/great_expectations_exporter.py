"""
This module provides functionalities to export data contracts to Great Expectations suites.
It includes definitions for exporting different types of data (pandas, Spark, SQL) into
Great Expectations expectations format.
"""

import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, SchemaProperty

from datacontract.export.exporter import (
    Exporter,
    _check_schema_name_for_export,
)

logger = logging.getLogger(__name__)

#: Regular expressions used to translate ODCS ``logicalTypeOptions.format`` values
#: of string properties into ``expect_column_values_to_match_regex`` expectations.
_STRING_FORMAT_REGEX: Dict[str, str] = {
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    "uri": r"^[a-zA-Z][a-zA-Z0-9+.-]*:\S*$",
    "hostname": r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$",
    "ipv4": r"^((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])$",
    "ipv6": r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$",
}

#: Mapping of JDK ``DateTimeFormatter`` letter runs to their strftime equivalent.
_JDK_TO_STRFTIME: Dict[str, str] = {
    "yyyy": "%Y",
    "uuuu": "%Y",
    "yy": "%y",
    "MMMM": "%B",
    "MMM": "%b",
    "MM": "%m",
    "dd": "%d",
    "DDD": "%j",
    "EEEE": "%A",
    "EEE": "%a",
    "HH": "%H",
    "hh": "%I",
    "mm": "%M",
    "ss": "%S",
    "SSSSSS": "%f",
    "SSS": "%f",
    "a": "%p",
    "Z": "%z",
    "ZZ": "%z",
    "ZZZ": "%z",
    "X": "%z",
    "XX": "%z",
    "XXX": "%z",
    "zzz": "%Z",
    "z": "%Z",
}

#: ODCS logical types whose ``format`` option describes a date/time pattern.
_TEMPORAL_LOGICAL_TYPES = ("date", "timestamp", "time")

#: ``logicalTypeOptions`` keys that have no Great Expectations core equivalent.
_UNSUPPORTED_LOGICAL_TYPE_OPTIONS = (
    "multipleOf",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "required",
    "timezone",
    "defaultTimezone",
)


class GreatExpectationsEngine(str, Enum):
    """Enum to represent the type of data engine for expectations.

    Attributes:
        pandas (str): Represents the Pandas engine type.
        spark (str): Represents the Spark engine type.
        sql (str): Represents the SQL engine type.
    """

    pandas = "pandas"
    spark = "spark"
    sql = "sql"


class GreatExpectationsExporter(Exporter):
    """Exporter class to convert data contracts to Great Expectations suites.

    Methods:
        export: Converts a data contract model to a Great Expectations suite.

    """

    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        """Exports a data contract model to a Great Expectations suite.

        Args:
            data_contract (OpenDataContractStandard): The data contract specification.
            model (str): The model name to export.
            server (str): The server information.
            sql_server_type (str): Type of SQL server (e.g., "snowflake").
            export_args (dict): Additional arguments for export, such as "suite_name" and "engine".

        Returns:
            str: JSON string of the Great Expectations suite.
        """
        expectation_suite_name = export_args.get("suite_name")
        engine = export_args.get("engine")
        schema_name, _ = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        sql_server_type = "snowflake" if sql_server_type == "auto" else sql_server_type
        return to_great_expectations(data_contract, schema_name, expectation_suite_name, engine, sql_server_type)


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _jdk_format_to_strftime(jdk_format: str) -> Optional[str]:
    """Converts a JDK ``DateTimeFormatter`` pattern to a strftime format.

    Args:
        jdk_format (str): The JDK pattern, e.g. ``yyyy-MM-dd``.

    Returns:
        Optional[str]: The strftime format, or None if a pattern letter is not supported.
    """
    result = []
    index = 0
    while index < len(jdk_format):
        char = jdk_format[index]
        if char == "'":
            end = jdk_format.find("'", index + 1)
            if end == -1:
                return None
            literal = jdk_format[index + 1 : end]
            result.append(literal if literal else "'")
            index = end + 1
        elif char.isalpha():
            end = index
            while end < len(jdk_format) and jdk_format[end] == char:
                end += 1
            run = jdk_format[index:end]
            strftime_token = _JDK_TO_STRFTIME.get(run)
            if strftime_token is None:
                return None
            result.append(strftime_token)
            index = end
        else:
            result.append("%%" if char == "%" else char)
            index += 1
    return "".join(result)


def _warn_unsupported_logical_type_options(field_name: str, prop: SchemaProperty) -> None:
    """Logs a warning for each logical type option without a Great Expectations equivalent.

    Args:
        field_name (str): The name of the field.
        prop (SchemaProperty): The property object.
    """
    for option in _UNSUPPORTED_LOGICAL_TYPE_OPTIONS:
        if _get_logical_type_option(prop, option) is not None:
            logger.warning(
                "Great Expectations export: logicalTypeOptions.%s of column '%s' has no "
                "Great Expectations equivalent and is skipped.",
                option,
                field_name,
            )


def _get_enum_from_custom_properties(prop: SchemaProperty) -> Optional[List[str]]:
    """Get enum values from customProperties (used when importing from DCS)."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == "enum" and cp.value:
            if isinstance(cp.value, list):
                return cp.value
            return json.loads(cp.value)
    return None


def to_great_expectations(
    odcs: OpenDataContractStandard,
    schema_name: str,
    expectation_suite_name: str | None = None,
    engine: str | None = None,
    sql_server_type: str = "snowflake",
) -> str:
    """Converts a data contract model to a Great Expectations suite.

    Args:
        odcs (OpenDataContractStandard): The data contract.
        schema_name (str): The schema/model name to export.
        expectation_suite_name (str | None): Optional suite name for the expectations.
        engine (str | None): Optional engine type (e.g., "pandas", "spark").
        sql_server_type (str): The type of SQL server (default is "snowflake").

    Returns:
        str: JSON string of the Great Expectations suite.
    """
    # Find the schema by name
    schema = next((s for s in odcs.schema_ if s.name == schema_name), None)
    if schema is None:
        raise RuntimeError(f"Schema '{schema_name}' not found in data contract.")

    expectations = []
    if not expectation_suite_name:
        expectation_suite_name = "{schema_name}.{contract_version}".format(
            schema_name=schema_name, contract_version=odcs.version
        )

    # Get quality checks from schema-level quality
    if schema.quality:
        expectations.extend(get_quality_checks(schema.quality))

    # Get expectations from model fields
    expectations.extend(model_to_expectations(schema.properties or [], engine, sql_server_type))

    model_expectation_suite = to_suite(expectations, expectation_suite_name)

    return model_expectation_suite


def to_suite(expectations: List[Dict[str, Any]], expectation_suite_name: str) -> str:
    """Converts a list of expectations to a JSON-formatted suite.

    Args:
        expectations (List[Dict[str, Any]]): List of expectations.
        expectation_suite_name (str): Name of the expectation suite.

    Returns:
        str: JSON string of the expectation suite.
    """
    return json.dumps(
        {
            "name": expectation_suite_name,
            "expectations": expectations,
            "meta": {},
        },
        indent=2,
    )


def model_to_expectations(
    properties: List[SchemaProperty], engine: str | None, sql_server_type: str
) -> List[Dict[str, Any]]:
    """Converts model properties to a list of expectations.

    Args:
        properties (List[SchemaProperty]): List of model properties.
        engine (str | None): Engine type (e.g., "pandas", "spark").
        sql_server_type (str): SQL server type.

    Returns:
        List[Dict[str, Any]]: List of expectations.
    """
    expectations = []
    add_column_order_exp(properties, expectations)
    for prop in properties:
        add_field_expectations(prop.name, prop, expectations, engine, sql_server_type)
        if prop.quality:
            expectations.extend(get_quality_checks(prop.quality, prop.name))
    return expectations


def add_field_expectations(
    field_name: str,
    prop: SchemaProperty,
    expectations: List[Dict[str, Any]],
    engine: str | None,
    sql_server_type: str,
) -> List[Dict[str, Any]]:
    """Adds expectations for a specific field based on its properties.

    Args:
        field_name (str): The name of the field.
        prop (SchemaProperty): The property object.
        expectations (List[Dict[str, Any]]): The expectations list to update.
        engine (str | None): Engine type (e.g., "pandas", "spark").
        sql_server_type (str): SQL server type.

    Returns:
        List[Dict[str, Any]]: Updated list of expectations.
    """
    prop_type = _get_type(prop)
    if prop_type is not None:
        if engine == GreatExpectationsEngine.spark.value:
            from datacontract.export.spark_exporter import to_spark_data_type

            field_type = to_spark_data_type(prop).__class__.__name__
        elif engine == GreatExpectationsEngine.pandas.value:
            from datacontract.export.pandas_type_converter import convert_to_pandas_type

            field_type = convert_to_pandas_type(prop)
        elif engine == GreatExpectationsEngine.sql.value:
            from datacontract.export.sql_type_converter import convert_to_sql_type

            field_type = convert_to_sql_type(prop, sql_server_type)
        else:
            field_type = prop_type
        expectations.append(to_column_types_exp(field_name, field_type))

    # A primary key implies both non-null and unique values, so `required` and `unique`
    # do not need to be considered separately.
    # Library qualities override schema attributes; skip strict rule if covered by Library.
    if prop.primaryKey:
        if not _has_library_quality_for_metric(prop, "nullValues"):
            expectations.append(to_column_not_null_exp(field_name, mostly=1.0))
        if not _has_library_quality_for_metric(prop, "duplicateValues"):
            expectations.append(to_column_unique_exp(field_name, mostly=1.0))
    else:
        if prop.required and not _has_library_quality_for_metric(prop, "nullValues"):
            expectations.append(to_column_not_null_exp(field_name, mostly=1.0))
        if prop.unique and not _has_library_quality_for_metric(prop, "duplicateValues"):
            expectations.append(to_column_unique_exp(field_name, mostly=1.0))

    min_length = _get_logical_type_option(prop, "minLength")
    max_length = _get_logical_type_option(prop, "maxLength")
    if min_length is not None or max_length is not None:
        expectations.append(to_column_length_exp(field_name, min_length, max_length))

    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")
    exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
    exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")
    if exclusive_minimum is not None:
        minimum = exclusive_minimum
    if exclusive_maximum is not None:
        maximum = exclusive_maximum
    if minimum is not None or maximum is not None:
        expectations.append(
            to_column_min_max_exp(
                field_name,
                minimum,
                maximum,
                strict_min=exclusive_minimum is not None,
                strict_max=exclusive_maximum is not None,
            )
        )

    pattern = _get_logical_type_option(prop, "pattern")
    if pattern is not None:
        expectations.append(to_column_match_regex_exp(field_name, pattern))

    add_format_expectation(field_name, prop, expectations)

    enum_values = _get_logical_type_option(prop, "enum") or _get_enum_from_custom_properties(prop)
    if enum_values is not None and len(enum_values) != 0:
        expectations.append(to_column_enum_exp(field_name, enum_values))

    _warn_unsupported_logical_type_options(field_name, prop)

    return expectations


def add_format_expectation(
    field_name: str,
    prop: SchemaProperty,
    expectations: List[Dict[str, Any]],
) -> None:
    """Adds an expectation for the ``logicalTypeOptions.format`` option, when supported.

    Temporal logical types are translated to a strftime format expectation, strings with a
    known format to a regex expectation. The format of numeric logical types describes the
    storage of the value rather than a constraint, and is therefore ignored.

    Args:
        field_name (str): The name of the field.
        prop (SchemaProperty): The property object.
        expectations (List[Dict[str, Any]]): The expectations list to update.
    """
    format_option = _get_logical_type_option(prop, "format")
    if format_option is None:
        return
    logical_type = (prop.logicalType or "").lower()
    if logical_type in _TEMPORAL_LOGICAL_TYPES:
        strftime_format = _jdk_format_to_strftime(format_option)
        if strftime_format is None:
            logger.warning(
                "Great Expectations export: date format '%s' of column '%s' cannot be converted "
                "to a strftime format and is skipped.",
                format_option,
                field_name,
            )
            return
        expectations.append(to_column_strftime_format_exp(field_name, strftime_format))
    elif logical_type == "string":
        regex = _STRING_FORMAT_REGEX.get(format_option.lower())
        if regex is None:
            logger.warning(
                "Great Expectations export: string format '%s' of column '%s' is not supported and is skipped.",
                format_option,
                field_name,
            )
            return
        expectations.append(to_column_match_regex_exp(field_name, regex))


def add_column_order_exp(properties: List[SchemaProperty], expectations: List[Dict[str, Any]]):
    """Adds expectation for column ordering.

    Args:
        properties (List[SchemaProperty]): List of properties.
        expectations (List[Dict[str, Any]]): The expectations list to update.
    """
    column_names = [prop.name for prop in properties]
    expectations.append(
        {
            "type": "expect_table_columns_to_match_ordered_list",
            "kwargs": {"column_list": column_names},
            "meta": {"expectation_id": ""},
        }
    )


def to_column_types_exp(field_name, field_type) -> Dict[str, Any]:
    """Creates a column type expectation.

    Args:
        field_name (str): The name of the field.
        field_type (str): The type of the field.

    Returns:
        Dict[str, Any]: Column type expectation.
    """
    return {
        "type": "expect_column_values_to_be_of_type",
        "kwargs": {"column": field_name, "type_": field_type},
        "meta": {"expectation_id": ""},
    }


def to_column_unique_exp(field_name, mostly: Optional[float] = None) -> Dict[str, Any]:
    """Creates a column uniqueness expectation.

    Args:
        field_name (str): The name of the field.
        mostly (float | None): Optional GE ``mostly`` threshold (0.0–1.0).

    Returns:
        Dict[str, Any]: Column uniqueness expectation.
    """
    kwargs: Dict[str, Any] = {"column": field_name}
    if mostly is not None:
        kwargs["mostly"] = mostly
    return {
        "type": "expect_column_values_to_be_unique",
        "kwargs": kwargs,
        "meta": {"expectation_id": ""},
    }


def to_column_not_null_exp(field_name, mostly: Optional[float] = None) -> Dict[str, Any]:
    """Creates a column non-null expectation.

    Args:
        field_name (str): The name of the field.
        mostly (float | None): Optional GE ``mostly`` threshold (0.0–1.0).

    Returns:
        Dict[str, Any]: Column non-null expectation.
    """
    kwargs: Dict[str, Any] = {"column": field_name}
    if mostly is not None:
        kwargs["mostly"] = mostly
    return {
        "type": "expect_column_values_to_not_be_null",
        "kwargs": kwargs,
        "meta": {"expectation_id": ""},
    }


def to_column_match_regex_exp(field_name, regex: str) -> Dict[str, Any]:
    """Creates a column regex expectation.

    Args:
        field_name (str): The name of the field.
        regex (str): The regular expression the values must match.

    Returns:
        Dict[str, Any]: Column regex expectation.
    """
    return {
        "type": "expect_column_values_to_match_regex",
        "kwargs": {"column": field_name, "regex": regex},
        "meta": {"expectation_id": ""},
    }


def to_column_strftime_format_exp(field_name, strftime_format: str) -> Dict[str, Any]:
    """Creates a column strftime format expectation.

    Args:
        field_name (str): The name of the field.
        strftime_format (str): The strftime format the values must match.

    Returns:
        Dict[str, Any]: Column strftime format expectation.
    """
    return {
        "type": "expect_column_values_to_match_strftime_format",
        "kwargs": {"column": field_name, "strftime_format": strftime_format},
        "meta": {"expectation_id": ""},
    }


def to_column_length_exp(field_name, min_length, max_length) -> Dict[str, Any]:
    """Creates a column length expectation.

    Args:
        field_name (str): The name of the field.
        min_length (int | None): Minimum length.
        max_length (int | None): Maximum length.

    Returns:
        Dict[str, Any]: Column length expectation.
    """
    return {
        "type": "expect_column_value_lengths_to_be_between",
        "kwargs": {
            "column": field_name,
            "min_value": min_length,
            "max_value": max_length,
        },
        "meta": {"expectation_id": ""},
    }


def to_column_min_max_exp(
    field_name, minimum, maximum, strict_min: bool = False, strict_max: bool = False
) -> Dict[str, Any]:
    """Creates a column min-max value expectation.

    Args:
        field_name (str): The name of the field.
        minimum (float | None): Minimum value.
        maximum (float | None): Maximum value.
        strict_min (bool): Whether the minimum value is exclusive.
        strict_max (bool): Whether the maximum value is exclusive.

    Returns:
        Dict[str, Any]: Column min-max value expectation.
    """
    kwargs = {"column": field_name, "min_value": minimum, "max_value": maximum}
    if strict_min:
        kwargs["strict_min"] = True
    if strict_max:
        kwargs["strict_max"] = True
    return {
        "type": "expect_column_values_to_be_between",
        "kwargs": kwargs,
        "meta": {"expectation_id": ""},
    }


def to_column_enum_exp(field_name, enum_list: List[str]) -> Dict[str, Any]:
    """Creates a expect_column_values_to_be_in_set expectation.

    Args:
        field_name (str): The name of the field.
        enum_list (Set[str]): enum list of value.

    Returns:
        Dict[str, Any]: Column value in set expectation.
    """
    return {
        "type": "expect_column_values_to_be_in_set",
        "kwargs": {"column": field_name, "value_set": enum_list},
        "meta": {"expectation_id": ""},
    }


# ---------------------------------------------------------------------------
# Library quality support
# ---------------------------------------------------------------------------

_PERCENT_UNITS = {"percent", "percentage", "%"}


def _is_percent_unit(quality: DataQuality) -> bool:
    """True when the quality threshold is expressed as a percentage of rows."""
    unit = getattr(quality, "unit", None)
    return unit is not None and str(unit).strip().lower() in _PERCENT_UNITS


def _calculate_mostly(quality: DataQuality) -> Optional[float]:
    """Convert a Library error-threshold to a GE ``mostly`` value (0.0–1.0).

    Returns ``None`` when the threshold cannot be expressed as a fraction
    (e.g. row-based counts without cardinality information).
    """
    # mustBe: 0 means zero errors regardless of unit → 100% of rows must pass
    if quality.mustBe is not None and quality.mustBe == 0:
        return 1.0

    if not _is_percent_unit(quality):
        if quality.mustBeLessThan is not None or quality.mustBeLessOrEqualTo is not None:
            logger.warning(
                "Great Expectations export: Library quality row-based threshold cannot be "
                "converted to 'mostly' (row count unknown); 'mostly' will be omitted."
            )
        return None

    # Percent unit: error_percent → mostly = 1 - error_percent / 100
    if quality.mustBeLessThan is not None:
        return round(1.0 - quality.mustBeLessThan / 100.0, 10)
    if quality.mustBeLessOrEqualTo is not None:
        return round(1.0 - quality.mustBeLessOrEqualTo / 100.0, 10)
    if quality.mustBe is not None:
        return round(1.0 - quality.mustBe / 100.0, 10)

    logger.warning(
        "Great Expectations export: Library quality percent operator cannot be mapped to "
        "'mostly' (only mustBe/mustBeLessThan/mustBeLessOrEqualTo supported); 'mostly' omitted."
    )
    return None


def _has_library_quality_for_metric(prop: SchemaProperty, metric: str) -> bool:
    """True if the property has a Library quality covering the given metric."""
    if not prop.quality:
        return False
    return any(
        q is not None and q.metric is not None and q.metric.lower() == metric.lower()
        for q in prop.quality
    )


def _library_null_values_exp(quality: DataQuality, field_name: str) -> Dict[str, Any]:
    mostly = _calculate_mostly(quality)
    kwargs: Dict[str, Any] = {"column": field_name}
    if mostly is not None:
        kwargs["mostly"] = mostly
    return {
        "type": "expect_column_values_to_not_be_null",
        "kwargs": kwargs,
        "meta": {"expectation_id": quality.id or ""},
    }


def _library_invalid_values_exp(quality: DataQuality, field_name: str) -> Optional[Dict[str, Any]]:
    args = quality.arguments or {}
    valid_values = args.get("validValues")
    pattern = args.get("pattern")

    if valid_values is None and pattern is None:
        logger.warning(
            "Great Expectations export: Library invalidValues on field '%s' requires "
            "either validValues or pattern in arguments; skipping.",
            field_name,
        )
        return None

    mostly = _calculate_mostly(quality)

    if pattern is not None:
        kwargs: Dict[str, Any] = {"column": field_name, "regex": pattern}
        if mostly is not None:
            kwargs["mostly"] = mostly
        return {
            "type": "expect_column_values_to_match_regex",
            "kwargs": kwargs,
            "meta": {"expectation_id": quality.id or ""},
        }

    kwargs = {"column": field_name, "value_set": valid_values}
    if mostly is not None:
        kwargs["mostly"] = mostly
    return {
        "type": "expect_column_values_to_be_in_set",
        "kwargs": kwargs,
        "meta": {"expectation_id": quality.id or ""},
    }


def _library_duplicate_values_field_exp(quality: DataQuality, field_name: str) -> Dict[str, Any]:
    mostly = _calculate_mostly(quality)
    kwargs: Dict[str, Any] = {"column": field_name}
    if mostly is not None:
        kwargs["mostly"] = mostly
    return {
        "type": "expect_column_values_to_be_unique",
        "kwargs": kwargs,
        "meta": {"expectation_id": quality.id or ""},
    }


def _library_duplicate_values_schema_exp(quality: DataQuality) -> Optional[Dict[str, Any]]:
    args = quality.arguments or {}
    cols = args.get("properties")
    if not cols:
        logger.warning(
            "Great Expectations export: Library duplicateValues at schema level requires "
            "'properties' in arguments; skipping."
        )
        return None
    return {
        "type": "expect_compound_columns_to_be_unique",
        "kwargs": {"column_list": cols},
        "meta": {"expectation_id": quality.id or ""},
    }


def _library_row_count_exp(quality: DataQuality) -> Optional[Dict[str, Any]]:
    if quality.mustBe is not None:
        return {
            "type": "expect_table_row_count_to_equal",
            "kwargs": {"value": quality.mustBe},
            "meta": {"expectation_id": quality.id or ""},
        }

    min_value: Optional[int] = None
    max_value: Optional[int] = None

    if quality.mustBeBetween is not None and len(quality.mustBeBetween) == 2:
        min_value = quality.mustBeBetween[0]
        max_value = quality.mustBeBetween[1]
    else:
        if quality.mustBeGreaterThan is not None:
            min_value = quality.mustBeGreaterThan + 1
        elif quality.mustBeGreaterOrEqualTo is not None:
            min_value = quality.mustBeGreaterOrEqualTo
        if quality.mustBeLessThan is not None:
            max_value = quality.mustBeLessThan - 1
        elif quality.mustBeLessOrEqualTo is not None:
            max_value = quality.mustBeLessOrEqualTo

    if min_value is None and max_value is None:
        logger.warning("Great Expectations export: Library rowCount has no valid threshold; skipping.")
        return None

    kwargs: Dict[str, Any] = {}
    if min_value is not None:
        kwargs["min_value"] = min_value
    if max_value is not None:
        kwargs["max_value"] = max_value
    return {
        "type": "expect_table_row_count_to_be_between",
        "kwargs": kwargs,
        "meta": {"expectation_id": quality.id or ""},
    }


def _library_to_expectations(
    quality: DataQuality, field_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Dispatch a Library quality check to the appropriate GE expectation(s)."""
    metric = quality.metric
    if metric is None:
        return []

    metric_lower = metric.lower()

    if metric_lower == "nullvalues":
        if field_name is None:
            logger.warning("Great Expectations export: Library nullValues is only supported at field level.")
            return []
        return [_library_null_values_exp(quality, field_name)]

    if metric_lower == "invalidvalues":
        if field_name is None:
            logger.warning("Great Expectations export: Library invalidValues is only supported at field level.")
            return []
        exp = _library_invalid_values_exp(quality, field_name)
        return [exp] if exp is not None else []

    if metric_lower == "duplicatevalues":
        if field_name is not None:
            return [_library_duplicate_values_field_exp(quality, field_name)]
        exp = _library_duplicate_values_schema_exp(quality)
        return [exp] if exp is not None else []

    if metric_lower == "rowcount":
        exp = _library_row_count_exp(quality)
        return [exp] if exp is not None else []

    if metric_lower == "missingvalues":
        if field_name is None:
            logger.warning("Great Expectations export: Library missingValues is only supported at field level.")
            return []
        logger.warning(
            "Great Expectations export: Library 'missingValues' on field '%s' is not supported; "
            "skipping. Consider using 'invalidValues' with a validValues or pattern argument.",
            field_name,
        )
        return []

    logger.warning(
        "Great Expectations export: Library metric '%s' is not supported; skipping.",
        metric,
    )
    return []


def get_quality_checks(qualities: List[DataQuality], field_name: str | None = None) -> List[Dict[str, Any]]:
    """Retrieves quality checks defined in a data contract.

    Args:
        qualities (List[DataQuality]): List of quality object from the model specification.
        field_name (str | None): field name if the quality list is attached to a specific field

    Returns:
        List[Dict[str, Any]]: List of quality check specifications.
    """
    quality_specification = []
    for quality in qualities:
        if quality is None:
            continue
        # Library type: identified by metric being set; no engine needed
        if quality.metric is not None:
            quality_specification.extend(_library_to_expectations(quality, field_name))
            continue
        # Custom type: engine = "great-expectations" or "greatexpectations"
        if (
            quality.engine is not None
            and quality.engine.lower() in ("great-expectations", "greatexpectations")
        ):
            ge_expectation = quality.implementation
            if field_name is not None and isinstance(ge_expectation, dict):
                ge_expectation["column"] = field_name
            quality_specification.append(ge_expectation)
    return quality_specification
