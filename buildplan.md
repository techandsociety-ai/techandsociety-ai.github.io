# Technical Design Document: CHIP50 Survey Data MCP Server

## Executive Summary

The CHIP50 MCP (Model Context Protocol) server provides secure, privacy-preserving access to survey data for researchers and journalists studying public opinion among average Americans. The system implements a tiered access model with automatic privacy protections while maintaining ease of use for non-technical users.

**Target Users:** Journalists, researchers (academic and independent)
**Privacy Model:** Cell size suppression (n≥10), automatic filtering of identifiable data
**Access Tiers:** Core researchers (raw data access) vs. Outside researchers (aggregated data only)
**Deployment:** Local MCP proxy → Remote authenticated server
**Installation:** One-click install via FastMCP

---

## System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│ User Environment (Claude Desktop, IDEs)                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Local MCP Proxy Server (FastMCP)                   │    │
│  │ - Handles stdio communication with Claude          │    │
│  │ - Manages API key storage (local config)           │    │
│  │ - Forwards requests to remote server               │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼─────────────────────────────────────────┘
                    │ HTTPS + API Key Auth
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ Remote Server (Cloud Run / App Engine)                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Authentication & Authorization Layer               │    │
│  │ - Validates API keys                               │    │
│  │ - Determines access tier (core vs. outside)        │    │
│  │ - Audit logging                                     │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Query Processing & Privacy Enforcement             │    │
│  │ - Cell size suppression (n≥10)                     │    │
│  │ - Tier-based query routing                         │    │
│  │ - Validates queries against privacy rules          │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼─────────────────────────────────────────┘
                    │ Service Account Auth
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ Google BigQuery (Separate Project: chip50-public)          │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │ Raw Data (Core Researchers Only)         │              │
│  │ - chip50_raw.demographics                │              │
│  │ - chip50_raw.survey_responses            │              │
│  │   Contains: user_id, precise_geo,        │              │
│  │   exact_timestamps, free_text            │              │
│  └──────────────────────────────────────────┘              │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │ Protected Views (Outside Researchers)    │              │
│  │ - chip50_public.demographics_protected   │              │
│  │ - chip50_public.survey_responses_agg     │              │
│  │   Excludes: user_id, free_text           │              │
│  │   Aggregates: zip→region, timestamp→week │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase-by-Phase Implementation Plan

### Phase 1: Core Database Creation ✅ (COMPLETE)

**Status:** Raw data tables created in BigQuery
- `demographics` table with 11 variables (age, education, income, party, race, etc.)
- `survey_responses` table with substantive questions
- Data structure supports wave-based analysis with survey weights

---

### Phase 2: Database Security & Privacy Layer

#### 2.1 BigQuery Project Isolation

**Action:** Create separate BigQuery project for public data access

```
Current: chip50-dev (contains raw data)
New:     chip50-public (will contain protected views only)
```

**Rationale:**
- IAM separation: Core researchers access `chip50-dev`, outside researchers only see `chip50-public`
- Billing isolation: Track costs for public queries separately
- Security boundary: No accidental raw data exposure

**Implementation:**
1. Create new GCP project: `chip50-public`
2. Enable BigQuery API
3. Configure cross-project authorized views from `chip50-dev` → `chip50-public`

#### 2.2 Protected View Creation

**Create two protected views in `chip50-public` dataset:**

**View 1: `demographics_protected`**
```sql
CREATE OR REPLACE VIEW `chip50-public.survey_data.demographics_protected` AS
SELECT
  -- Remove user_id entirely (PII)
  wave,

  -- Geographic aggregation (zip → region)
  CASE
    WHEN state IN ('ME', 'NH', 'VT', 'MA', 'RI', 'CT') THEN 'Northeast'
    WHEN state IN ('NY', 'NJ', 'PA') THEN 'Mid-Atlantic'
    WHEN state IN ('OH', 'IN', 'IL', 'MI', 'WI') THEN 'Midwest'
    -- ... (continue for all regions)
  END AS region,

  -- Keep safe demographics
  age_group,
  education_cat,
  income_cat,
  party_7,
  race,
  gender,
  urban_rural,
  weight,

  -- Create row hash for JOIN (replaces user_id)
  FARM_FINGERPRINT(CONCAT(CAST(id AS STRING), CAST(wave AS STRING))) AS row_hash

FROM `chip50-dev.survey_raw.demographics`
```

