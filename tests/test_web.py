"""Tests for the FastAPI web interface."""

import io
import textwrap

import pytest
from fastapi.testclient import TestClient

from isolint.web import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_xml_bytes():
    return textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                         xmlns:gco="http://www.isotc211.org/2005/gco">
          <gmd:fileIdentifier>
            <gco:CharacterString>web-test</gco:CharacterString>
          </gmd:fileIdentifier>
          <gmd:language>
            <gco:CharacterString>eng</gco:CharacterString>
          </gmd:language>
          <gmd:contact>
            <gco:CharacterString>Test</gco:CharacterString>
          </gmd:contact>
          <gmd:dateStamp>
            <gco:Date>2026-04-15</gco:Date>
          </gmd:dateStamp>
          <gmd:identificationInfo>
            <gmd:title>
              <gco:CharacterString>Web Test</gco:CharacterString>
            </gmd:title>
            <gmd:abstract>
              <gco:CharacterString>Abstract text that is long enough to pass minimum length checks for quality.</gco:CharacterString>
            </gmd:abstract>
          </gmd:identificationInfo>
        </gmd:MD_Metadata>
    """).encode()


class TestWebAPI:
    def test_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "isolint" in resp.text

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_validate_xml(self, client, sample_xml_bytes):
        resp = client.post(
            "/validate",
            files=[("files", ("test.xml", io.BytesIO(sample_xml_bytes), "application/xml"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "passed" in data
        assert "findings" in data

    def test_suggest_xml(self, client, sample_xml_bytes):
        resp = client.post(
            "/suggest",
            files=[("files", ("test.xml", io.BytesIO(sample_xml_bytes), "application/xml"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data

    def test_fair_xml(self, client, sample_xml_bytes):
        resp = client.post(
            "/fair",
            files=[("files", ("test.xml", io.BytesIO(sample_xml_bytes), "application/xml"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "overall" in data["score"]
        assert "grade" in data["score"]
