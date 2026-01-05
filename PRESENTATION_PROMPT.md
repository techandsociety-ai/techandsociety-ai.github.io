# Prompt for Claude Desktop: CHIP50 MCP Presentation

Please create a professional presentation (slide deck format) describing the CHIP50 Survey MCP Server project. The presentation should be comprehensive yet accessible to both technical and non-technical audiences.

## Overview
The CHIP50 Survey MCP (Model Context Protocol) Server is a privacy-preserving data analysis tool that provides AI assistants (like Claude) with secure access to CHIP50 survey data stored in Google BigQuery. It enables weighted cross-tabulations and statistical analysis while maintaining strict privacy protections.

---

## Section 1: Project Introduction (3-4 slides)

### Slide 1: What is CHIP50 MCP?
- A Model Context Protocol server that connects Claude Desktop to CHIP50 survey data
- Enables AI-assisted analysis of survey responses across demographic categories
- Built-in privacy protections and security measures
- Uses Google BigQuery for scalable cloud-based data storage and processing

### Slide 2: Key Features
- **BigQuery Integration**: Upload and query survey data in the cloud
- **Weighted Cross-tabulation**: Generate statistical analysis with survey weights
- **Wave-Based Architecture**: Each survey wave has separate tables for flexibility
- **Privacy-First Design**: Cell suppression, PII removal, geographic aggregation
- **Synthetic Data**: Safe testing environment with realistic fake data

### Slide 3: Use Cases
- Researchers analyzing public opinion trends across demographics
- Policy analysts examining survey responses by region and party affiliation
- Data scientists exploring correlations between demographics and attitudes
- Students and educators learning survey analysis methods

---

## Section 2: Data Security & Storage (4-5 slides)

### Slide 4: Multi-Layer Privacy Architecture

**Layer 1: Raw Data Storage (chip50.raw schema)**
- Contains original survey data with PII
- Access restricted to authorized data administrators only
- Never directly exposed through MCP tools
- Example tables: `demographics_w35`, `survey_responses_w35`

**Layer 2: Protected Views (chip50.public schema)**
- SQL views that transform raw data with privacy protections
- Accessible to external researchers through MCP
- Cell suppression enforced (minimum n≥10)
- Example views: `demographics_protected_w35`, `survey_responses_protected_w35`

### Slide 5: Privacy Protections in Detail

**1. PII Removal**
- User IDs removed completely from protected views
- Replaced with non-reversible `row_hash` for joining tables
- Uses FARM_FINGERPRINT for deterministic hashing

**2. Geographic Aggregation**
- State-level data aggregated to 5 US regions (Northeast, Mid-Atlantic, Midwest, South, West)
- Exact location data (zip, county, FIPS) removed
- Reduces geographic precision to protect privacy

**3. Cell Suppression**
- Any result with fewer than 10 responses is suppressed
- Shows `[suppressed]` instead of actual values
- Prevents identification of individuals in small groups

**4. API Key Authentication**
- Environment variable validation on startup
- Test key for synthetic data: `chip50_test_synthetic_data_only`
- Ensures only authorized users access the data

### Slide 6: Wave-Based Data Architecture

**Why Separate Tables Per Wave?**
- Each survey wave can have different questions/variables
- No NULL columns for questions not asked in certain waves
- Faster queries when analyzing single waves
- Easy to add new waves without modifying existing data
- Clear version control and data lineage

**Table Naming Convention:**
```
Wave 35:   demographics_w35, survey_responses_w35
Wave 35.1: demographics_w35_1, survey_responses_w35_1
Wave 36:   demographics_w36, survey_responses_w36
```

### Slide 7: Data Storage in Google BigQuery

**Why BigQuery?**
- Serverless, scalable cloud data warehouse
- SQL-based querying for familiar syntax
- Handles large datasets efficiently
- Built-in security and access controls
- Cost-effective for analytical workloads

**Dataset Structure:**
```
chip50 (project)
├── raw (dataset) - Restricted access
│   ├── demographics_w35
│   └── survey_responses_w35
└── public (dataset) - MCP access
    ├── demographics_protected_w35
    └── survey_responses_protected_w35
```

---

## Section 3: System Architecture & Design (3-4 slides)