**View 2: `survey_responses_protected`**
```sql
CREATE OR REPLACE VIEW `chip50-public.survey_data.survey_responses_protected` AS
SELECT
  -- Matching row_hash for JOIN
  FARM_FINGERPRINT(CONCAT(CAST(id AS STRING), CAST(wave AS STRING))) AS row_hash,
  wave,

  -- All substantive survey variables (NO free text)
  trust_congress,
  trust_media,
  trust_courts,
  approval_pres,
  approval_congress,
  economy_rating,
  vote_intention,
  -- ... (all coded/categorical responses)

  -- Exclude: Any free-text comment fields

FROM `chip50-dev.survey_raw.survey_responses`
WHERE id IS NOT NULL  -- Data quality filter
```

**Key Privacy Features:**
- ✅ No `user_id` or `id` columns exposed
- ✅ Geographic precision reduced (state → region)
- ✅ Timestamps aggregated (if present: exact_time → week_of_year)
- ✅ Free-text responses excluded entirely
- ✅ Uses `FARM_FINGERPRINT` for deterministic JOIN key (non-reversible)

#### 2.3 Authorized Views Configuration

**Setup cross-project access:**
1. In `chip50-dev` project: Grant `chip50-public` service account `BigQuery Data Viewer` role on raw tables
2. Create authorized view relationship
3. Test that direct queries to `chip50-dev` fail from outside researcher accounts

---

### Phase 3: Tiered Access & Authentication

#### 3.1 Access Tier Definitions

| Tier | Users | Data Access | Use Case |
|------|-------|-------------|----------|
| **Core Researcher** | Internal team, PIs | Raw tables in `chip50-dev` | Deep analysis, method development, quality control |
| **Outside Researcher** | Journalists, academics, verified users | Protected views in `chip50-public` | Public-facing reports, standard crosstabs |

#### 3.2 API Key Management System

**User Application Flow (Auto-Approved):**
1. Researcher visits `chip50.org/register` (simple web form)
2. Submits: Name, email, organization, intended use
3. System **automatically approves** and generates API key
4. User receives instant email with:
   - API key: `chip50_outside_[random32]` (e.g., `chip50_outside_a3f9d2e1...`)
   - Installation instructions
   - Link to documentation
5. API key metadata stored in Firestore

**Note:** Core researcher keys are manually issued by admins (separate process)

**API Key Storage (Firestore):**
```python
# Firestore document schema
{
  "api_key": "chip50_outside_xyz123...",
  "user_email": "researcher@university.edu",
  "tier": "outside",  # or "core" (core keys manually issued)
  "organization": "State University",
  "created_at": "2025-01-15T10:00:00Z",
  "expires_at": "2026-01-15T10:00:00Z",  # 1 year expiry
  "is_active": true,
  "daily_query_count": 0,  # Resets at midnight UTC
  "daily_quota": 100,  # 100 queries per day
  "total_queries": 0,
  "last_used": null,
  "last_quota_reset": "2025-01-15T00:00:00Z"
}
```

#### 3.3 Authentication Middleware (Remote Server)

**FastAPI middleware with rate limiting:**
```python
def authenticate_request(api_key: str) -> dict:
    """
    Validates API key, enforces rate limits, and returns user context.
    Returns: {"tier": "core"|"outside", "user_id": "...", "is_valid": bool}
    Raises: HTTPException(429) if quota exceeded
    """
    # 1. Look up API key in Firestore
    user_doc = firestore_client.collection('api_keys').document(api_key).get()

    if not user_doc.exists:
        raise HTTPException(401, "Invalid API key")

    user = user_doc.to_dict()

    # 2. Check is_active and expiration
    if not user['is_active'] or datetime.now() > user['expires_at']:
        raise HTTPException(401, "API key expired or deactivated")

    # 3. Check and reset daily quota (midnight UTC)
    now = datetime.utcnow()
    last_reset = user['last_quota_reset']
    if now.date() > last_reset.date():
        # New day - reset counter
        user['daily_query_count'] = 0
        user['last_quota_reset'] = now

    # 4. Enforce rate limit (100 queries/day)
    if user['daily_query_count'] >= user['daily_quota']:
        raise HTTPException(429, f"Daily quota exceeded ({user['daily_quota']} queries/day). Resets at midnight UTC.")

    # 5. Increment counters
    user['daily_query_count'] += 1
    user['total_queries'] += 1
    user['last_used'] = now

    # 6. Update Firestore
    firestore_client.collection('api_keys').document(api_key).update(user)

    return {"tier": user["tier"], "user_id": user["user_email"], "is_valid": True}
```

