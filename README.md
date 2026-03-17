# Social Media Demographics - Remote MCP Server

A **remote** Model Context Protocol (MCP) server for analyzing social media usage patterns across demographic segments, deployed on Google Cloud Run.

## 🚀 Quick Start

This repository contains a complete remote MCP server in the `remote-mcp/` directory.

```bash
cd remote-mcp
./deploy.sh
```

See [remote-mcp/QUICKSTART.md](remote-mcp/QUICKSTART.md) for a 10-minute deployment guide.

## 📦 What's Inside

**`remote-mcp/`** - Complete remote MCP server with:
- ✅ FastAPI server with SSE transport
- ✅ BigQuery integration for analytics
- ✅ 10,000 synthetic survey responses
- ✅ 8 social media platforms (Twitter, Facebook, Instagram, TikTok, LinkedIn, YouTube, Reddit, Snapchat)
- ✅ Rich demographic breakdowns
- ✅ Google Cloud Run deployment
- ✅ Privacy protection (cell suppression)
- ✅ Beautiful logo for Claude Desktop

## 📚 Documentation

- **[QUICKSTART.md](remote-mcp/QUICKSTART.md)** - Get started in 10 minutes
- **[SETUP.md](remote-mcp/SETUP.md)** - Detailed setup and configuration
- **[AGENTS.md](remote-mcp/AGENTS.md)** - Architecture and design decisions
- **[README.md](remote-mcp/README.md)** - Full project documentation

## 🎯 Features

- **Remote Access**: Accessible from anywhere via HTTPS
- **Serverless**: Runs on Google Cloud Run, auto-scales from zero
- **Privacy Protected**: Automatic cell suppression for small counts (n<10)
- **Batch Analytics**: Parallel query execution for efficiency
- **Weighted Analysis**: Population-weighted estimates
- **Multi-Device**: Use from desktop, laptop, or tablet with same configuration

## 💰 Cost

Expected monthly cost: **$5-15** for personal use (leverages Google Cloud free tier)

## 🔧 Requirements

- Google Cloud account with billing enabled
- gcloud CLI installed
- Claude Desktop

## 🚀 Deployment

```bash
# Set your Google Cloud project
export GCP_PROJECT="your-project-id"

# Deploy to Cloud Run
cd remote-mcp
./deploy.sh

# Configure Claude Desktop with the output URL and API key
```

## 📊 Example Queries

Once deployed and configured in Claude Desktop, try:

- "Show me Twitter usage by age group"
- "Compare TikTok and Facebook usage across demographics"
- "Analyze Instagram usage by education level and income"
- "What's the demographic profile of LinkedIn users?"

## 🏗️ Architecture

This is a **remote MCP server**, not a local one:

- **Transport**: SSE (Server-Sent Events) over HTTPS, not stdio
- **Deployment**: Google Cloud Run serverless containers
- **Data**: BigQuery serverless data warehouse
- **Configuration**: URL + API key, not command + args

See [remote-mcp/AGENTS.md](remote-mcp/AGENTS.md) for detailed architecture documentation.

## 📄 License

MIT License (see remote-mcp/ directory for details)

## 🤝 Contributing

This project demonstrates how to build a remote MCP server with:
- FastAPI for the web framework
- SSE transport for streaming responses
- Google Cloud Run for serverless deployment
- BigQuery for scalable data analytics
- Synthetic data generation for privacy

Feel free to fork and adapt for your own use cases!

---

**Ready to deploy?** Head to [remote-mcp/](remote-mcp/) and follow the QUICKSTART guide!