### Slide 8: What is Model Context Protocol (MCP)?

- Open standard for connecting AI assistants to data sources
- Created by Anthropic (makers of Claude)
- Enables Claude to use external tools and access data
- Server-based architecture: MCP servers provide tools to Claude Desktop
- Secure, controlled access to sensitive data

### Slide 9: Available Capabilities

**Data Upload Capability**
- **Purpose**: Load survey data into the cloud data warehouse
- **When to use**: Initial data setup or adding new survey waves
- **Privacy Design**: Controlled access to restricted storage layer
- **Key Choices**: Support for different write modes (replace, append, require empty)

**Cross-Tabulation Analysis Capability**
- **Purpose**: Generate weighted statistical breakdowns
- **When to use**: Understanding how responses vary across demographics
- **Privacy Design**: Automatic suppression of small sample sizes
- **Key Features**: Survey weighting, multi-wave comparison, flexible grouping

### Slide 10: How Data Flows Through the System

```
1. Survey Data (CSV files)
   ↓
2. Data Processing Layer
   - Separates demographic and response data
   - Removes identifying information
   - Organizes by survey wave
   ↓
3. Raw Storage Layer (restricted access)
   - Complete dataset with all fields
   - Access limited to data administrators
   - Source of truth for all analysis
   ↓
4. Privacy Transformation Layer (database views)
   - Applies geographic aggregation
   - Creates anonymous join keys
   - Filters sensitive fields
   ↓
5. Analysis Service Layer
   - Enforces minimum sample sizes
   - Validates user credentials
   - Executes statistical queries
   ↓
6. AI Assistant Interface
   - Presents privacy-protected results
   - Generates insights and interpretations
```

### Slide 11: Architectural Design Principles

**1. Separation of Concerns**
   - Raw data storage isolated from public access
   - Privacy transformations applied at database view layer
   - Additional protections enforced at service layer

**2. Defense in Depth**
   - Multiple privacy mechanisms working together
   - Authentication at entry point
   - Access controls at storage layer
   - Statistical disclosure controls at output

**3. Fail-Safe Defaults**
   - Authentication required from startup
   - Small samples suppressed automatically
   - Sensitive fields excluded by design

**4. Transparency & Auditability**
   - Privacy rules defined in declarative SQL
   - All transformations version controlled
   - Query patterns can be logged and reviewed

### Slide 12: Privacy Architecture - Design Decisions

**Decision 1: Database Views vs. Application-Level Filtering**
- **Choice**: Implement privacy transformations as database views
- **Rationale**:
  - Declarative, auditable privacy rules
  - Impossible to bypass (enforced at data layer)
  - Reusable across different analysis tools
  - Performance benefits (query optimization)

**Decision 2: Hash-Based Joins vs. Direct IDs**
- **Choice**: Replace user IDs with cryptographic hashes
- **Rationale**:
  - Allows joining demographic and response tables
  - Prevents reverse lookup to identify individuals
  - Deterministic (same person = same hash within wave)

**Decision 3: Geographic Aggregation Level**
- **Choice**: Aggregate states to 5 US regions
- **Rationale**:
  - Balances privacy protection with analytical utility
  - Prevents identification in low-population states
  - Still allows meaningful regional comparisons
  - Follows established research standards

**Decision 4: Minimum Sample Size Threshold**
- **Choice**: Suppress results with n<10
- **Rationale**:
  - Industry standard for k-anonymity
  - Prevents identification in small subgroups
  - Applied at final output (can be adjusted)
  - Clear communication to users

### Slide 13: Workflow - Processing a New Survey Wave

**Phase 1: Data Preparation**
- Read raw survey export files
- Separate demographic and response variables
- Remove personally identifiable fields
- Add temporal markers (wave number, date)

**Phase 2: Cloud Storage**
- Upload to restricted storage layer
- Validate data quality and schema
- Create backup of previous version
- Update metadata and documentation

**Phase 3: Privacy Layer Creation**
- Define transformation rules (SQL views)
- Apply geographic aggregation logic
- Configure anonymous join mechanisms
- Test privacy protections

**Phase 4: Validation & Deployment**
- Verify row counts and joins work correctly
- Test sample analyses with new data
- Document any schema changes
- Enable access through MCP tools

