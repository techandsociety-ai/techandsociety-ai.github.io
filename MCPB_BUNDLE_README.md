# CHIP50 Survey Analysis - MCPB Bundle

**Privacy-preserving survey data analysis for Claude Desktop**

Version: 2.0.0
Bundle: `chip50-survey-mcp-v2.0.0.mcpb`

---

## What's Included

This MCPB bundle provides privacy-protected access to CHIP50 survey data through Claude Desktop:

### ✅ Privacy Features
- **Automatic Cell Suppression** - Cells with n<10 automatically hidden
- **Geographic Aggregation** - States aggregated to 5 regions
- **No PII** - User IDs and identifiable data excluded
- **Protected Views** - Queries only privacy-safe BigQuery views

### ✅ Tools
1. **`get_available_variables`** - Discover available data
2. **`generate_crosstab`** - Generate privacy-protected crosstabs

### ✅ Data Access
- 500 respondents × 3 waves = 1,500 observations
- 8 demographic variables (region, age, education, party, etc.)
- 12 survey variables (trust scales, approval ratings, etc.)
- Weighted analysis for population estimates

---

## Installation

### Method 1: Drag and Drop (Easiest)

1. Download `chip50-survey-mcp-v2.0.0.mcpb`
2. Open Claude Desktop
3. Go to **Settings → MCP Servers**
4. Drag the `.mcpb` file into the window

### Method 2: File Picker

1. Download `chip50-survey-mcp-v2.0.0.mcpb`
2. Open Claude Desktop
3. Go to **Settings → MCP Servers**
4. Click **"Add Server"** or **"Install from File"**
5. Select the `.mcpb` file

---

## Configuration

### Required: Google Cloud Authentication

The bundle accesses BigQuery, so you need Google Cloud credentials:

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set project
gcloud config set project chip50
```

### Required: Environment Variables in Claude Desktop

After installing the bundle, configure in Claude Desktop settings:

| Variable | Value |
|----------|-------|
| `CHIP50_API_KEY` | `chip50_test_synthetic_data_only` |
| `CHIP50_PROJECT_ID` | `chip50` |
| `CHIP50_DATASET_PUBLIC` | `public` |

**How to set in Claude Desktop:**
1. Settings → MCP Servers
2. Find "CHIP50 Survey Analysis"
3. Click settings/gear icon
4. Add environment variables

---

## Usage Examples

### Discover Available Data

**Ask Claude:**
> "What variables are available in the CHIP50 data?"

Claude will call `get_available_variables()` and show you all demographic and survey variables with descriptions.

### Generate a Crosstab

**Ask Claude:**
> "Show me trust in Congress by party affiliation"

Claude will call `generate_crosstab(survey_variable="trust_congress", demographic_variable="party_7")` and display results with automatic privacy protection.

### Filter by Wave

**Ask Claude:**
> "Show vote intention by region for wave 9 only"

Results will include only wave 9 data with cell suppression applied.

---

## Privacy Protections Explained

### Cell Suppression (n≥10)
Any crosstab cell with fewer than 10 respondents is automatically suppressed:

```json
{
  "demographic_value": "Native American",
  "survey_value": 1,
  "count": "[suppressed]",
  "note": "n<10 (privacy protection)"
}
```

### Geographic Aggregation
States are aggregated into 5 regions:
- **Northeast** - ME, NH, VT, MA, RI, CT
- **Mid-Atlantic** - NY, NJ, PA
- **Midwest** - OH, IN, IL, MI, WI, MN, IA, MO, ND, SD, NE, KS
- **South** - DE, MD, VA, WV, NC, SC, GA, FL, KY, TN, AL, MS, AR, LA, OK, TX
- **West** - MT, ID, WY, CO, NM, AZ, UT, NV, WA, OR, CA, AK, HI

### No User IDs
The protected views use non-reversible hashes instead of user IDs, making re-identification impossible.

---

## Troubleshooting

### "CHIP50_API_KEY environment variable not set"
- Configure environment variables in Claude Desktop settings
- Make sure to use exact value: `chip50_test_synthetic_data_only`

### "Invalid authorization header"
- This is a UI message from MCP inspector, not our server
- Disable the authorization header toggle in inspector
- Our authentication uses environment variables, not HTTP headers

### "Error: No data returned"
- Check variable names are correct (case-sensitive)
- Use `get_available_variables` to see valid options
- Verify you have BigQuery access: `bq ls --project_id=chip50`

### BigQuery Authentication Errors
```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project
# Should return: chip50
```

---

## Building the Bundle (Developers)

To rebuild the bundle from source:

```bash
# Build the MCPB bundle
./build_mcpb.sh

# Output: chip50-survey-mcp-v2.0.0.mcpb
```

The build script:
1. Cleans previous builds
2. Copies necessary files
3. Creates ZIP archive with `.mcpb` extension
4. Generates SHA-256 checksum

---

## Architecture

```
User (Claude Desktop)
    ↓
MCPB Bundle (Local)
├─ Cell Suppression (n≥10)
├─ Privacy Logic
└─ BigQuery Client
    ↓
chip50.public.* (Protected Views)
├─ demographics_protected
└─ survey_responses_protected
```

**Key Points:**
- ✅ **No Remote Server** - Everything runs locally
- ✅ **Direct BigQuery** - Queries protected views directly
- ✅ **User's GCP Credentials** - No centralized auth needed
- ✅ **Privacy Enforced** - Cell suppression + protected views

---

## What's Different from Phase 2

| Aspect | Phase 2 | Phase 3 (MCPB Bundle) |
|--------|---------|----------------------|
| **Distribution** | Manual setup | MCPB bundle (drag-and-drop) |
| **Tools** | `upload_csv`, `generate_bigquery_crosstab` | `get_available_variables`, `generate_crosstab` |
| **Privacy** | View-level only | View + cell suppression |
| **Data Access** | Raw tables | Protected views |
| **Installation** | Clone repo + config | Install bundle in Claude Desktop |
| **Updates** | Git pull | Download new `.mcpb` file |

---

## Files in Bundle

```
chip50-survey-mcp-v2.0.0.mcpb/
├── manifest.json              # Bundle configuration
├── mcp_server/
│   └── server.py             # MCP server (updated for Phase 3)
├── synthetic_data/           # Synthetic data files
├── sql/                      # Protected view definitions
├── README.md                 # Project overview
├── QUICKSTART.md            # Usage guide
├── SETUP.md                 # Database setup
└── pyproject.toml           # Python dependencies
```

---

## Support & Documentation

- **Quick Start**: See `QUICKSTART.md` in bundle
- **Database Setup**: See `SETUP.md` in bundle
- **Technical Details**: See `buildplan.md` (not in bundle)
- **Issues**: Report to repository

---

## License

MIT License - See LICENSE file

---

## Version History

### v2.0.0 (Current)
- ✅ Privacy-protected views (`chip50.public.*`)
- ✅ Automatic cell suppression (n≥10)
- ✅ Geographic aggregation (states → regions)
- ✅ New tools: `get_available_variables`, `generate_crosstab`
- ✅ MCPB bundle packaging

### v1.0.0 (Legacy)
- Direct raw data access
- Tools: `upload_csv_to_bigquery`, `generate_bigquery_crosstab`
- No privacy protections

---

**Ready to analyze survey data with privacy protections built-in!** 🎉
