# Architecture Documentation - Remote MCP Server

## Overview

This project implements a **REMOTE** Model Context Protocol (MCP) server, fundamentally different from local MCP implementations.

## Key Architectural Decisions

### Remote vs Local MCP

**This is a REMOTE MCP server:**

| Aspect | This Project (Remote) | Traditional MCP (Local) |
|--------|----------------------|------------------------|
| **Deployment** | Google Cloud Run | Local machine |
| **Transport** | SSE (Server-Sent Events) | stdio (standard input/output) |
| **Protocol** | HTTP/HTTPS | Process communication |
| **Configuration** | `url` + API key | `command` + `args` |
| **Resources** | Cloud resources | Local CPU/memory |
| **Access** | Anywhere with internet | Only on local machine |
| **Scaling** | Auto-scales serverless | Single process |
| **Cost** | Pay-per-use | Free (uses local resources) |

### Why Remote MCP?

1. **No Local Resource Usage**: BigQuery queries can be expensive - offload to cloud
2. **Multi-Device Access**: Use from desktop, laptop, tablet with same config
3. **Team Sharing**: Multiple users can access the same MCP server
4. **Data Centralization**: BigQuery dataset lives in cloud, not local files
5. **Scalability**: Handles concurrent requests from multiple users
6. **Always Available**: Not dependent on your machine being on

## System Architecture

```
┌─────────────────┐
│ Claude Desktop  │
│   (Client)      │
└────────┬────────┘
         │ HTTPS/SSE
         │ API Key Auth
         ▼
┌─────────────────────────┐
│   Google Cloud Run      │
│  ┌──────────────────┐   │
│  │  FastAPI Server  │   │
│  │  - SSE Transport │   │
│  │  - MCP Protocol  │   │
│  │  - Auth Layer    │   │
│  └────────┬─────────┘   │
│           │              │
│           │ SDK          │
│           ▼              │
│  ┌──────────────────┐   │
│  │  BigQuery Client │   │
│  └──────────────────┘   │
└───────────┬──────────────┘
            │ BigQuery API
            ▼
┌────────────────────────┐
│   BigQuery Dataset     │
│  ┌──────────────────┐  │
│  │  demographics    │  │
│  │  (10k rows)      │  │
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ platform_usage   │  │
│  │  (10k rows)      │  │
│  └──────────────────┘  │
└────────────────────────┘
```

## Transport Layer: SSE vs stdio

### Traditional Local MCP (stdio)
```json
{
  "mcpServers": {
    "local-server": {
      "command": "python",
      "args": ["server.py"]
    }
  }
}
```

**Process:**
1. Claude Desktop spawns a local Python process
2. Communicates via stdin/stdout pipes
3. JSON-RPC over process pipes
4. Single-machine, single-user

### This Project (Remote SSE)
```json
{
  "mcpServers": {
    "remote-server": {
      "url": "https://service.run.app/sse",
      "transport": {
        "type": "sse"
      },
      "env": {
        "API_KEY": "..."
      }
    }
  }
}
```

**Process:**
1. Claude Desktop makes HTTPS connection to Cloud Run
2. Server-Sent Events (SSE) for streaming responses
3. API key in Authorization header
4. Multi-device, potentially multi-user

## Technology Stack

### Backend
- **FastAPI**: Modern async web framework for Python
- **MCP Python SDK**: Official MCP protocol implementation
- **SSE Transport**: `mcp.server.sse.SseServerTransport`
- **Google Cloud BigQuery**: Serverless data warehouse
- **Pandas**: Data manipulation and analysis

### Infrastructure
- **Google Cloud Run**: Serverless container platform
  - Auto-scales from 0 to N instances
  - Pay only for request time
  - Built-in HTTPS, load balancing, health checks
- **Google Container Registry**: Docker image storage
- **Google Cloud Build**: Automated container builds
- **BigQuery**: 10k+ row synthetic dataset

### Security
- **API Key Authentication**: Custom middleware validates `Authorization` header
- **HTTPS Only**: TLS encryption for all traffic
- **Cell Suppression**: Privacy protection (n<10 suppressed)
- **No PII Storage**: Only aggregated demographics

## Data Flow

### Query Execution Path

```
1. User asks Claude: "Show me Twitter usage by age"
   ↓
2. Claude calls MCP tool: generate_crosstab(platform="twitter", demographic="age_group")
   ↓
3. HTTPS POST to Cloud Run /sse endpoint
   ↓
4. FastAPI receives request, validates API key
   ↓
5. MCP server routes to _generate_crosstab()
   ↓
6. BigQuery client executes SQL query
   ↓
7. Results returned, cell suppression applied
   ↓
8. JSON response streamed via SSE
   ↓
9. Claude receives data, presents to user
```

### Async Processing

The server uses Python `asyncio` for efficient concurrent request handling:

```python
# Single request
await self._generate_crosstab(platform, demographic)

# Batch requests (parallel execution)
tasks = [self._generate_crosstab(platform, demo) for demo in demographics]
results = await asyncio.gather(*tasks)
```

