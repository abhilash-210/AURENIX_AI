"""
Workspace management integration tests.

Tests cover:
- Workspace CRUD (create, list, get, rename, delete)
- Conversation CRUD (create, list, rename, delete)
- Workspace isolation for documents and conversations
- Unauthorized access guards
- Cascade delete verification
"""
from __future__ import annotations

import pytest
import asyncio
import uuid

import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import create_app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.chat import Conversation, Message
from app.models.document import Document

# ── Helpers ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def app():
    application = create_app()
    # Trigger the startup event to initialize DB tables
    async with application.router.lifespan_context(application):
        yield application


@pytest_asyncio.fixture(scope="module")
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture(scope="module")
async def auth_tokens(client: AsyncClient):
    """Register two users and return their tokens."""
    # User A
    email_a = f"user_a_{uuid.uuid4().hex[:6]}@test.com"
    res_a = await client.post("/api/v1/auth/register", json={
        "email": email_a, "password": "TestPass123!", "full_name": "User A"
    })
    assert res_a.status_code == 201
    login_a = await client.post("/api/v1/auth/login", json={"email": email_a, "password": "TestPass123!"})
    login_data_a = login_a.json().get("data", login_a.json())
    # Handle both {data: {token: {access_token}}} and {data: {access_token}} shapes
    token_a = (
        login_data_a.get("token", {}).get("access_token")
        or login_data_a.get("access_token")
    )
    assert token_a, f"Could not extract token_a from: {login_a.json()}"

    # User B
    email_b = f"user_b_{uuid.uuid4().hex[:6]}@test.com"
    res_b = await client.post("/api/v1/auth/register", json={
        "email": email_b, "password": "TestPass123!", "full_name": "User B"
    })
    assert res_b.status_code == 201
    login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "TestPass123!"})
    login_data_b = login_b.json().get("data", login_b.json())
    token_b = (
        login_data_b.get("token", {}).get("access_token")
        or login_data_b.get("access_token")
    )
    assert token_b, f"Could not extract token_b from: {login_b.json()}"

    return {"a": token_a, "b": token_b}


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════
# 1. WORKSPACE CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestWorkspaceCRUD:

    @pytest.mark.asyncio
    async def test_list_workspaces_auto_creates_default(self, client, auth_tokens):
        """First list call auto-creates a default workspace."""
        res = await client.get("/api/v1/workspaces", headers=auth_headers(auth_tokens["a"]))
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) >= 1
        assert data[0]["name"]  # has a name

    @pytest.mark.asyncio
    async def test_create_workspace(self, client, auth_tokens):
        """POST /workspaces creates a new workspace."""
        res = await client.post("/api/v1/workspaces",
            json={"name": "Company HR", "description": "HR workspace"},
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 201
        ws = res.json()["data"]
        assert ws["name"] == "Company HR"
        assert ws["id"]
        TestWorkspaceCRUD.workspace_a_id = ws["id"]

    @pytest.mark.asyncio
    async def test_create_second_workspace(self, client, auth_tokens):
        """Users can create multiple workspaces."""
        res = await client.post("/api/v1/workspaces",
            json={"name": "College Project"},
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 201
        ws = res.json()["data"]
        assert ws["name"] == "College Project"
        TestWorkspaceCRUD.workspace_b_id = ws["id"]

    @pytest.mark.asyncio
    async def test_list_workspaces_shows_all(self, client, auth_tokens):
        """User sees all their workspaces."""
        res = await client.get("/api/v1/workspaces", headers=auth_headers(auth_tokens["a"]))
        assert res.status_code == 200
        ids = [w["id"] for w in res.json()["data"]]
        assert TestWorkspaceCRUD.workspace_a_id in ids
        assert TestWorkspaceCRUD.workspace_b_id in ids

    @pytest.mark.asyncio
    async def test_get_single_workspace(self, client, auth_tokens):
        """GET /workspaces/{id} returns workspace details."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=auth_headers(auth_tokens["a"]))
        assert res.status_code == 200
        assert res.json()["data"]["id"] == ws_id

    @pytest.mark.asyncio
    async def test_get_workspace_unauthorized(self, client, auth_tokens):
        """User B cannot access User A's workspace."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=auth_headers(auth_tokens["b"]))
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_rename_workspace(self, client, auth_tokens):
        """PATCH /workspaces/{id} renames the workspace."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.patch(f"/api/v1/workspaces/{ws_id}",
            json={"name": "Company HR (Updated)"},
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "Company HR (Updated)"

    @pytest.mark.asyncio
    async def test_rename_workspace_unauthorized(self, client, auth_tokens):
        """User B cannot rename User A's workspace."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.patch(f"/api/v1/workspaces/{ws_id}",
            json={"name": "Hacked"},
            headers=auth_headers(auth_tokens["b"]),
        )
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_delete_workspace(self, client, auth_tokens):
        """DELETE /workspaces/{id} removes workspace."""
        ws_id = TestWorkspaceCRUD.workspace_b_id
        res = await client.delete(f"/api/v1/workspaces/{ws_id}", headers=auth_headers(auth_tokens["a"]))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_deleted_workspace_not_found(self, client, auth_tokens):
        """Deleted workspace returns 404."""
        ws_id = TestWorkspaceCRUD.workspace_b_id
        res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=auth_headers(auth_tokens["a"]))
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_deleted_workspace_not_in_list(self, client, auth_tokens):
        """Deleted workspace does not appear in list."""
        res = await client.get("/api/v1/workspaces", headers=auth_headers(auth_tokens["a"]))
        ids = [w["id"] for w in res.json()["data"]]
        assert TestWorkspaceCRUD.workspace_b_id not in ids