#### 3.4 Audit Logging

**Log every query execution:**
```python
audit_log = {
    "timestamp": datetime.utcnow(),
    "user_id": user_context["user_id"],
    "tier": user_context["tier"],
    "query_type": "crosstab",
    "parameters": {
        "survey_variable": "trust_congress",
        "demographic_variable": "party_7"
    },
    "cell_suppression_applied": true,
    "cells_suppressed": 3,
    "result_row_count": 24,
    "execution_time_ms": 450,
    "bigquery_bytes_processed": 1024000
}
```

**Storage:** BigQuery audit table or Cloud Logging for compliance review

---

### Phase 4: MCP Server Implementation

#### 4.1 Architecture: Local Proxy + Remote Server

**Why this architecture?**
- ✅ Non-technical users: Install via single command (`npx chip50-mcp` or `pip install chip50-mcp`)
- ✅ Secure credentials: API key stored locally, never in Claude Desktop config
- ✅ Centralized logic: Privacy enforcement, cell suppression on remote server
- ✅ Easy updates: Server-side updates without user reinstalls

#### 4.2 Local MCP Proxy (FastMCP)

**Installation Method (GitHub Releases):**
```bash
# Platform-specific install scripts

# macOS/Linux:
curl -fsSL https://github.com/chip50/chip50-mcp/releases/latest/download/install.sh | bash

# Windows (PowerShell):
irm https://github.com/chip50/chip50-mcp/releases/latest/download/install.ps1 | iex

# What the install script does:
# 1. Detects OS and Python version
# 2. Downloads platform-specific release package
# 3. Extracts to ~/.chip50/mcp-server/
# 4. Runs configuration wizard:
#    - Prompts for API key (from chip50.org/register)
#    - Validates key against remote server
#    - Saves to ~/.chip50/config.json
# 5. Adds MCP server to Claude Desktop config automatically
# 6. Tests connection

# Manual installation (alternative):
git clone https://github.com/chip50/chip50-mcp.git
cd chip50-mcp
./install.sh  # or install.ps1 on Windows
```

**Local Proxy Responsibilities:**
1. **MCP Protocol Handling:** stdio communication with Claude Desktop
2. **Credential Management:** Read API key from local config
3. **Request Forwarding:** HTTPS POST to remote server with auth header
4. **Error Handling:** User-friendly error messages (invalid key, quota exceeded, etc.)

**File:** `local_proxy/server.py` (FastMCP implementation)
```python
from fastmcp import FastMCP

mcp = FastMCP("CHIP50 Survey Analysis")

@mcp.tool()
def generate_crosstab(
    survey_variable: str,
    demographic_variable: str,
    waves: list[int] | None = None,
    filter_conditions: str | None = None
) -> dict:
    """Generate weighted crosstab from CHIP50 survey data."""

    # Read API key from local config
    api_key = load_api_key()  # from ~/.chip50/config.json

    # Forward to remote server
    response = requests.post(
        "https://chip50-api.example.com/v1/crosstab",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "survey_variable": survey_variable,
            "demographic_variable": demographic_variable,
            "waves": waves,
            "filter_conditions": filter_conditions
        }
    )

    # Handle errors
    if response.status_code == 401:
        raise Exception("Invalid API key. Run: chip50-mcp configure")
    elif response.status_code == 403:
        raise Exception("Access denied. Your tier does not permit this query.")
    elif response.status_code == 429:
        raise Exception("Query quota exceeded. Try again later.")

    return response.json()
```

