import os
import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.pipeline.pdf_parser import PDFParser
from backend.app.pipeline.normalizer import FactNormalizer
from backend.app.pipeline.fact_extractor import FactExtractionEngine
from backend.app.pipeline.entity_resolution import EntityResolutionEngine
from backend.app.pipeline.candidate_matcher import CandidateFactMatcher
from backend.app.pipeline.relationship_engine import RelationshipEngine
from backend.app.sample_generator import generate_sample_pdfs

client = TestClient(app)

# ---------------------------------------------------------
# Normalization Tests
# ---------------------------------------------------------

def test_number_normalization():
    res1 = FactNormalizer.normalize_number_and_unit("$4.2 billion")
    assert res1["normalized_value"] == 4_200_000_000.0
    assert res1["currency"] == "USD"
    assert res1["fact_type"] == "CURRENCY"

    res2 = FactNormalizer.normalize_number_and_unit("14,200")
    assert res2["normalized_value"] == 14200.0
    assert res2["fact_type"] == "NUMERICAL"

    res3 = FactNormalizer.normalize_number_and_unit("USD 0.5 billion")
    assert res3["normalized_value"] == 500_000_000.0
    assert res3["currency"] == "USD"

    res4 = FactNormalizer.normalize_number_and_unit("€120 million")
    assert res4["normalized_value"] == 120_000_000.0
    assert res4["currency"] == "EUR"

def test_percentage_normalization():
    res1 = FactNormalizer.normalize_number_and_unit("32%")
    assert res1["normalized_value"] == 32.0
    assert res1["unit"] == "%"
    assert res1["fact_type"] == "PERCENTAGE"

    res2 = FactNormalizer.normalize_number_and_unit("21.4 percent")
    assert res2["normalized_value"] == 21.4
    assert res2["fact_type"] == "PERCENTAGE"

def test_temporal_normalization():
    t1 = FactNormalizer.extract_temporal_context("Revenue for FY2025 was $500 million.")
    assert t1["temporal_type"] == "FISCAL_YEAR"
    assert t1["temporal_year"] == 2025

    t2 = FactNormalizer.extract_temporal_context("Q1 FY2025 cloud revenue was $120 million.")
    assert t2["temporal_type"] == "QUARTER"
    assert t2["temporal_quarter"] == 1

    t3 = FactNormalizer.extract_temporal_context("Accelerate capex by 40% in the coming cycle.")
    assert t3["temporal_type"] == "RELATIVE"
    assert t3["is_relative"] is True

def test_fy2025_vs_q1_not_automatically_contradictory():
    """Explicit requirement check: FY2025 revenue and Q1 FY2025 revenue must not be automatically contradictory."""
    fact_fy = {
        "id": "F-TEST-1",
        "subject": "ABC Corporation",
        "predicate": "revenue",
        "raw_value": "$500 million",
        "fact_type": "CURRENCY",
        "normalized_value": 500000000.0,
        "temporal_period": "FY2025",
        "temporal_type": "FISCAL_YEAR",
        "evidence": {"filename": "Form_10K.pdf", "source_text": "Revenue for FY2025 was $500 million."}
    }
    
    fact_q1 = {
        "id": "F-TEST-2",
        "subject": "ABC Corporation",
        "predicate": "revenue",
        "raw_value": "$120 million",
        "fact_type": "CURRENCY",
        "normalized_value": 120000000.0,
        "temporal_period": "Q1 FY2025",
        "temporal_type": "QUARTER",
        "evidence": {"filename": "Q1_Report.pdf", "source_text": "Revenue for Q1 FY2025 was $120 million."}
    }

    rel = RelationshipEngine.analyze_pair(fact_fy, fact_q1)
    assert rel["category"] in ["CONTEXTUALIZES", "TEMPORAL_CHANGE"]
    assert rel["category"] != "CONTRADICTS"

# ---------------------------------------------------------
# Entity Resolution Tests
# ---------------------------------------------------------

def test_entity_resolution():
    norm1 = EntityResolutionEngine.normalize_entity_name("ABC Corporation Inc.")
    norm2 = EntityResolutionEngine.normalize_entity_name("ABC Corp LLC")
    assert norm1 == "abc"
    assert norm2 == "abc"

    facts = [
        {"subject": "ABC Corporation Inc.", "predicate": "revenue", "raw_value": "$500M"},
        {"subject": "ABC Corp", "predicate": "revenue", "raw_value": "$500M"},
        {"subject": "XYZ Logistics Ltd.", "predicate": "headcount", "raw_value": "5000"}
    ]
    res_map = EntityResolutionEngine.resolve_entities(facts)
    assert res_map["ABC Corporation Inc."] == res_map["ABC Corp"]
    assert res_map["ABC Corporation Inc."] != res_map["XYZ Logistics Ltd."]

# ---------------------------------------------------------
# Relationship Engine Tests
# ---------------------------------------------------------

