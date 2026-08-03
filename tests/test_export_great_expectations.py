import json
import logging
from typing import Any, Dict

import pytest
from datacontract_specification.model import DataContractSpecification
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.great_expectations_exporter import to_great_expectations
from datacontract.imports.dcs_importer import convert_dcs_to_odcs
from datacontract.lint import resolve

# logging.basicConfig(level=logging.DEBUG, force=True)

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
UUID_REGEX = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "great-expectations",
            "./fixtures/export/datacontract.odcs.yaml",
        ],
    )
    assert result.exit_code == 0


@pytest.fixture
def data_contract_basic() -> OpenDataContractStandard:
    return OpenDataContractStandard.from_file("fixtures/export/datacontract.odcs.yaml")


@pytest.fixture
def data_contract_complex() -> OpenDataContractStandard:
    dcs = DataContractSpecification.from_file("fixtures/export/rdf/datacontract-complex.yaml")
    return convert_dcs_to_odcs(dcs)


@pytest.fixture
def odcs() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location("./fixtures/great-expectations/odcs.yaml")


@pytest.fixture
def data_contract_great_expectations_quality_yaml() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/datacontract_quality_yaml.yaml",
    )


@pytest.fixture
def data_contract_great_expectations_quality_column() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/datacontract_quality_column.yaml",
    )


@pytest.fixture
def odcs_logical_type_options() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/odcs_logical_type_options.yaml",
    )


@pytest.fixture
def expected_json_suite() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "timestamp"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_json_suite_table_quality() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {"type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 10}, "meta": {}},
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_json_suite_with_enum() -> Dict[str, Any]:
    return {
        "name": "orders.1.1.1",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["id", "type"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "id", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {"type": "expect_column_values_to_not_be_null", "kwargs": {"column": "id", "mostly": 1.0}, "meta": {"expectation_id": ""}},
            {"type": "expect_column_values_to_be_unique", "kwargs": {"column": "id", "mostly": 1.0}, "meta": {"expectation_id": ""}},
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "type", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "type", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "type", "value_set": ["A", "B", "C", "D", "E"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_value_lengths_to_equal",
                "kwargs": {"value": 1},
                "meta": {"notes": "Ensures that column length is 1."},
                "column": "type",
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_spark_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "StringType"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "TimestampType"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_pandas_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "str"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "datetime64[ns]"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_sql_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "STRING"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "TIMESTAMP_TZ"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_sql_trino_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "varchar"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {
                    "column": "processed_timestamp",
                    "type_": "timestamp(3) with time zone",
                },
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }


def test_to_great_expectation(data_contract_basic: OpenDataContractStandard):
    expected_json_suite = {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "order_total", "order_status"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "varchar"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_value_lengths_to_be_between",
                "kwargs": {"column": "order_id", "min_value": 8, "max_value": 10},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "order_id", "regex": "^B[0-9]+$"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_total", "type_": "bigint"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_total", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "order_total",
                    "min_value": 0,
                    "max_value": 1000000,
                },
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_status", "type_": "text"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_status", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_status", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "order_status", "value_set": ["pending", "shipped", "delivered"]},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }

    result_orders = to_great_expectations(data_contract_basic, "orders")
    assert result_orders == json.dumps(expected_json_suite, indent=2)


def test_to_great_expectation_complex(data_contract_complex: OpenDataContractStandard):
    """
    Test with 2 model definitions in the contract
    """

    expected_orders = {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {
                    "column_list": [
                        "order_id",
                        "order_timestamp",
                        "order_total",
                        "customer_id",
                        "customer_email_address",
                    ]
                },
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "text"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "order_id", "regex": UUID_REGEX},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_timestamp", "type_": "timestamp"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_timestamp", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_total", "type_": "long"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_total", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "customer_id", "type_": "text"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_value_lengths_to_be_between",
                "kwargs": {"column": "customer_id", "min_value": 10, "max_value": 20},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "customer_email_address", "type_": "text"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "customer_email_address", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "customer_email_address", "regex": EMAIL_REGEX},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }

    expected_line_items = {
        "name": "line_items.1.0.0",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["lines_item_id", "order_id", "sku"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "lines_item_id", "type_": "text"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "lines_item_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "lines_item_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "text"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "order_id", "regex": UUID_REGEX},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "sku", "type_": "text"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "sku", "regex": "^[A-Za-z0-9]{8,14}$"},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }
    result_orders = to_great_expectations(data_contract_complex, "orders")
    assert result_orders == json.dumps(expected_orders, indent=2)

    result_line_items = to_great_expectations(data_contract_complex, "line_items")

    assert result_line_items == json.dumps(expected_line_items, indent=2)


def test_to_great_expectation_quality(
    odcs: OpenDataContractStandard,
    expected_json_suite: Dict[str, Any],
):
    """
    Test with Quality definition in the contract
    """

    result = to_great_expectations(odcs, "orders")
    assert result == json.dumps(expected_json_suite, indent=2)