#### 4.3 Remote Server (Cloud Run / App Engine)

**Hosting Options:**
- **Recommended:** Google Cloud Run (auto-scaling, pay-per-use, HTTPS included)
- Alternative: App Engine Standard (simpler, good for steady traffic)

**Server Framework:** FastAPI (Python)

**Key Components:**

**1. Authentication Endpoint:**
```python
@app.post("/v1/validate-key")
def validate_api_key(api_key: str):
    """Validates API key during local proxy setup."""
    user = authenticate_request(api_key)
    if user["is_valid"]:
        return {"valid": true, "tier": user["tier"], "expires_at": user["expires_at"]}
    else:
        return {"valid": false, "error": "Invalid or expired key"}
```

**2. Crosstab Endpoint with Privacy Enforcement:**
```python
@app.post("/v1/crosstab")
def generate_crosstab(
    request: CrosstabRequest,
    user: dict = Depends(authenticate_request)
):
    """
    Generate crosstab with automatic cell suppression.
    Enforces tier-based access to raw vs. protected views.
    """

    # 1. Route query based on user tier
    if user["tier"] == "core":
        dataset = "chip50-dev.survey_raw"
        tables = {"demographics": "demographics", "survey": "survey_responses"}
    else:  # outside
        dataset = "chip50-public.survey_data"
        tables = {"demographics": "demographics_protected", "survey": "survey_responses_protected"}

    # 2. Build BigQuery SQL (similar to current implementation)
    sql = build_crosstab_query(
        dataset=dataset,
        tables=tables,
        survey_var=request.survey_variable,
        demographic_var=request.demographic_variable,
        waves=request.waves,
        filters=request.filter_conditions
    )

    # 3. Execute query
    client = bigquery.Client(project="chip50-public")
    results = client.query(sql).to_dataframe()

    # 4. Apply cell size suppression (CRITICAL PRIVACY STEP)
    suppressed_results, suppressed_count = suppress_small_cells(
        results,
        min_cell_size=10
    )

    # 5. Audit log
    log_query(user, request, suppressed_count, results.shape[0])

    # 6. Return formatted results
    return {
        "data": suppressed_results.to_dict(orient="records"),
        "metadata": {
            "total_cells": len(results),
            "suppressed_cells": suppressed_count,
            "note": "Cells with n<10 suppressed for privacy"
        }
    }
```

**3. Cell Suppression Logic:**
```python
def suppress_small_cells(df: pd.DataFrame, min_cell_size: int = 10) -> tuple:
    """
    Suppress crosstab cells with counts below threshold.

    Returns: (suppressed_dataframe, count_of_suppressed_cells)
    """
    suppressed_count = 0

    # Identify count columns (weighted_count, percentage, etc.)
    for col in df.columns:
        if 'count' in col.lower() or 'n_' in col.lower():
            # Mask cells below threshold
            mask = df[col] < min_cell_size
            df.loc[mask, col] = None  # or "[suppressed]"
            suppressed_count += mask.sum()

            # Also suppress corresponding percentages
            if 'count' in col:
                pct_col = col.replace('count', 'percentage')
                if pct_col in df.columns:
                    df.loc[mask, pct_col] = None

    return df, suppressed_count
```

#### 4.4 Deployment Configuration

**Cloud Run Deployment:**
```yaml
# cloud-run.yaml
service: chip50-mcp-server
runtime: python311
env: standard

env_variables:
  BIGQUERY_PROJECT_RAW: chip50-dev
  BIGQUERY_PROJECT_PUBLIC: chip50-public
  API_KEY_DB: firestore  # or cloud-sql
  MIN_CELL_SIZE: "10"

resources:
  memory: 512Mi
  cpu: 1

scaling:
  min_instances: 0
  max_instances: 10
```

**Service Account Permissions:**
```
Remote server service account needs:
- BigQuery Data Viewer on chip50-dev.survey_raw (for core researchers)
- BigQuery Data Viewer on chip50-public.survey_data (for all users)
- BigQuery Job User (to run queries)
- Cloud Datastore User (to validate API keys)
```

