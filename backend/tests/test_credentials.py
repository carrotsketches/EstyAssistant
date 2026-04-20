"""Direct tests for the DynamoDB-backed credentials module via moto."""

import importlib
import os

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def dynamo_table():
    """Spin up a mock DynamoDB table and reload the credentials module against it."""
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["DYNAMODB_TABLE"] = "test-credentials"

    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="test-credentials",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Reload to reset the cached _table handle against the mocked client.
        from api import credentials
        credentials._table = None
        importlib.reload(credentials)
        yield credentials
        credentials._table = None


class TestCredentials:
    def test_save_and_load_roundtrip(self, dynamo_table):
        dynamo_table.save_credentials(
            api_key="key", access_token="access", refresh_token="refresh",
            user_id="user-1", shop_id="shop-1",
        )
        creds = dynamo_table.load_credentials()
        assert creds["api_key"] == "key"
        assert creds["access_token"] == "access"
        assert creds["user_id"] == "user-1"
        assert creds["shop_id"] == "shop-1"

    def test_load_returns_none_when_missing(self, dynamo_table):
        assert dynamo_table.load_credentials() is None

    def test_delete_credentials(self, dynamo_table):
        dynamo_table.save_credentials("k", "a", "r", "u")
        dynamo_table.delete_credentials()
        assert dynamo_table.load_credentials() is None

    def test_save_without_shop_id_normalizes_to_none(self, dynamo_table):
        dynamo_table.save_credentials("k", "a", "r", "u")
        creds = dynamo_table.load_credentials()
        assert creds["shop_id"] is None


class TestOAuthState:
    def test_save_and_consume(self, dynamo_table):
        dynamo_table.save_oauth_state("state-abc", "verifier-xyz", "http://cb")
        loaded = dynamo_table.load_oauth_state("state-abc")
        assert loaded == {"verifier": "verifier-xyz", "redirect_uri": "http://cb"}

    def test_load_consumes_single_use(self, dynamo_table):
        dynamo_table.save_oauth_state("state-abc", "v", "http://cb")
        dynamo_table.load_oauth_state("state-abc")
        assert dynamo_table.load_oauth_state("state-abc") is None

    def test_load_unknown_state_returns_none(self, dynamo_table):
        assert dynamo_table.load_oauth_state("nope") is None


class TestJobs:
    def test_create_and_get(self, dynamo_table):
        dynamo_table.create_job("job-1")
        job = dynamo_table.get_job("job-1")
        assert job == {"status": "pending"}

    def test_update_with_result(self, dynamo_table):
        dynamo_table.create_job("job-2")
        dynamo_table.update_job("job-2", "completed", result={"listing_id": "42"})
        job = dynamo_table.get_job("job-2")
        assert job["status"] == "completed"
        assert job["result"] == {"listing_id": "42"}

    def test_update_with_error(self, dynamo_table):
        dynamo_table.create_job("job-3")
        dynamo_table.update_job("job-3", "failed", error="boom")
        job = dynamo_table.get_job("job-3")
        assert job["status"] == "failed"
        assert job["error"] == "boom"

    def test_get_unknown_job_returns_none(self, dynamo_table):
        assert dynamo_table.get_job("missing") is None


class TestListings:
    def test_save_returns_dict(self, dynamo_table):
        out = dynamo_table.save_listing(
            "abc", "Title", ["tag1", "tag2"], "Desc",
            price=4.99, s3_key="uploads/a", sizes=["8x10"],
            etsy_listing_id="E1", etsy_listing_url="https://etsy/1",
            preview_url="https://preview/1",
        )
        assert out["id"] == "abc"
        assert out["title"] == "Title"
        assert out["price"] == 4.99
        assert out["etsy_listing_id"] == "E1"

    def test_list_sorted_desc_by_created_at(self, dynamo_table):
        dynamo_table.save_listing("a", "First", [], "")
        dynamo_table.save_listing("b", "Second", [], "")
        listings = dynamo_table.list_listings()
        assert {l["id"] for l in listings} == {"a", "b"}

    def test_list_respects_limit(self, dynamo_table):
        for i in range(5):
            dynamo_table.save_listing(f"id-{i}", f"T{i}", [], "")
        assert len(dynamo_table.list_listings(limit=3)) == 3

    def test_get_listing_roundtrip(self, dynamo_table):
        dynamo_table.save_listing("abc", "Title", ["t"], "D")
        got = dynamo_table.get_listing("abc")
        assert got["id"] == "abc"
        assert got["title"] == "Title"

    def test_get_missing_returns_none(self, dynamo_table):
        assert dynamo_table.get_listing("nope") is None

    def test_delete_listing(self, dynamo_table):
        dynamo_table.save_listing("abc", "T", [], "")
        assert dynamo_table.delete_listing("abc") is True
        assert dynamo_table.get_listing("abc") is None

    def test_delete_missing_returns_false(self, dynamo_table):
        assert dynamo_table.delete_listing("nope") is False


class TestCustomTemplates:
    def test_save_returns_dict(self, dynamo_table):
        out = dynamo_table.save_custom_template(
            "t1", "My Frame", "templates/t1.jpg",
            orientation="horizontal", frame_bbox=[10, 20, 100, 200],
        )
        assert out["id"] == "t1"
        assert out["name"] == "My Frame"
        assert out["orientation"] == "horizontal"
        assert out["frame_bbox"] == [10, 20, 100, 200]
        assert out["is_custom"] is True

    def test_list_templates(self, dynamo_table):
        dynamo_table.save_custom_template("a", "A", "k/a")
        dynamo_table.save_custom_template("b", "B", "k/b")
        templates = dynamo_table.list_custom_templates()
        assert {t["id"] for t in templates} == {"a", "b"}

    def test_delete_template(self, dynamo_table):
        dynamo_table.save_custom_template("a", "A", "k/a")
        assert dynamo_table.delete_custom_template("a") is True
        assert dynamo_table.list_custom_templates() == []

    def test_delete_missing_template_returns_false(self, dynamo_table):
        assert dynamo_table.delete_custom_template("nope") is False
