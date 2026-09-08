# Qdrant Recovery Runbook

## Overview

This runbook covers Qdrant vector database recovery procedures for Lumenly. Qdrant stores vector embeddings derived from document content.

---

## Data Classification

### Qdrant Data Nature

**Classification:** DERIVED DATA

**Reasoning:**
- Vectors are embeddings of document text stored in MongoDB `user_documents.content`
- Vectors can be reconstructed from source documents
- Vectors are not primary data
- Vectors are computational artifacts

**Reconstruction Strategy:**
```
MongoDB user_documents (source content)
      ↓
Chunking logic
      ↓
Embedding generation (OpenAI/Gemini/etc.)
      ↓
Qdrant upsert
```

**Backup Required:** NO (reconstructible)

**Recovery Strategy:** Vector reconstruction from MongoDB source documents

---

## Symptoms

Qdrant may need recovery if:
- Qdrant service crashes
- Vector collection corrupted
- Search returns incorrect results
- Qdrant becomes unresponsive
- Disk full

---

## Detection

### Health Check Failure

```bash
curl http://localhost:8000/health/ready
```

**Expected:** `{"status":"healthy","checks":{"qdrant":"healthy",...}}`

**Failure:** `{"status":"unhealthy","checks":{"qdrant":"unhealthy",...}}`

### Application Errors

- Qdrant connection errors in logs
- Vector search failures
- "collection not found" errors
- Timeout errors

### Monitoring Alerts

- `QdrantUnavailable` (P0) - Qdrant completely unavailable
- `HighHTTPLatencyP95` (P1) - Possible Qdrant performance issue

---

## Recovery Procedures

### Procedure 1: Qdrant Restart (Standard Recovery)

**Use when:** Qdrant process crashed or unresponsive

**Steps:**

1. **Check Qdrant Status**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose ps qdrant
   ```

2. **View Qdrant Logs**
   ```bash
   docker compose logs qdrant
   ```

3. **Restart Qdrant**
   ```bash
   docker compose restart qdrant
   ```

4. **Verify Qdrant is Running**
   ```bash
   docker compose ps qdrant
   docker compose logs qdrant
   ```

5. **Test Qdrant Connectivity**
   ```bash
   # Test via application health check
   curl http://localhost:8000/health/ready
   ```

**Expected Result:** All checks show "healthy"

---

### Procedure 2: Vector Reconstruction (Full Recovery)

**Use when:** Qdrant data lost or corrupted, need to reconstruct vectors

**Prerequisites:**
- MongoDB `user_documents` collection intact
- Embedding provider API key available
- Application chunking logic available

**Steps:**

1. **Verify MongoDB Source Data**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   
   # Check user_documents exist
   db.user_documents.countDocuments()
   
   # Check documents with content
   db.user_documents.find({content: {$exists: true, $ne: ""}}).count()
   
   exit
   ```

2. **Clear Qdrant Collections** (Optional - if corrupted)
   ```bash
   # This requires Qdrant API access
   # Use Qdrant REST API or Python client
   ```

3. **Trigger Vector Reconstruction**
   ```bash
   # Option A: Via application API (if endpoint exists)
   curl -X POST http://localhost:8000/api/admin/reconstruct-vectors \
     -H "Authorization: Bearer <admin_token>"
   
   # Option B: Manual script (if available)
   cd /Users/mohsenrassam/Desktop/Lumenly/apps/backend
   python scripts/reconstruct_vectors.py
   ```

4. **Monitor Reconstruction Progress**
   ```bash
   # Monitor application logs
   docker compose logs -f backend
   
   # Monitor Celery worker logs (if async)
   docker compose logs -f celery-worker
   ```

5. **Verify Reconstruction**
   ```bash
   # Check vector counts match document chunk counts
   docker compose exec mongo mongosh
   use lumenly
   
   # Get total chunks from documents
   db.user_documents.aggregate([
     {$group: {_id: null, totalChunks: {$sum: "$chunk_count"}}}
   ])
   
   exit
   
   # Check Qdrant vector count (via application or Qdrant API)
   ```

6. **Test Vector Search**
   ```bash
   # Test search functionality
   curl -X POST http://localhost:8000/api/search \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"query":"test query"}'
   ```

**Expected Result:** Search returns relevant results

---

### Procedure 3: Partial Vector Reconstruction

**Use when:** Specific documents need vector reconstruction

**Steps:**

1. **Identify Documents Needing Reconstruction**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   
   # Find documents with empty vector_ids
   db.user_documents.find({
     status: "PROCESSED",
     vector_ids: {$size: 0}
   })
   
   # Find documents with status PROCESSED but no vectors
   db.user_documents.find({
     status: "PROCESSED",
     chunk_count: {$gt: 0},
     vector_ids: {$size: 0}
   })
   
   exit
   ```

2. **Trigger Partial Reconstruction**
   ```bash
   # Option A: Via application API (if endpoint exists)
   curl -X POST http://localhost:8000/api/admin/reconstruct-document \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"document_id":"<document_id>"}'
   
   # Option B: Manual script
   python scripts/reconstruct_document.py <document_id>
   ```

3. **Verify Reconstruction**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   
   db.user_documents.findOne({_id: ObjectId("<document_id>")})
   
   exit
   ```

**Expected Result:** `vector_ids` field populated

---

### Procedure 4: Qdrant Collection Recreation

**Use when:** Collection corrupted or deleted

**Steps:**

1. **Delete Corrupted Collection**
   ```bash
   # Via Qdrant REST API
   curl -X DELETE http://localhost:6333/collections/<collection_name>
   ```