#### 4.5 Updated Tool Specifications

**Remove:** `upload_csv_to_bigquery` (not in scope for user-facing MCP)

**Keep (Enhanced):** `generate_crosstab`

**New Tool Parameters:**
```python
@mcp.tool()
def generate_crosstab(
    survey_variable: str,  # e.g., "trust_congress"
    demographic_variable: str,  # e.g., "party_7", "region" (not "state" for outside researchers)
    waves: list[int] | None = None,  # e.g., [7, 8, 9]
    include_suppressed_count: bool = False  # Show how many cells were suppressed
) -> dict:
    """
    Generate weighted crosstab from CHIP50 survey data.

    Privacy protections:
    - Cells with n<10 automatically suppressed
    - Outside researchers see regional (not state-level) geography
    - No access to free-text or user IDs

    Returns:
    {
      "crosstab": [...],  # List of {demographic_value, count, percentage, ...}
      "metadata": {
        "total_n": 1450,
        "suppressed_cells": 3,
        "waves_included": [7, 8, 9],
        "note": "Cells suppressed for privacy"
      }
    }
    """
```

**Potential Additional Tool:**
```python
@mcp.tool()
def get_available_variables() -> dict:
    """
    List available survey and demographic variables for your access tier.

    Returns different variable lists based on core vs. outside researcher tier.
    """
```

---

## Critical Files & Modifications

### Files to Modify

1. **[mcp_server/server.py](mcp_server/server.py)**
   - Remove `upload_csv_to_bigquery` tool (lines 46-100)
   - Replace direct BigQuery calls with remote server API calls
   - Add local config file reading for API key
   - Simplify to pure proxy logic

2. **[requirements.txt](requirements.txt)**
   - Remove: `google-cloud-bigquery`, `db-dtypes` (not needed in local proxy)
   - Add: `requests`, `fastmcp`, `pydantic`

3. **[manifest.json](manifest.json)**
   - Update server name and description
   - Update command to use `chip50-mcp` CLI wrapper

### New Files to Create

4. **`remote_server/main.py`** (NEW)
   - FastAPI server implementation
   - Authentication middleware with 100/day rate limiting
   - Privacy enforcement logic
   - BigQuery query execution with cell suppression

5. **`remote_server/privacy.py`** (NEW)
   - `suppress_small_cells()` function (n≥10 threshold)
   - `build_protected_query()` for tier-based routing
   - Cell suppression audit logging

6. **`remote_server/auth.py`** (NEW)
   - API key validation with Firestore
   - Tier determination (core vs. outside)
   - Daily quota enforcement (100 queries/day)
   - Auto-reset at midnight UTC

7. **`remote_server/registration.py`** (NEW)
   - Auto-approval API key generation endpoint
   - Email notification on registration
   - Firestore document creation

8. **`local_proxy/config.py`** (NEW)
   - Read/write `~/.chip50/config.json`
   - API key validation on setup
   - User-friendly configuration CLI

9. **`install.sh`** (NEW - macOS/Linux)
   - Platform detection
   - Python version check (≥3.8)
   - Download latest release
   - Extract to ~/.chip50/
   - Run configuration wizard
   - Add to Claude Desktop config
   - Test connection

10. **`install.ps1`** (NEW - Windows)
    - Windows equivalent of install.sh
    - PowerShell-based installation
    - Same functionality as bash script

11. **`sql/create_protected_views.sql`** (NEW)
    - SQL statements to create `demographics_protected` and `survey_responses_protected`
    - Documentation of privacy transformations

12. **`docs/INSTALLATION.md`** (UPDATE)
    - Quick start guide with curl command
    - API key registration instructions
    - Platform-specific troubleshooting

13. **`website/registration_form.html`** (NEW)
    - Simple form at chip50.org/register
    - Fields: name, email, organization, intended use
    - Auto-generates API key on submit
    - Email with installation instructions

---

## Testing & Validation Plan

### Security Tests (Phase 2 Validation)

**Test 1: Raw Data Isolation**
```sql
-- Using outside researcher credentials, attempt to query raw data
-- EXPECTED: Permission denied error
SELECT * FROM `chip50-dev.survey_raw.demographics` LIMIT 1;
```

