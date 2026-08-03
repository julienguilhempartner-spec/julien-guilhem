"""
Tests for Library quality type conversion to Great Expectations suites.

Covers all 6 Library metrics (nullValues, invalidValues, duplicateValues,
missingValues, rowCount) and all operator/unit combinations.
"""

import json
import logging

import pytest
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.great_expectations_exporter import to_great_expectations
from datacontract.lint import resolve


@pytest.fixture
def odcs_library() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/datacontract_library_quality.yaml"
    )


# ---------------------------------------------------------------------------
# nullValues
# ---------------------------------------------------------------------------


def test_library_null_values_mustbe_zero():
    """nullValues + mustBe: 0 → expect_column_values_to_not_be_null, no mostly."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col_a
        logicalType: string
        quality:
          - id: col_a_no_nulls
            metric: nullValues
            mustBe: 0
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    expectations = result["expectations"]
    null_exp = next(e for e in expectations if e["type"] == "expect_column_values_to_not_be_null")
    assert null_exp["kwargs"] == {"column": "col_a", "mostly": 1.0}
    assert null_exp["meta"] == {"expectation_id": "col_a_no_nulls"}


def test_library_null_values_percent_less_than():
    """nullValues + mustBeLessThan: 1 percent → mostly: 0.99."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: email
        logicalType: string
        quality:
          - id: email_null_pct
            metric: nullValues
            mustBeLessThan: 1
            unit: percent
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    null_exp = next(
        e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null"
    )
    assert null_exp["kwargs"]["mostly"] == pytest.approx(0.99)
    assert null_exp["meta"] == {"expectation_id": "email_null_pct"}


def test_library_null_values_percent_less_or_equal():
    """nullValues + mustBeLessOrEqualTo: 2 percent → mostly: 0.98."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        quality:
          - id: col_null_2pct
            metric: nullValues
            mustBeLessOrEqualTo: 2
            unit: percent
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    null_exp = next(
        e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null"
    )
    assert null_exp["kwargs"]["mostly"] == pytest.approx(0.98)


def test_library_null_values_rows_no_mostly(caplog):
    """nullValues + mustBeLessThan: 10 (rows) → no mostly, warning logged."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        quality:
          - id: col_null_rows
            metric: nullValues
            mustBeLessThan: 10
"""
    )
    with caplog.at_level(logging.WARNING):
        result = json.loads(to_great_expectations(odcs, "tbl"))
    null_exp = next(
        e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null"
    )
    assert "mostly" not in null_exp["kwargs"]
    assert any("row-based threshold" in msg.lower() or "mostly" in msg.lower() for msg in caplog.messages)


# ---------------------------------------------------------------------------
# invalidValues
# ---------------------------------------------------------------------------


def test_library_invalid_values_valid_set():
    """invalidValues + validValues list + mustBe: 0 → expect_column_values_to_be_in_set."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: status
        logicalType: string
        quality:
          - id: status_valid
            metric: invalidValues
            mustBe: 0
            arguments:
              validValues:
                - PENDING
                - COMPLETED
                - FAILED
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_in_set")
    assert exp["kwargs"]["value_set"] == ["PENDING", "COMPLETED", "FAILED"]
    assert exp["kwargs"]["mostly"] == 1.0
    assert exp["meta"] == {"expectation_id": "status_valid"}


def test_library_invalid_values_valid_set_with_tolerance():
    """invalidValues + validValues list + mustBeLessThan: 5 percent → mostly: 0.95."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: category
        logicalType: string
        quality:
          - id: cat_valid_with_tolerance
            metric: invalidValues
            mustBeLessThan: 5
            unit: percent
            arguments:
              validValues:
                - A
                - B
                - C
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_in_set")
    assert exp["kwargs"]["mostly"] == pytest.approx(0.95)


def test_library_invalid_values_pattern():
    """invalidValues + pattern + mustBe: 0 → expect_column_values_to_match_regex."""
    odcs = OpenDataContractStandard.from_string(
        r"""
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: iban
        logicalType: string
        quality:
          - id: iban_pattern
            metric: invalidValues
            mustBe: 0
            arguments:
              pattern: '^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$'
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_match_regex")
    assert exp["kwargs"]["regex"] == r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$"
    assert exp["kwargs"]["mostly"] == 1.0
    assert exp["meta"] == {"expectation_id": "iban_pattern"}


