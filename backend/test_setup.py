"""
Test script to validate backend setup.
Run this to ensure all configurations are working.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_config():
    """Test configuration loading."""
    print("=" * 60)
    print("Testing Configuration...")
    print("=" * 60)

    try:
        from config import settings, firestore_client, storage_bucket, litellm_router

        print("✅ Settings loaded")
        print(f"   - Project: {settings.google_cloud_project}")
        print(f"   - Bucket: {settings.storage_bucket}")
        print(f"   - Environment: {settings.environment}")
        print(f"   - Gemini Model: {settings.gemini_model}")

        print("✅ Firestore client initialized")
        print(f"   - Type: {type(firestore_client).__name__}")

        print("✅ Storage bucket initialized")
        print(f"   - Name: {storage_bucket.name}")

        print("✅ LiteLLM router initialized")
        print(f"   - Type: {type(litellm_router).__name__}")

        return True

    except Exception as e:
        print(f"❌ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_models():
    """Test Pydantic models."""
    print("\n" + "=" * 60)
    print("Testing Pydantic Models...")
    print("=" * 60)

    try:
        from models import (
            Project, ProjectCreate,
            Document, AIMetadata,
            BRD, BRDSection, Citation
        )
        from datetime import datetime

        # Test Project model
        project = Project(
            project_id="proj_test123",
            name="Test Project",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        print(f"✅ Project model: {project.project_id}")

        # Test serialization
        json_data = project.model_dump(mode='json')
        print(f"✅ Project serialization works")

        print("✅ All models imported successfully")
        return True

    except Exception as e:
        print(f"❌ Models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_services():
    """Test service imports."""
    print("\n" + "=" * 60)
    print("Testing Services...")
    print("=" * 60)

    try:
        from services import (
            firestore_service,
            storage_service,
            gemini_service,
            document_service,
            agent_service
        )

        print("✅ Firestore service imported")
        print("✅ Storage service imported")
        print("✅ Gemini service imported")
        print("✅ Document service imported")
        print("✅ Agent service imported")

        return True

    except Exception as e:
        print(f"❌ Services test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_prompts():
    """Test prompt loading."""
    print("\n" + "=" * 60)
    print("Testing Prompts...")
    print("=" * 60)

    try:
        from utils import prompts

        # List available prompts
        keys = prompts.list_keys()
        print(f"✅ Loaded {len(keys)} prompts")

        # Test a few key prompts
        test_keys = [
            "document_classification",
            "requirement_extraction",
            "brd_section_executive_summary"
        ]

        for key in test_keys:
            prompt = prompts.get(key)
            print(f"✅ Prompt '{key}': {len(prompt)} chars")

        return True

    except Exception as e:
        print(f"❌ Prompts test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_routes():
    """Test route imports."""
    print("\n" + "=" * 60)
    print("Testing Routes...")
    print("=" * 60)

    try:
        from routes import projects_router, documents_router, brds_router

        print(f"✅ Projects router: {projects_router.prefix}")
        print(f"✅ Documents router: {documents_router.prefix}")
        print(f"✅ BRDs router: {brds_router.prefix}")

        return True

    except Exception as e:
        print(f"❌ Routes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_tools():
    """Test agent tools."""
    print("\n" + "=" * 60)
    print("Testing Agent Tools...")
    print("=" * 60)

    try:
        from agent.tools import AgentTools, ToolExecutor
        from config import firestore_client, storage_bucket

        tools = AgentTools(
            firestore_client=firestore_client,
            storage_client=storage_bucket.client
        )

        executor = ToolExecutor(tools)

        print("✅ AgentTools initialized")
        print("✅ ToolExecutor initialized")

        return True

    except Exception as e:
        print(f"❌ Agent tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n🚀 BRD Generator Backend - Setup Validation\n")

    results = []

    results.append(await test_config())
    results.append(await test_models())
    results.append(await test_services())
    results.append(await test_prompts())
    results.append(await test_routes())
    results.append(await test_agent_tools())

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nTests passed: {passed}/{total}")

    if passed == total:
        print("\n✅ All tests passed! Backend is ready.")
        print("\nNext steps:")
        print("1. Run: python main.py")
        print("2. Visit: http://localhost:8080/docs")
        print("3. Test API endpoints")
    else:
        print("\n❌ Some tests failed. Fix errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