---

## Section 4: Simple Examples (4-5 slides)

### Slide 14: Example 1 - Simple Cross-Tabulation

**Research Question:** "How does trust in Congress vary by party affiliation?"

**User Request to Claude:**
```
"Generate a cross-tab of trust in Congress by party affiliation for wave 35"
```

**What Happens:**
- Claude automatically selects the appropriate analysis tool
- System applies survey weights for population-representative results
- Cell suppression enforced for privacy (n≥10)

**Sample Results:**
| Party Affiliation | Trust Level | Weighted % | Count |
|-------------------|-------------|------------|-------|
| Strong Democrat | High | 45.2% | 234 |
| Lean Democrat | High | 38.1% | 156 |
| Independent | Medium | 52.3% | 287 |
| Lean Republican | Low | 31.4% | 142 |
| Strong Republican | Low | 28.7% | 198 |

**Privacy Note:** Any cells with fewer than 10 respondents show `[suppressed]`

### Slide 15: Example 2 - Demographic Breakdown

**Question:** "Show me approval ratings by education level"

**Claude Desktop Conversation:**
```
User: "What's the presidential approval rating across education categories?"

Claude uses: generate_bigquery_crosstab
- survey_variable: "approval_pres"
- demographic_variable: "education_cat"
- waves: [35]
```

**Results:**
| Education Level | Approve | Disapprove | Neutral | Count |
|-----------------|---------|------------|---------|-------|
| High School or Less | 42.3% | 48.2% | 9.5% | 428 |
| Some College | 45.7% | 43.1% | 11.2% | 512 |
| Bachelor's Degree | 51.2% | 39.8% | 9.0% | 367 |
| Graduate Degree | 58.3% | 33.4% | 8.3% | 193 |

### Slide 16: Example 3 - Regional Analysis

**Question:** "How do regional differences affect policy preferences?"

**Claude Desktop Conversation:**
```
User: "Compare healthcare issue importance across US regions"

Claude uses: generate_bigquery_crosstab
- survey_variable: "issue_healthcare"
- demographic_variable: "region"
- waves: [35, 35.1]
```

**Results:**
| Region | Very Important | Somewhat Important | Not Important | Count |
|--------|----------------|-------------------|---------------|-------|
| Northeast | 67.8% | 25.3% | 6.9% | 312 |
| Mid-Atlantic | 65.2% | 28.1% | 6.7% | 298 |
| Midwest | 61.4% | 30.2% | 8.4% | 445 |
| South | 63.9% | 27.8% | 8.3% | 587 |
| West | 68.1% | 24.6% | 7.3% | 398 |

**Note:** Geography aggregated to regions for privacy protection

### Slide 17: Example 4 - Multi-Wave Trend Analysis

**Question:** "How has public opinion changed over time?"

**Claude Desktop Conversation:**
```
User: "Show trust in media trends across waves 35, 35.1, and 36"

Claude uses: generate_bigquery_crosstab
- survey_variable: "trust_media"
- demographic_variable: "wave"
- waves: [35, 35.1, 36]
```

**Results:**
| Wave | High Trust | Medium Trust | Low Trust | Count |
|------|-----------|--------------|-----------|-------|
| 35 | 28.4% | 41.2% | 30.4% | 1,247 |
| 35.1 | 26.9% | 42.7% | 30.4% | 1,183 |
| 36 | 25.1% | 43.2% | 31.7% | 1,305 |

**Insight:** Slight decline in high trust over time

### Slide 18: Example 5 - Upload Synthetic Data for Testing

**Question:** "How do I test with synthetic data?"

**Claude Desktop Conversation:**
```
User: "Upload the synthetic demographics file to my test project"

Claude uses: upload_csv_to_bigquery
- csv_path: "synthetic_data/synthetic_demographics.csv"
- project_id: "my-test-project"
- dataset_id: "chip50_test"
- table_id: "demographics"
- write_disposition: "WRITE_TRUNCATE"
```

**Results:**
```
✓ Uploaded 1,500 rows to my-test-project.chip50_test.demographics
✓ Schema: 15 columns detected
✓ Table replaced successfully
```

---

## Section 5: Technical Architecture (2-3 slides)

### Slide 19: Technology Stack

