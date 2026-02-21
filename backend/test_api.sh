#!/bin/bash
# Quick API Test Script
# Tests authentication and new features

BASE_URL="http://localhost:8080"

echo "========================================"
echo "BRD Generator API - Test Script"
echo "========================================"

# Test 1: Health Check
echo -e "\n1. Health Check"
curl -s $BASE_URL/health | python3 -m json.tool

# Test 2: Register User
echo -e "\n2. Register User"
REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "display_name": "Test User"
  }')

echo "$REGISTER_RESPONSE" | python3 -m json.tool

# Extract token (custom token - need to exchange for ID token in real app)
TOKEN=$(echo "$REGISTER_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "ERROR: Failed to get token. User might already exist."
  echo "Trying to verify with existing token..."
  # In real app, you'd do Firebase sign-in to get ID token
  echo "NOTE: For real testing, use Firebase SDK to sign in and get ID token"
  exit 1
fi

echo "Token: $TOKEN"

# Test 3: Verify Token (requires Firebase ID token, not custom token)
echo -e "\n3. Get Current User (requires ID token)"
echo "NOTE: Custom token needs to be exchanged for ID token via Firebase SDK"
echo "Skipping this test - would need Firebase client SDK"

# Test 4: List Projects (requires auth)
echo -e "\n4. List Projects (requires authentication)"
echo "NOTE: Would need valid ID token from Firebase"

# Test 5: Create Project (requires auth)
echo -e "\n5. Create Project (requires authentication)"
echo "NOTE: Would need valid ID token from Firebase"

echo -e "\n========================================"
echo "API Routes Available:"
echo "========================================"
echo "Auth:"
echo "  POST /auth/register - Register new user"
echo "  GET  /auth/me - Get current user info (requires auth)"
echo "  POST /auth/verify - Verify token (requires auth)"
echo ""
echo "Projects:"
echo "  GET  /projects - List all user's projects (requires auth)"
echo "  POST /projects - Create project (requires auth)"
echo "  GET  /projects/{id} - Get project details (requires auth)"
echo ""
echo "Documents:"
echo "  POST /projects/{id}/documents/upload - Upload files (multiple supported!)"
echo "  GET  /projects/{id}/documents - List documents"
echo "  GET  /projects/{id}/documents/{doc_id} - Get document"
echo ""
echo "BRDs:"
echo "  POST /projects/{id}/brds/generate - Generate BRD"
echo "  GET  /projects/{id}/brds - List BRDs"
echo "  GET  /projects/{id}/brds/{brd_id} - Get BRD"
echo ""
echo "Documentation: http://localhost:8080/docs"
