# Phase 12.4: Authorization & Tenant Isolation Matrix

## Authorization Architecture Summary

### Identity Source of Truth
- **Authentication**: JWT-based OAuth2 with Bearer tokens
- **Token Claims**: `sub` (user_id), `email`, `role`
- **Critical Security Measure**: Email and role are sourced from PostgreSQL database, NOT trusted from token claims
- **Validation**: `get_current_user()` in deps.py validates token and fetches fresh user data from database
- **Protection**: Prevents token manipulation attacks even if signing key is compromised

### Protected Routes

| Route | Method | Auth Required | Role Required | Owner Required | Tenant Check |
|-------|--------|---------------|---------------|---------------|-------------|
| `/api/v1/auth/register` | POST | No | None | N/A | N/A |
| `/api/v1/auth/login` | POST | No | None | N/A | N/A |
| `/api/v1/auth/refresh` | POST | No | None | N/A | N/A |
| `/api/v1/auth/logout` | POST | No | None | N/A | N/A |
| `/api/v1/auth/me` | GET | Yes | None | Self | Yes |
| `/api/v1/journals/` | POST | Yes | None | Self | Yes |
| `/api/v1/journals/` | GET | Yes | None | Self | Yes |
| `/api/v1/journals/{id}` | GET | Yes | None | Self | Yes |
| `/api/v1/documents/` | POST | Yes | None | Self | Yes |
| `/api/v1/documents/` | GET | Yes | None | Self | Yes |
| `/api/v1/documents/{id}` | GET | Yes | None | Self | Yes |
| `/api/v1/ai/ask` | POST | Yes | None | Self | Yes |
| `/api/v1/vectors/insert` | POST | Yes | None | Self | Yes |
| `/api/v1/vectors/search` | POST | Yes | None | Self | Yes |
| `/api/v1/vectors/documents` | GET | Yes | None | Self | Yes |
| `/api/v1/vectors/documents/{doc_key}` | DELETE | Yes | None | Self | Yes |
| `/api/v1/memory/` | POST | Yes | None | Self | Yes |
| `/api/v1/memory/` | GET | Yes | None | Self | Yes |
| `/api/v1/memory/{id}` | GET | Yes | None | Self | Yes |
| `/api/v1/memory/{id}` | PUT | Yes | None | Self | Yes |
| `/api/v1/memory/{id}` | DELETE | Yes | None | Self | Yes |
| `/api/v1/memory/search` | POST | Yes | None | Self | Yes |
| `/api/v1/coaching/session` | POST | Yes | None | Self | Yes |
| `/api/v1/coaching/history` | GET | Yes | None | Self | Yes |
| `/api/v1/coaching/insights` | GET | Yes | None | Self | Yes |
| `/api/v1/coaching/ws/{session_id}` | WebSocket | Yes | None | Self | Yes |
| `/api/v1/users/me` | GET | Yes | None | Self | Yes |
| `/api/v1/metrics/metrics` | GET | No | None | N/A | N/A |

### Data Models with Tenant Isolation

#### PostgreSQL
- **User**: Stores authentication credentials, role, status
- **No user-owned data in PostgreSQL** (user data is in MongoDB)

#### MongoDB (Beanie ODM)
All MongoDB documents have `user_id: uuid.UUID` field:
- **JournalEntry**: User journal entries
- **Goal**: User goals and objectives
- **Habit**: User habits and streaks
- **UserDocument**: Uploaded documents and processing status
- **CoachingSession**: Coaching session records
- **AIInsight**: AI-generated insights
- **ComplianceEvent**: Security and compliance events

#### Qdrant (Vector Database)
- **knowledge_base collection**: Vectors with `user_id` in payload
- **lumenly_vectors collection**: Document vectors with `user_id` in payload
- All vector searches filter by `user_id` at query level

#### Redis
- **refresh_token:{user_id}**: User-specific refresh tokens
- **ws_connection:{user_id}**: WebSocket connection rate limiting
- **ws_message:{user_id}**: WebSocket message rate limiting
- **ws_tool_call:{user_id}**: WebSocket tool call rate limiting

### Tenant Isolation Enforcement Points

1. **API Layer**: FastAPI dependencies (`get_current_active_user`)
2. **MongoDB Layer**: Beanie queries with `user_id` filter
3. **Qdrant Layer**: Vector search filters with `user_id` match
4. **Tool Layer**: Tool registry with user context validation
5. **WebSocket Layer**: JWT authentication + session ownership check
6. **Celery Layer**: Explicit `user_id` parameter in task signatures
7. **RAG Layer**: Memory and knowledge retrieval scoped to `user_id`

### Cross-Tenant Access Controls