**Backend:**
- Python 3.10+ (core language)
- Google Cloud BigQuery (data warehouse)
- Pandas (data processing)
- MCP SDK 0.9.0+ (Model Context Protocol)

**Data Processing:**
- CSV file processing scripts
- SQL views for privacy transformations
- Bash scripts for automation

**Deployment:**
- MCPB package format for easy installation
- uv package manager for dependency management
- Environment variables for configuration

**Security:**
- API key authentication
- BigQuery IAM permissions
- Environment-based secrets management

### Slide 20: Project File Structure

```
chip50MCP/
├── mcp_server/
│   ├── server.py          # Main MCP server (with inline dependencies)
│   ├── mcpb.json          # Package metadata
│   └── pyproject.toml     # Python package config
├── sql/
│   ├── create_demographics_protected_w35.sql
│   ├── create_survey_responses_protected_w35.sql
│   └── [SQL scripts for each wave]
├── synthetic_data/
│   ├── generate_synthetic_data.py
│   ├── synthetic_demographics.csv (1,500 safe test rows)
│   └── synthetic_survey_responses.csv
├── data/                  # Real data (gitignored)
│   ├── CSP_W35.csv
│   └── processed/
├── process_real_data_by_wave.py
├── upload_real_data_by_wave.py
├── WAVE_BASED_WORKFLOW.md
└── README.md
```

### Slide 21: Installation & Setup

**Option 1: Install as MCPB Package (Recommended)**
1. Download `chip50MCP.mcpb` file
2. In Claude Desktop: Extensions → Install from file
3. Select the .mcpb file
4. Set environment variables:
   ```bash
   CHIP50_API_KEY=chip50_test_synthetic_data_only
   CHIP50_PROJECT_ID=your-gcp-project
   ```

**Option 2: Developer Setup**
1. Clone repository
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Add to `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "chip50-survey-mcp": {
         "command": "uv",
         "args": ["run", "/path/to/chip50MCP/mcp_server/server.py"]
       }
     }
   }
   ```
4. Restart Claude Desktop

---

## Section 6: Benefits & Impact (2 slides)

### Slide 22: Key Benefits

**For Researchers:**
- AI-assisted analysis reduces time from hours to minutes
- Natural language queries (no SQL knowledge required)
- Automatic privacy protections built-in
- Reproducible analyses with synthetic data for testing

**For Data Privacy:**
- Multiple layers of protection (PII removal, aggregation, suppression)
- No direct access to raw data
- Transparent privacy rules encoded in SQL
- Audit trail of all queries

**For Organizations:**
- Democratizes access to survey data
- Reduces burden on data administrators
- Scalable cloud infrastructure
- Standards-based MCP integration

### Slide 23: Future Enhancements

**Planned Features:**
- More sophisticated API key management (OAuth, JWT)
- Additional statistical tools (regression, time series)
- Visualization generation (charts, maps)
- Automated report generation
- Support for more data sources beyond BigQuery

**Community Contributions Welcome:**
- Open source (MIT License)
- Extensible architecture
- Documentation for developers
- Synthetic data for safe experimentation

---

## Formatting Instructions

Please format this presentation with:

1. **Clear, concise bullet points** (avoid walls of text)
2. **Code examples** in properly formatted code blocks with syntax highlighting
3. **Visual hierarchy** with headers, subheaders, and emphasis
4. **Consistent style** throughout all slides
5. **Tables** for data examples (properly aligned)
6. **Callout boxes** for important privacy/security notes
7. **Diagrams** or ASCII art for architecture flows (if possible)
8. **Page numbers** and section markers

**Tone:** Professional yet accessible, assuming audience has mixed technical background (some technical, some non-technical stakeholders).

**Length:** Aim for 20-25 slides total, can be adjusted based on need.

**Output format:** Markdown format suitable for conversion to PDF/PowerPoint, or Google Slides if you can generate that directly.

---

## Additional Context

- This is a real research project for analyzing public opinion survey data
- Privacy is paramount - this handles real human survey responses
- The synthetic data allows safe testing and demonstrations without privacy risks
- The wave-based architecture reflects how longitudinal surveys actually work in practice
- MCP is a new technology (2024) that makes AI assistants more powerful and useful