def test_corroboration_logic():
    fact_a = {
        "id": "F-001",
        "subject": "Cloud Infrastructure segment",
        "predicate": "revenue",
        "raw_value": "$4.2 billion",
        "fact_type": "CURRENCY",
        "normalized_value": 4200000000.0,
        "temporal_period": "Q4 2023",
        "evidence": {"filename": "Earnings.pdf", "source_text": "Cloud Infrastructure segment revenue reached $4.2 billion."}
    }
    fact_b = {
        "id": "F-003",
        "subject": "cloud business",
        "predicate": "revenue",
        "raw_value": "$4.2B",
        "fact_type": "CURRENCY",
        "normalized_value": 4200000000.0,
        "temporal_period": "Q4 2023",
        "evidence": {"filename": "Letter.pdf", "source_text": "Our cloud business crossed $4.2B in the fourth quarter."}
    }

    rel = RelationshipEngine.analyze_pair(fact_a, fact_b)
    assert rel["category"] == "CORROBORATES"

def test_contradiction_logic():
    fact_a = {
        "id": "F-004",
        "subject": "global permanent headcount",
        "predicate": "headcount",
        "raw_value": "14,200",
        "fact_type": "NUMERICAL",
        "normalized_value": 14200.0,
        "temporal_period": "December 31, 2023",
        "evidence": {"filename": "Workforce.pdf", "source_text": "Total headcount stood at 14,200."}
    }
    fact_b = {
        "id": "F-005",
        "subject": "active permanent employees",
        "predicate": "headcount",
        "raw_value": "15,800",
        "fact_type": "NUMERICAL",
        "normalized_value": 15800.0,
        "temporal_period": "December 31, 2023",
        "evidence": {"filename": "ESG.pdf", "source_text": "Closed fiscal year with 15,800 active permanent employees."}
    }

    rel = RelationshipEngine.analyze_pair(fact_a, fact_b)
    assert rel["category"] == "CONTRADICTS"

def test_contextual_difference_gaap_vs_nongaap():
    fact_a = {
        "id": "F-006",
        "subject": "operating margin",
        "predicate": "operating margin",
        "raw_value": "21.4%",
        "fact_type": "PERCENTAGE",
        "normalized_value": 21.4,
        "temporal_period": "FY2023",
        "scope_qualifiers": ["GAAP"],
        "evidence": {"filename": "Form10K.pdf", "source_text": "GAAP Operating Margin contracted to 21.4%."}
    }
    fact_b = {
        "id": "F-007",
        "subject": "operating margin",
        "predicate": "operating margin",
        "raw_value": "28.6%",
        "fact_type": "PERCENTAGE",
        "normalized_value": 28.6,
        "temporal_period": "FY2023",
        "scope_qualifiers": ["Non-GAAP"],
        "evidence": {"filename": "Presentation.pdf", "source_text": "Adjusted Non-GAAP Operating Margin was 28.6%."}
    }

    rel = RelationshipEngine.analyze_pair(fact_a, fact_b)
    assert rel["category"] == "CONTEXTUALIZES"

def test_failure_case_handling():
    fact_a = {
        "id": "F-008",
        "subject": "the newly formed regional subsidiary",
        "predicate": "capital deployment growth",
        "raw_value": "40%",
        "fact_type": "PERCENTAGE",
        "normalized_value": 40.0,
        "temporal_type": "RELATIVE",
        "temporal_period": "coming cycle",
        "evidence": {"filename": "StrategyMemo.pdf", "source_text": "The newly formed regional subsidiary will accelerate capital deployment by an additional 40% in the coming cycle."}
    }
    fact_b = {
        "id": "F-001",
        "subject": "ABC Corporation",
        "predicate": "revenue",
        "raw_value": "$500 million",
        "fact_type": "CURRENCY",
        "temporal_period": "FY2025",
        "evidence": {"filename": "Report.pdf", "source_text": "ABC Corporation revenue was $500M."}
    }

    rel = RelationshipEngine.analyze_pair(fact_a, fact_b)
    assert rel["category"] == "UNCERTAIN"
    assert rel["diagnostic_fix"] is not None

# ---------------------------------------------------------
# Upload Limits & Edge Cases Tests
# ---------------------------------------------------------

def test_non_pdf_upload_rejected():
    fake_file = io.BytesIO(b"not a real pdf content")
    response = client.post(
        "/api/documents",
        files={"file": ("test.txt", fake_file, "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]

def test_pdf_parser_missing_file():
    with pytest.raises(FileNotFoundError):
        PDFParser.parse_pdf("non_existent_file_path_12345.pdf")

# ---------------------------------------------------------
# API End-to-End Test
# ---------------------------------------------------------

def test_demo_seed_api():
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["documents"]) == 7

    # Check documents endpoints (both /documents and /api/documents)
    docs_resp = client.get("/documents")
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    assert len(docs) == 7

    first_doc_id = docs[0]["id"]
    doc_facts_resp = client.get(f"/documents/{first_doc_id}/facts")
    assert doc_facts_resp.status_code == 200
    assert isinstance(doc_facts_resp.json(), list)

    # Check facts endpoints
    facts_resp = client.get("/facts")
    assert facts_resp.status_code == 200
    facts = facts_resp.json()
    assert len(facts) >= 7

    # Check fact-level relationships
    first_fact_id = facts[0]["id"]
    fact_rel_resp = client.get(f"/facts/{first_fact_id}/relationships")
    assert fact_rel_resp.status_code == 200

    # Check relationships endpoint
    rel_resp = client.get("/relationships")
    assert rel_resp.status_code == 200
    rels = rel_resp.json()
    assert len(rels) >= 3

    categories = set([r["category"] for r in rels])
    assert "CORROBORATES" in categories
    assert "CONTRADICTS" in categories
    assert "CONTEXTUALIZES" in categories

    # Health check
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"