**Test 2: User ID Leakage**
```sql
-- Verify user_id not accessible through protected views
SELECT * FROM `chip50-public.survey_data.demographics_protected`
WHERE row_hash = 'FARM_FINGERPRINT(...)';
-- EXPECTED: No user_id column exists
```

**Test 3: Geographic Precision**
```sql
-- Verify state-level data aggregated to region
SELECT DISTINCT region FROM `chip50-public.survey_data.demographics_protected`;
-- EXPECTED: Only regions returned (Northeast, South, etc.), not state codes
```

### Privacy Tests (Phase 3 Validation)

**Test 4: Cell Suppression**
```python
# Generate crosstab with rare demographic combination
result = generate_crosstab(
    survey_variable="trust_congress",
    demographic_variable="race",
    waves=[7]  # Single wave to reduce sample size
)

# EXPECTED: Some cells showing None or "[suppressed]" with note about n<10
assert result["metadata"]["suppressed_cells"] > 0
```

**Test 5: Attempt Row-Level Extraction**
```python
# Try to extract individual responses by iterating all combinations
# EXPECTED: Should be impossible due to aggregation enforcement
```

**Test 6: API Key Tier Enforcement**
```python
# Using outside researcher API key
# Attempt to query variable only available to core researchers
# EXPECTED: 403 Forbidden error
```

### Functional Tests (Phase 4 Validation)

**Test 7: One-Click Installation**
```bash
# Fresh machine test
pip install chip50-mcp
chip50-mcp configure
# Enter API key when prompted
# EXPECTED: Successfully adds to Claude Desktop, can run queries immediately
```

**Test 8: Crosstab Accuracy**
```python
# Compare results between core and outside researcher tiers
# Same query should return same counts/percentages (minus suppressed cells)
# EXPECTED: Statistical consistency, only difference is suppression
```

**Test 9: Error Handling**
```python
# Invalid API key
# EXPECTED: Clear error message with instructions to run configure command

# Expired API key
# EXPECTED: Error with contact information to renew access

# Invalid variable name
# EXPECTED: Helpful error listing available variables
```

---

## Implementation Timeline & Priorities

### Phase 2: Database Security ✅ (COMPLETE)
**Goal:** Secure raw data and create privacy-preserving views

**Status:** COMPLETE
- ✅ Created protected BigQuery views in `chip50.public.*`
- ✅ Implemented privacy protections (user_id removal, state→region aggregation)
- ✅ Validated with comprehensive test suite
- ✅ Full analytical capability preserved with row_hash JOIN

**Deliverable:** Protected BigQuery views that prevent PII exposure

---

### Phase 3: MCPB Bundle Package ✅ (COMPLETE - In Testing)
**Goal:** Installable MCP bundle with privacy-safe BigQuery access

**Status:** CODE COMPLETE - Ready for stakeholder testing

**Approach:** MCPB bundle installed via Claude Desktop UI
- ✅ Direct BigQuery access to protected views
- ✅ Cell suppression (n≥10) built-in
- ✅ Simple API key via Claude Desktop settings UI
- ✅ No remote server needed
- ✅ One-click install in Claude Desktop

**Deliverable:** `chip50-survey-mcp.mcpb` bundle

**Advantages of MCPB Approach:**
- ✅ **Easy Installation:** Users install via Claude Desktop UI (drag-and-drop or file picker)
- ✅ **Nice Settings UI:** Claude Desktop provides built-in UI for API key configuration
- ✅ **No Command Line:** Non-technical users can install without terminal
- ✅ **Auto-Updates:** Bundles can be updated and redistributed easily
- ✅ **Local Execution:** All privacy logic runs locally (no remote server)
- ✅ **Direct BigQuery:** Queries protected views directly with user's GCP credentials

---

### Phase 4: MCPB Distribution & Documentation (Priority: HIGH - NEXT)
**Goal:** Publish bundle and create user-friendly documentation