2. **Recreate Collection**
   ```bash
   # Via application (application should auto-create on first use)
   # Or via Qdrant REST API
   curl -X PUT http://localhost:6333/collections/<collection_name> \
     -H "Content-Type: application/json" \
     -d '{
       "vectors": {
         "size": 1536,
         "distance": "Cosine"
       }
     }'
   ```

3. **Trigger Vector Reconstruction** (see Procedure 2)

---

## Verification

### Qdrant Level Verification

```bash
# Check Qdrant collections
curl http://localhost:6333/collections

# Check collection info
curl http://localhost:6333/collections/<collection_name>

# Check vector count
curl http://localhost:6333/collections/<collection_name>?with_vectors=true
```

### Application Level Verification

```bash
# Health check
curl http://localhost:8000/health/ready

# Test vector search
curl -X POST http://localhost:8000/api/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"test query"}'
```

### Data Consistency Verification

```bash
# Verify vector counts match document chunk counts
docker compose exec mongo mongosh
use lumenly

# Get total chunks from documents
db.user_documents.aggregate([
  {$group: {_id: null, totalChunks: {$sum: "$chunk_count"}}}
])

exit
```

---

## Rollback/Recovery

If recovery fails:

1. **Stop the recovery**
2. **Preserve current state** (don't delete data unnecessarily)
3. **Check Qdrant logs for errors**
4. **Check MongoDB source data integrity**
5. **Verify embedding provider API key**
6. **Escalate to senior engineering**

---

## Escalation

**Escalate if:**
- Qdrant repeatedly crashes
- Vector reconstruction fails
- Search returns incorrect results after reconstruction
- Reconstruction time exceeds 1 hour
- MongoDB source data corrupted

**Escalation Path:**
1. Senior Engineering
2. CTO

---

## Recovery Duration

**Expected Recovery Times:**

- Qdrant restart: 30 seconds - 2 minutes
- Vector reconstruction (small dataset): 5-15 minutes
- Vector reconstruction (medium dataset): 15-60 minutes
- Vector reconstruction (large dataset): 1-4 hours

**Target RTO:** 4 hours (current stage)
**Actual recovery time should be measured and documented**

---

## Post-Recovery Actions

1. **Document the recovery**
   - What failed
   - Why it failed
   - Recovery duration
   - Vectors reconstructed
   - Verification results

2. **Investigate root cause**
   - Review Qdrant logs
   - Check disk space
   - Check memory usage
   - Check for OOM kills

3. **Prevent recurrence**
   - Add monitoring
   - Add alerts
   - Adjust resource limits
   - Add persistence configuration

4. **Update documentation**
   - Update runbook with lessons learned
   - Update recovery procedures

---

## Monitoring During Recovery

### Metrics to Watch

- `database_health_status{database="qdrant"}` - Qdrant health
- `vector_search_duration_seconds` - Search latency
- `http_request_duration_seconds` - Application latency

### Logs to Monitor

```bash
# Qdrant logs
docker compose logs -f qdrant

# Backend logs
docker compose logs -f backend

# Celery worker logs (if async reconstruction)
docker compose logs -f celery-worker
```

---

## Backup Strategy

**Backup Required:** NO

**Reasoning:**
- Vectors are derived from MongoDB source documents
- Vectors can be reconstructed
- Snapshot backup would be redundant
- Reconstruction is safer (ensures vectors match current embedding model)

**Future Consideration:**
If reconstruction time becomes unacceptable:
- Implement Qdrant snapshots
- Implement snapshot retention policy
- Implement snapshot backup to external storage
- Balance reconstruction vs snapshot strategy

---

## Reconstruction Dependencies

**Required for Reconstruction:**
1. MongoDB `user_documents` collection intact
2. Document content (`content` field) present
3. Embedding provider API key available
4. Chunking logic available
5. Sufficient time for reconstruction

**Reconstruction Failure Modes:**
- MongoDB source data lost → Cannot reconstruct (data loss)
- Embedding provider unavailable → Cannot reconstruct (service unavailable)
- Chunking logic changed → Vectors may differ from original
- Embedding model changed → Vectors will differ from original

---

## References

- Qdrant client: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/db/qdrant.py`
- Data models: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/models/domain.py`
- Docker Compose: `/Users/mohsenrassam/Desktop/Lumenly/.docker/docker-compose.yml`

---

## Data Loss Impact

### Vectors Lost
- **Impact:** Vector search unavailable until reconstruction
- **Duration:** 5 minutes - 4 hours (depending on dataset size)
- **Severity:** MEDIUM
- **Recovery:** Reconstruct from MongoDB source documents

### Source Documents Lost (MongoDB)
- **Impact:** Vectors cannot be reconstructed (permanent data loss)
- **Duration:** Permanent
- **Severity:** CRITICAL
- **Recovery:** Restore MongoDB from backup

---

## Reconstruction vs Snapshot Trade-offs

### Reconstruction (Current Strategy)
**Advantages:**
- No additional storage required
- Vectors always match current embedding model
- Simpler architecture
- No snapshot management overhead

**Disadvantages:**
- Reconstruction time required
- Dependent on MongoDB source data
- Dependent on embedding provider availability

### Snapshot (Future Consideration)
**Advantages:**
- Instant restore
- No reconstruction time
- Independent of embedding provider

**Disadvantages:**
- Additional storage required
- Snapshot management overhead
- Vectors may not match current embedding model
- Additional complexity

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