# ═══════════════════════════════════════════════════════════════════════
# 2. CONVERSATION CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestConversationCRUD:

    @pytest.mark.asyncio
    async def test_create_conversation(self, client, auth_tokens):
        """POST /workspaces/{id}/conversations creates a conversation."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.post(f"/api/v1/workspaces/{ws_id}/conversations",
            json={"title": "Leave Policy Discussion"},
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 201
        conv = res.json()
        assert conv["title"] == "Leave Policy Discussion"
        TestConversationCRUD.conv_a_id = conv["id"]

    @pytest.mark.asyncio
    async def test_create_second_conversation(self, client, auth_tokens):
        """Multiple conversations can exist in a workspace."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.post(f"/api/v1/workspaces/{ws_id}/conversations",
            json={"title": "Employee Benefits"},
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 201
        TestConversationCRUD.conv_b_id = res.json()["id"]

    @pytest.mark.asyncio
    async def test_list_conversations(self, client, auth_tokens):
        """GET lists both conversations."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.get(f"/api/v1/workspaces/{ws_id}/conversations",
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 200
        ids = [c["id"] for c in res.json()["items"]]
        assert TestConversationCRUD.conv_a_id in ids
        assert TestConversationCRUD.conv_b_id in ids

    @pytest.mark.asyncio
    async def test_rename_conversation(self, client, auth_tokens):
        """PATCH renames a conversation."""
        conv_id = TestConversationCRUD.conv_a_id
        res = await client.patch(f"/api/v1/conversations/{conv_id}",
            json={"title": "Leave Policy (Renamed)"},
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 200
        assert res.json()["title"] == "Leave Policy (Renamed)"

    @pytest.mark.asyncio
    async def test_rename_conversation_unauthorized(self, client, auth_tokens):
        """User B cannot rename User A's conversation."""
        conv_id = TestConversationCRUD.conv_a_id
        res = await client.patch(f"/api/v1/conversations/{conv_id}",
            json={"title": "Hacked"},
            headers=auth_headers(auth_tokens["b"]),
        )
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_delete_conversation(self, client, auth_tokens):
        """DELETE removes a conversation."""
        conv_id = TestConversationCRUD.conv_b_id
        res = await client.delete(f"/api/v1/conversations/{conv_id}",
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_deleted_conversation_not_in_list(self, client, auth_tokens):
        """Deleted conversation no longer appears in list."""
        ws_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.get(f"/api/v1/workspaces/{ws_id}/conversations",
            headers=auth_headers(auth_tokens["a"]),
        )
        ids = [c["id"] for c in res.json()["items"]]
        assert TestConversationCRUD.conv_b_id not in ids

    @pytest.mark.asyncio
    async def test_deleted_conversation_messages_gone(self, client, auth_tokens):
        """Messages of deleted conversation return 404."""
        conv_id = TestConversationCRUD.conv_b_id
        res = await client.get(f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_headers(auth_tokens["a"]),
        )
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_delete_conversation_unauthorized(self, client, auth_tokens):
        """User B cannot delete User A's remaining conversation."""
        conv_id = TestConversationCRUD.conv_a_id
        res = await client.delete(f"/api/v1/conversations/{conv_id}",
            headers=auth_headers(auth_tokens["b"]),
        )
        assert res.status_code in (403, 404)


# ═══════════════════════════════════════════════════════════════════════
# 3. WORKSPACE ISOLATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestWorkspaceIsolation:

    @pytest.mark.asyncio
    async def test_conversations_isolated_between_workspaces(self, client, auth_tokens):
        """Conversations from workspace A don't appear in workspace B."""
        # Create workspace C for User A
        res_c = await client.post("/api/v1/workspaces",
            json={"name": "Personal Research"},
            headers=auth_headers(auth_tokens["a"]),
        )
        ws_c_id = res_c.json()["data"]["id"]

        # Create conversation in workspace A
        ws_a_id = TestWorkspaceCRUD.workspace_a_id
        conv_res = await client.post(f"/api/v1/workspaces/{ws_a_id}/conversations",
            json={"title": "WS-A Conversation"},
            headers=auth_headers(auth_tokens["a"]),
        )
        conv_a_id = conv_res.json()["id"]

        # Workspace C list should NOT contain WS-A conversation
        list_res = await client.get(f"/api/v1/workspaces/{ws_c_id}/conversations",
            headers=auth_headers(auth_tokens["a"]),
        )
        ids_in_c = [c["id"] for c in list_res.json()["items"]]
        assert conv_a_id not in ids_in_c, "Workspace A conversation leaked into Workspace C"

        # Cleanup
        await client.delete(f"/api/v1/workspaces/{ws_c_id}", headers=auth_headers(auth_tokens["a"]))

    @pytest.mark.asyncio
    async def test_cross_user_workspace_access_denied(self, client, auth_tokens):
        """User B cannot access User A's workspace conversations."""
        ws_a_id = TestWorkspaceCRUD.workspace_a_id
        res = await client.get(f"/api/v1/workspaces/{ws_a_id}/conversations",
            headers=auth_headers(auth_tokens["b"]),
        )
        # Should be forbidden since B is not a member
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_workspace_delete_cascades_conversations(self, client, auth_tokens):
        """Deleting a workspace removes its conversations."""
        # Create fresh workspace + conversation
        ws_res = await client.post("/api/v1/workspaces",
            json={"name": "Temp Workspace"},
            headers=auth_headers(auth_tokens["a"]),
        )
        temp_ws_id = ws_res.json()["data"]["id"]

        conv_res = await client.post(f"/api/v1/workspaces/{temp_ws_id}/conversations",
            json={"title": "Temp Conv"},
            headers=auth_headers(auth_tokens["a"]),
        )
        temp_conv_id = conv_res.json()["id"]

        # Delete workspace
        del_res = await client.delete(f"/api/v1/workspaces/{temp_ws_id}",
            headers=auth_headers(auth_tokens["a"]),
        )
        assert del_res.status_code == 200

        # Verify conversation is gone (DB cascade)
        msg_res = await client.get(f"/api/v1/conversations/{temp_conv_id}/messages",
            headers=auth_headers(auth_tokens["a"]),
        )
        assert msg_res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_unauthenticated_workspace_access_denied(self, client):
        """Unauthenticated requests are rejected."""
        res = await client.get("/api/v1/workspaces")
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_conversation_access_denied(self, client):
        """Unauthenticated conversation creation is rejected."""
        fake_ws = str(uuid.uuid4())
        res = await client.post(f"/api/v1/workspaces/{fake_ws}/conversations",
            json={"title": "Unauthorized conv"},
        )
        assert res.status_code == 401
