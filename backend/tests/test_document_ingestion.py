"""
Integration tests for document ingestion service and API routes.
"""

from __future__ import annotations

import io
import uuid
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import create_app
from app.models.user import User
from app.models.workspace import Workspace
from app.routes.auth import get_current_user
from app.services.ingestion.service import DocumentIngestionService


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"ingest_test_{user_id.hex[:8]}@aurenix.ai",
        hashed_password="hashed_pwd_stub",
        full_name="Ingest User",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def sample_workspace(db_session: AsyncSession, sample_user: User) -> Workspace:
    from app.models.workspace import WorkspaceMember
    ws_id = uuid.uuid4()
    workspace = Workspace(
        id=ws_id,
        name="Ingestion Workspace",
        slug=f"ingest-ws-{ws_id.hex[:8]}",
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=sample_user.id,
        role="owner",
    )
    db_session.add(member)
    await db_session.commit()
    return workspace


@pytest.fixture
def auth_client(client: AsyncClient, sample_user: User):
    # Override get_current_user dependency on app
    app = client._transport.app
    app.dependency_overrides[get_current_user] = lambda: sample_user
    return client


class TestDocumentIngestionService:
    @pytest.mark.asyncio
    async def test_ingest_txt_file(self, db_session: AsyncSession, sample_user: User, sample_workspace: Workspace):
        service = DocumentIngestionService(db_session)
        content = b"Heading\n\nThis is paragraph one of the ingested text document.\nParagraph two here."

        result = await service.ingest_document(
            content=content,
            filename="report.txt",
            workspace_id=sample_workspace.id,
            owner_id=sample_user.id,
            chunk_size=100,
            chunk_overlap=20,
        )

        assert result.status == "completed"
        assert result.filename == "report.txt"
        assert result.file_type == "txt"
        assert result.chunk_count >= 1

        # Check DB record
        doc = await service.get_document(result.document_id)
        assert doc is not None
        assert doc.status == "completed"
        assert doc.total_chunks == result.chunk_count

        # Check chunks
        chunks = await service.get_document_chunks(result.document_id)
        assert len(chunks) == result.chunk_count
        assert "paragraph one" in chunks[0].content

    @pytest.mark.asyncio
    async def test_ingest_csv_file(self, db_session: AsyncSession, sample_user: User, sample_workspace: Workspace):
        service = DocumentIngestionService(db_session)
        content = b"id,name,score\n1,Alice,95\n2,Bob,88\n"

        result = await service.ingest_document(
            content=content,
            filename="scores.csv",
            workspace_id=sample_workspace.id,
            owner_id=sample_user.id,
        )

        assert result.status == "completed"
        assert result.file_type == "csv"

        chunks = await service.get_document_chunks(result.document_id)
        assert len(chunks) == 2
        assert chunks[0].row_number == 1
        assert "Alice" in chunks[0].content


class TestDocumentEndpoints:
    @pytest.mark.asyncio
    async def test_upload_document_endpoint_success(self, auth_client: AsyncClient, sample_workspace: Workspace):
        files = {"file": ("test.txt", b"API upload test content text", "text/plain")}
        response = await auth_client.post(
            f"/api/v1/workspaces/{sample_workspace.id}/documents/upload",
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert "data" in data
        doc_data = data["data"]
        assert doc_data["filename"] == "test.txt"
        assert doc_data["status"] == "completed"
        doc_id = doc_data["id"]

        # Fetch details endpoint
        detail_res = await auth_client.get(f"/api/v1/documents/{doc_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["data"]["id"] == doc_id

        # Fetch chunks endpoint for vector layer consumption
        chunks_res = await auth_client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert chunks_res.status_code == 200
        chunks_data = chunks_res.json()["data"]
        assert len(chunks_data) >= 1
        assert chunks_data[0]["document_id"] == doc_id
        assert "metadata" in chunks_data[0]

    @pytest.mark.asyncio
    async def test_upload_document_unsupported_type(self, auth_client: AsyncClient, sample_workspace: Workspace):
        files = {"file": ("malicious.exe", b"MZbinarycontent", "application/octet-stream")}
        response = await auth_client.post(
            f"/api/v1/workspaces/{sample_workspace.id}/documents/upload",
            files=files,
        )

        assert response.status_code == 415
        assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_list_workspace_documents(self, auth_client: AsyncClient, sample_workspace: Workspace):
        # Upload two documents
        await auth_client.post(
            f"/api/v1/workspaces/{sample_workspace.id}/documents/upload",
            files={"file": ("doc1.txt", b"Doc 1 content", "text/plain")},
        )
        await auth_client.post(
            f"/api/v1/workspaces/{sample_workspace.id}/documents/upload",
            files={"file": ("doc2.txt", b"Doc 2 content", "text/plain")},
        )

        response = await auth_client.get(f"/api/v1/workspaces/{sample_workspace.id}/documents")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 2