def test_library_invalid_values_no_args_logs_warning(caplog):
    """invalidValues without validValues or pattern → warning logged, no expectation."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        quality:
          - id: col_no_args
            metric: invalidValues
            mustBe: 0
"""
    )
    with caplog.at_level(logging.WARNING):
        result = json.loads(to_great_expectations(odcs, "tbl"))
    types = [e["type"] for e in result["expectations"]]
    assert "expect_column_values_to_be_in_set" not in types
    assert "expect_column_values_to_match_regex" not in types
    assert any("validValues" in msg or "pattern" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# duplicateValues (column-level)
# ---------------------------------------------------------------------------


def test_library_duplicate_values_mustbe_zero():
    """duplicateValues + mustBe: 0 → expect_column_values_to_be_unique, mostly: 1.0."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: order_id
        logicalType: string
        quality:
          - id: order_id_unique
            metric: duplicateValues
            mustBe: 0
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_unique")
    assert exp["kwargs"] == {"column": "order_id", "mostly": 1.0}
    assert exp["meta"] == {"expectation_id": "order_id_unique"}


def test_library_duplicate_values_percent():
    """duplicateValues + mustBeLessThan: 1 percent → mostly: 0.99."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: code
        logicalType: string
        quality:
          - id: code_dup_pct
            metric: duplicateValues
            mustBeLessThan: 1
            unit: percent
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_unique")
    assert exp["kwargs"]["mostly"] == pytest.approx(0.99)


# ---------------------------------------------------------------------------
# rowCount (schema-level)
# ---------------------------------------------------------------------------


def test_library_row_count_between():
    """rowCount + mustBeBetween: [1000, 5000] → expect_table_row_count_to_be_between."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    quality:
      - id: tbl_row_count
        metric: rowCount
        mustBeBetween: [1000, 5000]
    properties:
      - name: col
        logicalType: string
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(
        e for e in result["expectations"] if e["type"] == "expect_table_row_count_to_be_between"
    )
    assert exp["kwargs"] == {"min_value": 1000, "max_value": 5000}
    assert exp["meta"] == {"expectation_id": "tbl_row_count"}


def test_library_row_count_greater_than():
    """rowCount + mustBeGreaterThan: 100 → min_value: 101."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    quality:
      - id: tbl_row_gt
        metric: rowCount
        mustBeGreaterThan: 100
    properties:
      - name: col
        logicalType: string
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(
        e for e in result["expectations"] if e["type"] == "expect_table_row_count_to_be_between"
    )
    assert exp["kwargs"]["min_value"] == 101
    assert "max_value" not in exp["kwargs"]


def test_library_row_count_greater_or_equal():
    """rowCount + mustBeGreaterOrEqualTo: 100 → min_value: 100."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    quality:
      - id: tbl_row_ge
        metric: rowCount
        mustBeGreaterOrEqualTo: 100
    properties:
      - name: col
        logicalType: string
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(
        e for e in result["expectations"] if e["type"] == "expect_table_row_count_to_be_between"
    )
    assert exp["kwargs"]["min_value"] == 100


def test_library_row_count_equal():
    """rowCount + mustBe: 500 → expect_table_row_count_to_equal."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    quality:
      - id: tbl_row_equal
        metric: rowCount
        mustBe: 500
    properties:
      - name: col
        logicalType: string
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_table_row_count_to_equal")
    assert exp["kwargs"] == {"value": 500}
    assert exp["meta"] == {"expectation_id": "tbl_row_equal"}


# ---------------------------------------------------------------------------
# duplicateValues (schema-level, compound)
# ---------------------------------------------------------------------------


def test_library_compound_unique():
    """duplicateValues (schema) + properties list → expect_compound_columns_to_be_unique."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    quality:
      - id: compound_unique
        metric: duplicateValues
        mustBe: 0
        arguments:
          properties:
            - tenant_id
            - order_id
    properties:
      - name: tenant_id
        logicalType: string
      - name: order_id
        logicalType: string
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(
        e for e in result["expectations"] if e["type"] == "expect_compound_columns_to_be_unique"
    )
    assert exp["kwargs"]["column_list"] == ["tenant_id", "order_id"]
    assert exp["meta"] == {"expectation_id": "compound_unique"}


def test_library_compound_unique_no_properties_logs_warning(caplog):
    """duplicateValues (schema) without properties → warning, no expectation."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    quality:
      - id: compound_no_cols
        metric: duplicateValues
        mustBe: 0
    properties:
      - name: col
        logicalType: string
"""
    )
    with caplog.at_level(logging.WARNING):
        result = json.loads(to_great_expectations(odcs, "tbl"))
    types = [e["type"] for e in result["expectations"]]
    assert "expect_compound_columns_to_be_unique" not in types
    assert any("properties" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# missingValues (unsupported in Phase 1)
# ---------------------------------------------------------------------------


def test_library_missing_values_unsupported(caplog):
    """missingValues → warning logged, no expectation generated."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        quality:
          - id: col_missing
            metric: missingValues
            mustBeLessThan: 1
            unit: percent
            arguments:
              missingValues:
                - null
                - ""
                - "N/A"
"""
    )
    with caplog.at_level(logging.WARNING):
        result = json.loads(to_great_expectations(odcs, "tbl"))
    types = [e["type"] for e in result["expectations"]]
    assert not any("missing" in t for t in types)
    assert any("missingValues" in msg or "missing_values" in msg.lower() for msg in caplog.messages)


# ---------------------------------------------------------------------------
# Unsupported metric
# ---------------------------------------------------------------------------


def test_library_unsupported_metric_logs_warning(caplog):
    """Unknown metric → warning logged, no expectation."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        quality:
          - id: col_unknown
            metric: unknownMetric
            mustBe: 0
"""
    )
    with caplog.at_level(logging.WARNING):
        result = json.loads(to_great_expectations(odcs, "tbl"))
    exp_count = sum(
        1 for e in result["expectations"] if e.get("meta", {}).get("expectation_id") == "col_unknown"
    )
    assert exp_count == 0
    assert any("unknownMetric" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# Schema attribute strict rules (mostly: 1.0)
# ---------------------------------------------------------------------------


def test_column_required_gets_mostly_1():
    """required: true → expect_column_values_to_not_be_null with mostly: 1.0."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        required: true
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null")
    assert exp["kwargs"] == {"column": "col", "mostly": 1.0}
    assert exp["meta"] == {"expectation_id": ""}


def test_column_unique_gets_mostly_1():
    """unique: true → expect_column_values_to_be_unique with mostly: 1.0."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: code
        logicalType: string
        unique: true
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_unique")
    assert exp["kwargs"] == {"column": "code", "mostly": 1.0}
    assert exp["meta"] == {"expectation_id": ""}


def test_column_primarykey_gets_both_strict():
    """primaryKey: true → both not_null and unique expectations with mostly: 1.0."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: id
        logicalType: string
        primaryKey: true
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    exps = result["expectations"]
    not_null = next(e for e in exps if e["type"] == "expect_column_values_to_not_be_null")
    unique = next(e for e in exps if e["type"] == "expect_column_values_to_be_unique")
    assert not_null["kwargs"] == {"column": "id", "mostly": 1.0}
    assert unique["kwargs"] == {"column": "id", "mostly": 1.0}


def test_library_overrides_required_attribute():
    """Library nullValues quality overrides required: true schema attribute (Library wins)."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: email
        logicalType: string
        required: true
        quality:
          - id: email_null_pct
            metric: nullValues
            mustBeLessThan: 1
            unit: percent
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    null_exps = [e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null"]
    # Only one not_null expectation (from Library), not two
    assert len(null_exps) == 1
    assert null_exps[0]["kwargs"]["mostly"] == pytest.approx(0.99)
    assert null_exps[0]["meta"] == {"expectation_id": "email_null_pct"}


def test_library_overrides_unique_attribute():
    """Library duplicateValues quality overrides unique: true schema attribute (Library wins)."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: code
        logicalType: string
        unique: true
        quality:
          - id: code_dup_pct
            metric: duplicateValues
            mustBeLessThan: 5
            unit: percent
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    unique_exps = [e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_unique"]
    # Only one unique expectation (from Library), not two
    assert len(unique_exps) == 1
    assert unique_exps[0]["kwargs"]["mostly"] == pytest.approx(0.95)
    assert unique_exps[0]["meta"] == {"expectation_id": "code_dup_pct"}


# ---------------------------------------------------------------------------
# expectation_id in meta
# ---------------------------------------------------------------------------


def test_expectation_id_uses_quality_id():
    """expectation_id in meta should match the quality id field."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        quality:
          - id: MY_QUALITY_RULE_001
            metric: nullValues
            mustBe: 0
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    null_exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null")
    assert null_exp["meta"]["expectation_id"] == "MY_QUALITY_RULE_001"


def test_expectation_id_empty_when_no_quality_id():
    """expectation_id in meta is empty string when quality has no id field."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        quality:
          - metric: nullValues
            mustBe: 0
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    null_exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null")
    assert null_exp["meta"]["expectation_id"] == ""


def test_schema_derived_expectations_have_expectation_id_in_meta():
    """Schema-derived expectations (not from Library quality) have empty expectation_id in meta."""
    odcs = OpenDataContractStandard.from_string(
        """
kind: DataContract
apiVersion: v3.1.0
id: test
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: col
        logicalType: string
        required: true
        unique: true
"""
    )
    result = json.loads(to_great_expectations(odcs, "tbl"))
    for exp in result["expectations"]:
        assert "expectation_id" in exp["meta"], f"Missing expectation_id in {exp['type']}"


# ---------------------------------------------------------------------------
# Full fixture integration test
# ---------------------------------------------------------------------------


def test_library_full_fixture(odcs_library: OpenDataContractStandard, caplog):
    """Integration test against the full Library quality fixture YAML."""
    with caplog.at_level(logging.WARNING):
        result = json.loads(to_great_expectations(odcs_library, "orders"))

    expectations = result["expectations"]
    types = [e["type"] for e in expectations]

    # Schema-level: 3 rowCount (between, gt, equal) + compound unique
    assert types.count("expect_table_row_count_to_be_between") == 2
    assert types.count("expect_table_row_count_to_equal") == 1
    assert types.count("expect_compound_columns_to_be_unique") == 1

    # Column: order_id Library nullValues (mustBe: 0) — primaryKey skipped due to Library override
    order_id_null = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_not_be_null"
        and e["kwargs"].get("column") == "order_id"
    ]
    assert len(order_id_null) == 1
    assert order_id_null[0]["kwargs"]["mostly"] == 1.0
    assert order_id_null[0]["meta"]["expectation_id"] == "order_id_no_nulls"

    # order_id primaryKey unique: NOT skipped (no Library duplicateValues quality)
    order_id_unique = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_be_unique"
        and e["kwargs"].get("column") == "order_id"
    ]
    assert len(order_id_unique) == 1
    assert order_id_unique[0]["kwargs"]["mostly"] == 1.0

    # email: Library nullValues overrides required: true
    email_null = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_not_be_null"
        and e["kwargs"].get("column") == "email"
    ]
    assert len(email_null) == 1
    assert email_null[0]["kwargs"]["mostly"] == pytest.approx(0.99)

    # phone: invalidValues with pattern
    phone_regex = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_match_regex"
        and e["kwargs"].get("column") == "phone"
    ]
    assert len(phone_regex) == 1

    # product_code: Library duplicateValues overrides unique: true
    product_code_unique = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_be_unique"
        and e["kwargs"].get("column") == "product_code"
    ]
    assert len(product_code_unique) == 1
    assert product_code_unique[0]["kwargs"]["mostly"] == pytest.approx(0.95)

    # status: invalidValues with validValues
    status_set = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_be_in_set"
        and e["kwargs"].get("column") == "status"
    ]
    assert len(status_set) == 1
    assert set(status_set[0]["kwargs"]["value_set"]) == {"PENDING", "COMPLETED", "FAILED"}

    # missing_column: should be skipped with a warning
    assert not any("missing_column" in str(e.get("kwargs", {})) for e in expectations)
    assert any("missingValues" in msg for msg in caplog.messages)

    # tenant_id: required: true → strict mostly: 1.0
    tenant_null = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_not_be_null"
        and e["kwargs"].get("column") == "tenant_id"
    ]
    assert len(tenant_null) == 1
    assert tenant_null[0]["kwargs"]["mostly"] == 1.0

    # notes: row-based threshold → no mostly, warning logged
    notes_set = [
        e for e in expectations
        if e["type"] == "expect_column_values_to_be_in_set"
        and e["kwargs"].get("column") == "notes"
    ]
    assert len(notes_set) == 1
    assert "mostly" not in notes_set[0]["kwargs"]