This allows:
- Multiple demographics analyzed in parallel
- Non-blocking I/O for BigQuery queries
- Efficient resource usage on Cloud Run

## Configuration Management

### Environment Variables (Cloud Run)

Set via deployment:
```bash
gcloud run deploy ... \
  --set-env-vars "GCP_PROJECT=...,API_KEY=...,DATASET_NAME=..."
```

### Client Configuration (Claude Desktop)

Stored locally in `claude_desktop_config.json`:
- Service URL (from deployment)
- API key (generated during deployment)
- Transport type (sse)

## Deployment Pipeline

```
1. Developer runs ./deploy.sh
   ↓
2. Script enables Google Cloud APIs
   ↓
3. Creates BigQuery dataset + synthetic data
   ↓
4. Cloud Build builds Docker container
   ↓
5. Container pushed to GCR
   ↓
6. Cloud Run deploys new revision
   ↓
7. Health checks pass
   ↓
8. Service URL ready for Claude Desktop
```

## Privacy Architecture

### Multi-Layer Protection

1. **Cell Suppression**: SQL-level filtering
   ```sql
   CASE WHEN n < 10 THEN TRUE ELSE FALSE END as suppressed
   ```

2. **Application-Level**: Python clears suppressed values
   ```python
   df.loc[df['suppressed'], 'n'] = None
   ```

3. **No Raw Data**: Only aggregated views exposed
4. **Synthetic Data**: No real PII in dataset
5. **Access Control**: API key required for all queries

## Scaling Characteristics

### Cloud Run Auto-Scaling

- **Min Instances**: 0 (scales to zero when idle)
- **Max Instances**: 10 (configurable)
- **Concurrency**: 80 requests per instance (default)
- **CPU Allocation**: Only during request processing

### BigQuery Performance

- **Cached Queries**: Automatic 24-hour cache
- **Partitioning**: Tables clustered by `row_hash`
- **Cost**: First 1TB queries/month free

## Cost Model

### Serverless Pricing

**Cloud Run:**
- Free tier: 2M requests/month
- CPU: $0.00002400 per vCPU-second
- Memory: $0.00000250 per GiB-second
- Typical: ~$5-10/month

**BigQuery:**
- Free tier: 1TB queries/month, 10GB storage
- Our dataset: ~100MB
- Typical: ~$1-5/month

**Total: ~$6-15/month for personal use**

## Monitoring & Observability

### Cloud Run Metrics
- Request count
- Request latency (p50, p95, p99)
- Container instances
- CPU/memory utilization
- Error rates

### Logs
```bash
gcloud run logs read social-media-demographics-mcp --region us-central1
```

### Health Checks
- `/health` endpoint: Validates BigQuery connectivity
- Cloud Run health checks: Automatic instance replacement

## Comparison with Original Local MCP

This project was derived from a local CHIP50 MCP server. Key transformations:

| Component | Local (Original) | Remote (This Project) |
|-----------|-----------------|----------------------|
| Server Framework | `mcp.server.Server` | FastAPI + `mcp.server.Server` |
| Transport | stdio | SSE (`SseServerTransport`) |
| Launch | Claude spawns process | Claude connects to URL |
| Authentication | None (local trust) | API key |
| Data Access | Direct BigQuery client | Same, but in container |
| Deployment | `uv run server.py` | Docker + Cloud Run |
| Configuration | `.mcpb.json` | `deploy.sh` + Cloud Run config |

## Future Enhancements

### Potential Improvements

1. **Multi-Tenancy**: Support multiple API keys with rate limits per user
2. **Caching Layer**: Redis for frequently requested crosstabs
3. **WebSocket Transport**: For bidirectional streaming
4. **GraphQL API**: Alternative to REST for complex queries
5. **VPC Connector**: Private BigQuery access (no public internet)
6. **Cloud Armor**: DDoS protection, rate limiting
7. **Cloud CDN**: Cache static responses globally
8. **Audit Logging**: Track all queries for compliance

### Scaling Beyond Personal Use

For production/team use:
- Implement OAuth2 instead of simple API keys
- Add usage quotas per user
- Set up Cloud Monitoring alerts
- Enable Cloud Trace for request tracing
- Add BigQuery slot reservations for predictable performance

## Development Workflow

### Local Testing
```bash
./test_local.sh  # Runs server on localhost:8080
```

### Deploy to Cloud
```bash
./deploy.sh  # Full deployment pipeline
```

### Update Deployed Service
```bash
# Code changes
gcloud builds submit --tag gcr.io/$GCP_PROJECT/social-media-demographics-mcp
gcloud run deploy social-media-demographics-mcp \
  --image gcr.io/$GCP_PROJECT/social-media-demographics-mcp \
  --region us-central1
```

## Summary

This is a **remote MCP server** designed for:
- ✅ Cloud-native deployment (Google Cloud Run)
- ✅ Remote access via HTTPS/SSE
- ✅ Serverless auto-scaling
- ✅ BigQuery data warehouse integration
- ✅ Multi-device accessibility
- ✅ Production-ready security and monitoring

It demonstrates that MCP servers don't have to run locally - they can be deployed as scalable, serverless microservices accessible from anywhere.