**Tasks:**
1. ✅ Create `.mcpb` bundle configuration
2. ✅ Test bundle installation in Claude Desktop
3. Create installation video/screenshots
4. Write non-technical installation guide
5. Publish bundle to GitHub releases
6. Create chip50.org landing page with download link
7. Document GCP setup for end users

**Deliverable:** Publicly available MCPB bundle with docs

---

### Phase 5: Optional Firestore Auth (Priority: LOW - FUTURE)
**Goal:** Add centralized API key management if needed

**Trigger:** If we need to track/limit usage or add tiered access

**Decision Point:** Do we need this?
- **Current:** Users bring their own GCP credentials (free, unlimited)
- **Future:** Centralized API keys with quotas (adds complexity)

**Tasks (If Needed):**
1. Set up Firestore database for API keys
2. Build registration web form (chip50.org/register)
3. Add auth layer between MCP server and BigQuery
4. Implement rate limiting (100/day)
5. Set up audit logging

**Deliverable:** Central API key system (optional)

**Note:** This may NOT be needed! Current approach lets users use their own GCP credentials, which:
- ✅ No quota management needed (users pay their own BigQuery costs)
- ✅ No registration system to build/maintain
- ✅ Simpler architecture
- ✅ Users control their own access

We can decide later if centralized auth is worth the complexity.

---

### Phase 7: Documentation (Priority: LOW - ONGOING)
**Goal:** User-friendly docs for journalists/researchers

**Tasks:**
1. Create QUICKSTART.md with example queries
2. Document available variables and their meanings
3. Create troubleshooting guide
4. Add usage examples for common research questions

**Deliverable:** Complete documentation suite

---

## Open Questions & Future Enhancements

### Design Decisions (FINALIZED)

**Architecture: MCPB Bundle (Current)**
- ✅ **Distribution:** MCPB bundle installable via Claude Desktop UI
- ✅ **Authentication:** User's own GCP credentials (via `gcloud auth`)
- ✅ **API Key UI:** Claude Desktop settings panel (built-in)
- ✅ **Cell suppression:** Local (in MCP server Python code, n≥10)
- ✅ **Privacy:** Protected BigQuery views (`chip50.public.*`)
- ✅ **Installation:** Drag-and-drop or file picker in Claude Desktop
- ✅ **Updates:** Redistribute new `.mcpb` file

**Key Simplifications:**
- ❌ **No remote server** - Direct BigQuery access
- ❌ **No Firestore** - Users manage own GCP credentials
- ❌ **No registration** - Download bundle from chip50.org
- ❌ **No rate limiting** - Users pay own BigQuery costs (minimal)
- ❌ **No quota management** - Self-service via GCP

**Why MCPB Approach Wins:**
1. **Easier for users** - No command line, just install in Claude Desktop
2. **Better UX** - Claude Desktop provides nice settings UI
3. **Simpler architecture** - No remote server to maintain
4. **Cost effective** - Users pay their own (tiny) BigQuery costs
5. **Privacy preserving** - All data stays in user's GCP project
6. **Scalable** - No server capacity to manage

**Optional Future (If Needed):**
- 🔄 Centralized API keys (Firestore) - Only if we need usage tracking/limits
- 🔄 Remote server (Cloud Run) - Only if direct BigQuery becomes problematic
- 🔄 Registration website - Only if we need centralized auth

### Future Enhancements (Post-Launch)
- **Export formats:** CSV/Excel download in addition to JSON
- **Visualization tool:** Auto-generate charts from crosstabs
- **Time series analysis:** Track opinion change across waves
- **Custom reports:** Template-based report generation
- **Public dashboard:** Web interface for common queries (no API key needed)
- **Advanced privacy:** Differential privacy noise injection for highly sensitive queries

---

## Appendix: Example User Workflows

### Workflow 1: Outside Researcher (Journalist)

1. **Register for instant access:**
   - Visit `https://chip50.org/register`
   - Submit form:
     - Name: "Jane Smith"
     - Email: "jsmith@newsorg.com"
     - Organization: "State Times"
     - Intended use: "Covering 2024 election trends"
   - **Instantly receive** API key via email: `chip50_outside_a3f9d2e1b4c5...`