def test_to_great_expectation_custom_name(
    odcs: OpenDataContractStandard,
):
    """
    Test with Quality definition in the contract
    """
    expected = {
        "name": "my_expectation_suite_name",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "timestamp"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }

    result = to_great_expectations(
        odcs,
        schema_name="orders",
        expectation_suite_name="my_expectation_suite_name",
    )
    assert result == json.dumps(expected, indent=2)


def test_to_great_expectation_engine_spark(
    odcs: OpenDataContractStandard,
    expected_spark_engine: Dict[str, Any],
):
    """
    Test with Spark engine
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="spark",
    )
    assert result == json.dumps(expected_spark_engine, indent=2)


def test_to_great_expectation_engine_pandas(
    odcs: OpenDataContractStandard,
    expected_pandas_engine: Dict[str, Any],
):
    """
    Test with pandas engine
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="pandas",
    )
    assert result == json.dumps(expected_pandas_engine, indent=2)


def test_to_great_expectation_engine_sql(
    odcs: OpenDataContractStandard,
    expected_sql_engine: Dict[str, Any],
):
    """
    Test with sql engine
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="sql",
    )
    assert result == json.dumps(expected_sql_engine, indent=2)


def test_to_great_expectation_engine_sql_trino(
    odcs: OpenDataContractStandard,
    expected_sql_trino_engine: Dict[str, Any],
):
    """
    Test with sql engine and sql server trino trino
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="sql",
        sql_server_type="trino",
    )
    assert result == json.dumps(expected_sql_trino_engine, indent=2)


def test_cli_with_spark_engine(expected_spark_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
            "--engine",
            "spark",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_spark_engine, indent=2).replace("\n", "")


def test_cli_with_pandas_engine(expected_pandas_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
            "--engine",
            "pandas",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_pandas_engine, indent=2).replace("\n", "")


def test_cli_with_sql_engine(expected_sql_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
            "--engine",
            "sql",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_sql_engine, indent=2).replace("\n", "")


def test_cli_with_sql_trino_engine(expected_sql_trino_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
            "--engine",
            "sql",
            "--dialect",
            "trino",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_sql_trino_engine, indent=2).replace("\n", "")


def test_to_great_expectation_quality_yaml(
    data_contract_great_expectations_quality_yaml: OpenDataContractStandard,
    expected_json_suite_table_quality: Dict[str, Any],
):
    """
    Test with Quality definition in a model quality list
    """
    result = to_great_expectations(data_contract_great_expectations_quality_yaml, "orders")
    assert result == json.dumps(expected_json_suite_table_quality, indent=2)


def test_to_great_expectation_quality_column(
    data_contract_great_expectations_quality_column: OpenDataContractStandard,
    expected_json_suite_with_enum: Dict[str, Any],
):
    """
    Test with quality definition in a field quality list
    """
    result = to_great_expectations(data_contract_great_expectations_quality_column, "orders")
    assert result == json.dumps(expected_json_suite_with_enum, indent=2)


def test_to_great_expectation_logical_type_options(odcs_logical_type_options: OpenDataContractStandard):
    """
    Test that primaryKey, required, unique and the logicalTypeOptions are converted to expectations
    """
    expected = {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {
                    "column_list": [
                        "order_id",
                        "customer_email",
                        "discount_code",
                        "order_total",
                        "quantity",
                        "order_date",
                        "processed_at",
                        "legacy_code",
                    ]
                },
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_id", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "customer_email", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "customer_email", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "customer_email", "regex": EMAIL_REGEX},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "discount_code", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "discount_code", "mostly": 1.0},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_value_lengths_to_be_between",
                "kwargs": {"column": "discount_code", "min_value": 4, "max_value": None},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "discount_code", "regex": "^[A-Z]+$"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_total", "type_": "number"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "order_total",
                    "min_value": 0,
                    "max_value": 1000000,
                    "strict_min": True,
                    "strict_max": True,
                },
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "quantity", "type_": "integer"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "quantity",
                    "min_value": 1,
                    "max_value": 100,
                    "strict_max": True,
                },
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_date", "type_": "date"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_strftime_format",
                "kwargs": {"column": "order_date", "strftime_format": "%Y-%m-%d"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_at", "type_": "timestamp"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_match_strftime_format",
                "kwargs": {"column": "processed_at", "strftime_format": "%Y-%m-%dT%H:%M:%S"},
                "meta": {"expectation_id": ""},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "legacy_code", "type_": "string"},
                "meta": {"expectation_id": ""},
            },
        ],
        "meta": {},
    }

    result = to_great_expectations(odcs_logical_type_options, "orders")
    assert result == json.dumps(expected, indent=2)


def test_to_great_expectation_unsupported_options_are_logged(
    odcs_logical_type_options: OpenDataContractStandard,
    caplog: pytest.LogCaptureFixture,
):
    """
    Test that logical type options without a Great Expectations equivalent are logged
    """
    with caplog.at_level(logging.WARNING, logger="datacontract.export.great_expectations_exporter"):
        to_great_expectations(odcs_logical_type_options, "orders")

    messages = [record.getMessage() for record in caplog.records]
    assert any("multipleOf" in message and "quantity" in message for message in messages)
    assert any("timezone" in message and "processed_at" in message for message in messages)
    assert any("binary" in message and "legacy_code" in message for message in messages)