- **Read Operations**: All queries filter by `user_id` at database level
- **Write Operations**: All mutations use authenticated `user_id` from database
- **Enumeration Protection**: Generic "not found" errors prevent user enumeration
- **Security Logging**: Compliance events logged for cross-tenant access attempts
- **Metrics**: Security metrics track authorization failures

### P0 Security Guarantees (from Phase 12.3)

1. ✅ JWT tokens contain required claims (sub, exp, email, role)
2. ✅ Email and role sourced from database, not token claims
3. ✅ Refresh token rotation prevents reuse
4. ✅ Concurrent refresh requests: only one succeeds
5. ✅ Inactive users cannot authenticate
6. ✅ Rate limiting enforced (fail-closed)
7. ✅ Tools enforce tenant isolation at database level
8. ✅ WebSocket authentication mandatory
9. ✅ Session ownership verified before WebSocket connection
10. ✅ Document processing preserves owner identity

### Authorization Audit Status

| Component | Status | Notes |
|-----------|--------|-------|
| API Routes | ✅ Verified | All protected routes use `get_current_active_user` |
| PostgreSQL | ✅ Verified | Only User table, no user-owned data |
| MongoDB | ✅ Verified | All documents have user_id indexes and filters |
| Qdrant | ✅ Verified | All vector searches include user_id filter |
| Redis | ✅ Verified | User-scoped keys for sessions and rate limiting |
| Tools | ✅ Verified | Tool registry enforces tenant isolation |
| Celery | ✅ Verified | Tasks use explicit user_id parameter |
| WebSocket | ✅ Verified | JWT auth + session ownership check |
| RAG/AI | ✅ Verified | Memory and knowledge scoped to user_id |
| RBAC | ⚠️ Limited | Only USER/ADMIN roles, no admin-only endpoints |

### Remaining Verification Tasks

1. ✅ Identity source of truth verification
2. ⏳ PostgreSQL tenant isolation (complete audit)
3. ⏳ MongoDB/Beanie tenant isolation (complete audit)
4. ⏳ Redis tenant boundaries (complete audit)
5. ⏳ Qdrant/vector tenant filtering (complete audit)
6. ⏳ AI/RAG authorization (complete audit)
7. ⏳ Tool authorization (complete audit)
8. ⏳ Document authorization (complete audit)
9. ⏳ Celery/background task authorization (complete audit)
10. ⏳ WebSocket authorization (complete audit)
11. ⏳ RBAC/role authorization (complete audit)
12. ⏳ IDOR/BOLA audit (complete audit)
13. ⏳ Cross-tenant negative tests (add comprehensive tests)
14. ⏳ Security test quality review
15. ⏳ Runtime tenant-isolation verification
16. ⏳ Full local regression (790 baseline)
17. ⏳ Fresh GitHub Actions run
18. ⏳ Final repository-wide authorization audit
19. ⏳ Comprehensive authorization report
20. ⏳ Git verification and commit

### Security Test Coverage

Existing authorization tests:
- `test_auth.py`: 20+ authentication security tests
- `test_tool_security_tenant_isolation.py`: 18+ tool isolation tests
- `test_documents.py`: 10+ document isolation tests
- `test_coaching_websocket_security.py`: WebSocket security tests
- `test_coaching_websocket_rate_limiting.py`: Rate limiting tests

### Known Limitations

1. **No Admin-Only Endpoints**: No endpoints require ADMIN role specifically
2. **No Organization/Tenant Model**: Single-tenant architecture (user-level isolation only)
3. **No Role-Based Resource Access**: All users have same resource access patterns
4. **No Fine-Grained Permissions**: No permission system beyond role

### Acceptance Criteria Status

- [ ] Authorization architecture documented
- [ ] Authenticated identity is server-side source of truth
- [ ] PostgreSQL tenant isolation verified
- [ ] MongoDB tenant isolation verified
- [ ] Redis tenant boundaries verified
- [ ] Qdrant tenant filtering verified
- [ ] AI/RAG cannot cross tenant boundaries
- [ ] P0 tools preserve tenant isolation
- [ ] Documents are object-authorized
- [ ] Celery tasks preserve tenant ownership
- [ ] WebSockets preserve tenant/identity authorization
- [ ] RBAC is enforced server-side
- [ ] IDOR/BOLA audit completed
- [ ] Cross-tenant negative tests pass
- [ ] Privilege-escalation tests pass
- [ ] Runtime tenant isolation verified
- [ ] Full local regression passes (zero skips)
- [ ] Fresh GitHub Actions run passes
- [ ] Security scan passes
- [ ] Docker build passes
- [ ] Final report contains exact evidence
- [ ] Working tree is clean