2. **One-command installation:**
   ```bash
   # macOS/Linux
   curl -fsSL https://github.com/chip50/chip50-mcp/releases/latest/download/install.sh | bash

   # Script prompts for API key, validates it, and configures everything
   # No manual pip install or config editing needed!
   ```

3. **Use in Claude Desktop:**
   ```
   User: "Using CHIP50 data, show me trust in Congress by party affiliation"

   Claude: [Calls generate_crosstab(survey_variable="trust_congress", demographic_variable="party_7")]

   Returns:
   | Party ID        | Trust (%) | Distrust (%) | N     |
   |-----------------|-----------|--------------|-------|
   | Strong Democrat | 45%       | 35%          | 210   |
   | Democrat        | 38%       | 42%          | 185   |
   | Lean Democrat   | 32%       | 48%          | [suppressed] |  # n<10
   | Independent     | 18%       | 62%          | 320   |
   | ...             |           |              |       |

   Note: 2 cells suppressed due to small sample size (n<10)
   Queries remaining today: 99/100
   ```

4. **If quota exceeded:**
   ```
   User: "Show me another crosstab..."

   Error: Daily quota exceeded (100 queries/day). Resets at midnight UTC.
   Current time: 2025-01-15 23:45 UTC
   Quota resets in: 15 minutes
   ```

### Workflow 2: Core Researcher (Academic PI)

1. **Access approved by admin** (manual verification)
2. **Receive core tier API key** with access to raw data
3. **Can query exact geographic data:**
   ```python
   generate_crosstab(
       survey_variable="approval_pres",
       demographic_variable="state"  # State-level allowed for core tier
   )
   ```
4. **Can access user_id for longitudinal panel analysis** (via direct BigQuery access to `chip50-dev` project)

---

## Quick Implementation Summary

### Architecture at a Glance
```
Users → curl install.sh → Local MCP Proxy → Remote FastAPI Server → BigQuery (Protected Views)
        ↓                   (API key)         (Rate limit: 100/day)    (Cell suppress: n≥10)
    Instant API key                           Privacy enforcement       No PII exposure
    (auto-approved)
```

### Key Design Decisions (Finalized)
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **API Key Approval** | Auto-approve | Instant access for journalists/researchers |
| **Rate Limiting** | 100 queries/day | Balances access with BigQuery cost control |
| **Tier Conversion** | No upgrade path | Core vs. outside are separate pools (security) |
| **Installation** | GitHub + curl script | Works for non-technical users, no package registry needed |
| **Cell Suppression** | n≥10 threshold | Industry standard for k-anonymity |
| **API Key Storage** | Firestore | Simple, auto-scaling, built-in to GCP |
| **Geography** | State → Region | Prevents re-identification via rare locations |

### What Gets Built

**Phase 2:** Protected BigQuery views (remove PII, aggregate geography)
**Phase 3:** Auto-approval registration system with Firestore + rate limiting
**Phase 4A:** Remote FastAPI server on Cloud Run with cell suppression
**Phase 4B:** One-command install script for local MCP proxy
**Phase 4C:** User documentation and troubleshooting guides

### User Experience Flow
1. Visit `chip50.org/register` → Get instant API key
2. Run: `curl -fsSL https://github.com/chip50/chip50-mcp/releases/latest/download/install.sh | bash`
3. Paste API key when prompted
4. Start using in Claude Desktop immediately
5. Get 100 queries/day with automatic privacy protections

---

## Summary

This design provides:
- ✅ **Privacy-first:** Automatic cell suppression (n≥10), no PII exposure, region-level geography only
- ✅ **Tiered access:** Core researchers (raw data) vs. outside researchers (protected views) - no conversion
- ✅ **Low-friction UX:** One-command install, instant auto-approved API keys
- ✅ **Cost control:** 100 queries/day rate limit with midnight UTC reset
- ✅ **Scalable architecture:** Cloud Run auto-scaling, Firestore for API keys, centralized privacy enforcement
- ✅ **Audit-ready:** Complete query logging to BigQuery for compliance
- ✅ **Maintainable:** Server-side updates without user reinstalls, GitHub-based distribution

**Ready to build!** Start with Phase 2 (database security) to create protected views.
