# Context Engine MVP - Blue-to-Budget Reconciliation Pipeline

A domain-specific system that bridges unstructured enterprise data (construction blueprints) and autonomous agents (budget management systems) using a stateful Neo4j graph database ontology.

## Overview

The Context Engine solves a critical problem in construction: when a Designer changes a Blueprint (The "Blue"), the Accountant doesn't find out until weeks later when an invoice arrives (The "Budget"). This creates dangerous lag where budget overruns are discovered too late.

Our engine closes this gap in real-time using:
- **Neo4j Graph Database**: Maintains a "Digital Twin" of project state
- **Claude 3.5 Sonnet**: Reasons about changes and recommends actions
- **Stateful Delta Calculation**: Knows exactly what changed and the budget impact

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: INGESTION (Document → Structure)                  │
│  - PDF Blueprints parsed to JSON                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: ONTOLOGY (The Digital Twin)                       │
│  - Neo4j Graph stores current state and relationships       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: REASONING & DISPATCH (Decision → Action)          │
│  - Claude analyzes changes and recommends actions           │
│  - Dispatcher executes updates or flags for approval        │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Python 3.11+** (for local development)
- **Anthropic API Key** (get it from: https://console.anthropic.com/)

### 1. Clone and Setup

```bash
# Navigate to project directory
cd ContextEngine

# Copy environment template
cp .env.example .env

# Edit .env and add your Anthropic API key
# NEO4J_PASSWORD is set to 'contextengine123' by default
nano .env  # or use your preferred editor
```

### 2. Start Services with Docker Compose

```bash
# Start Neo4j and the application
docker-compose up -d

# Check that services are running
docker-compose ps
```

This will start:
- **Neo4j** on ports 7474 (browser) and 7687 (bolt)
- **Context Engine** application container

### 3. Initialize Neo4j Database

#### Option A: Via Neo4j Browser (Recommended)

1. Open Neo4j Browser: http://localhost:7474
2. Login with credentials:
   - Username: `neo4j`
   - Password: `contextengine123` (or your custom password from .env)
3. Run the schema initialization:
   - Copy contents of `neo4j/init_schema.cypher`
   - Paste into query window and execute
4. Load sample data:
   - Copy contents of `neo4j/sample_data.cypher`
   - Paste into query window and execute

#### Option B: Via Command Line

```bash
# Copy the files into the container
docker cp neo4j/init_schema.cypher context-engine-neo4j:/var/lib/neo4j/import/
docker cp neo4j/sample_data.cypher context-engine-neo4j:/var/lib/neo4j/import/

# Execute via cypher-shell
docker exec -it context-engine-neo4j cypher-shell -u neo4j -p contextengine123 < /var/lib/neo4j/import/init_schema.cypher
docker exec -it context-engine-neo4j cypher-shell -u neo4j -p contextengine123 < /var/lib/neo4j/import/sample_data.cypher
```

### 4. Verify Setup

```bash
# Run tests
docker-compose run context-engine pytest tests/ -v

# Or run tests locally if you have Python installed
pip install -r requirements.txt
pytest tests/ -v
```

## Project Structure

```
ContextEngine/
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Python application container
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variable template
├── README.md                  # This file
│
├── data/
│   ├── mock_blueprints/
│   │   ├── before.json        # Initial blueprint state
│   │   └── after.json         # Changed blueprint state
│   └── budget_state.json      # Mock budget API storage
│
├── neo4j/
│   ├── init_schema.cypher     # Graph schema initialization
│   └── sample_data.cypher     # Sample data for testing
│
├── src/
│   ├── ingestion/             # PDF parsing module
│   │   ├── __init__.py
│   │   └── parser.py          # BlueprintParser class
│   │
│   ├── librarian/             # Neo4j query logic
│   │   ├── __init__.py
│   │   ├── graph_client.py    # Neo4j connection
│   │   └── state_queries.py   # State management queries
│   │
│   ├── briefcase/             # Context assembly for Claude
│   │   ├── __init__.py
│   │   ├── assembler.py       # BriefcaseAssembler class
│   │   └── templates.py       # Prompt templates
│   │
│   ├── reasoner/              # Claude API integration
│   │   ├── __init__.py
│   │   └── claude_client.py   # ClaudeClient class
│   │
│   └── dispatcher/            # Action execution
│       ├── __init__.py
│       ├── actions.py         # ActionDispatcher class
│       └── budget_api.py      # MockBudgetAPI class
│
└── tests/
    ├── __init__.py
    └── test_pipeline.py       # Integration tests
```

## How It Works

### The Blue-to-Budget Workflow

1. **Ingestion**: Blueprint is parsed to structured JSON
   - In MVP: Reads from `data/mock_blueprints/`
   - Future: Integrates with Reducto.ai or Unstructured.io

2. **Librarian Check**: Query Neo4j for current state
   - What's the current quantity of Wall_A?
   - What's the cost per unit?
   - Which budget line item is affected?

3. **Delta Calculation**: Compare current vs new state
   - Wall_A: 400 sqft → 500 sqft (+100 sqft)
   - Cost impact: 100 sqft × $10/sqft = $1,000

4. **Briefcase Assembly**: Construct context for Claude
   - Current state from graph
   - Detected changes
   - Business rules (approval thresholds, contingency limits)

5. **Claude Reasoning**: Analyze and recommend action
   - Is the change within acceptable thresholds?
   - Should it be auto-approved or flagged?
   - What's the confidence level?

6. **Dispatch Action**: Execute the recommendation
   - Auto-approve: Update budget directly
   - Flag for approval: Add to approval queue

## Example Usage

### Running the Complete Pipeline

Create a Python script `run_pipeline.py`:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

from src.ingestion.parser import BlueprintParser
from src.librarian.graph_client import GraphClient
from src.librarian.state_queries import StateQueries
from src.briefcase.assembler import BriefcaseAssembler
from src.reasoner.claude_client import ClaudeClient
from src.dispatcher.actions import ActionDispatcher
from src.dispatcher.budget_api import MockBudgetAPI

# Load environment variables
load_dotenv()

# Initialize components
parser = BlueprintParser(mock_mode=True)
graph_client = GraphClient(
    uri=os.getenv('NEO4J_URI'),
    user=os.getenv('NEO4J_USER'),
    password=os.getenv('NEO4J_PASSWORD')
)
state_queries = StateQueries(graph_client)
assembler = BriefcaseAssembler(approval_threshold=500.0)
claude = ClaudeClient(api_key=os.getenv('ANTHROPIC_API_KEY'))
budget_api = MockBudgetAPI(os.getenv('BUDGET_API_FILE'))
dispatcher = ActionDispatcher(budget_api)

# Parse blueprints
before = parser.parse_blueprint(Path('data/mock_blueprints/before.json'))
after = parser.parse_blueprint(Path('data/mock_blueprints/after.json'))

# Compare blueprints
changes = parser.compare_blueprints(before, after)

# Process each modified asset
for change in changes['modified']:
    asset_id = change['asset_id']
    new_quantity = change['after'].quantity

    # Calculate delta from graph state
    delta = state_queries.calculate_delta(asset_id, new_quantity)

    # Assemble briefcase
    briefcase = assembler.assemble_asset_change(delta)

    # Get Claude's recommendation
    recommendation = claude.reason_about_change(
        briefcase,
        assembler.get_function_definition()
    )

    # Dispatch action
    result = dispatcher.dispatch(
        recommendation,
        asset_id=asset_id,
        budget_code=delta['lineitem']['id'],
        cost_impact=delta['cost_impact']
    )

    print(f"\nAsset: {asset_id}")
    print(f"Action: {result['action_type']}")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Reasoning: {recommendation['reasoning']}")

# Clean up
graph_client.close()
```

Run it:

```bash
python run_pipeline.py
```

### Querying Neo4j Directly

```cypher
// Get all objects and their budget linkages
MATCH (o:Object)-[:INFLUENCES]->(li:LineItem)-[:SOURCED_FROM]->(v:Vendor)
RETURN o.id, o.quantity, o.cost_per_unit, li.code, v.name

// Get the "blast radius" of Wall_A changes
MATCH (o:Object {id: 'Wall_A'})-[:LOCATED_ON]->(f:Floor)-[:BELONGS_TO]->(p:Project)
MATCH (o)-[:INFLUENCES]->(li:LineItem)
RETURN o, f, p, li

// Calculate current project costs
MATCH (p:Project {id: 'proj_001'})<-[:BELONGS_TO]-(f:Floor)<-[:LOCATED_ON]-(o:Object)
RETURN sum(o.total_cost) as total_asset_cost
```

## Testing Scenarios

The system includes three key test scenarios:

### Scenario 1: Minor Change (Auto-Approve)
- Wall_A: 400 → 450 sqft
- Cost impact: $500
- Expected: Auto-approved (at threshold)

### Scenario 2: Major Change (Flag for Approval)
- Wall_A: 400 → 600 sqft
- Cost impact: $2,000
- Expected: Flagged for human approval

### Scenario 3: New Asset Added
- HVAC_Unit_1 added to blueprint
- Cost impact: Unknown
- Expected: Flagged for budget allocation review

## Configuration

### Environment Variables

Edit `.env` to configure:

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=contextengine123

# Anthropic
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Business Rules
APPROVAL_THRESHOLD=500.00
MAX_CONTINGENCY=5000.00
MIN_CONFIDENCE_THRESHOLD=0.85
```

### Business Rules

The system uses configurable business rules:

- **Approval Threshold**: Changes exceeding this dollar amount require approval
- **Max Contingency**: Maximum budget contingency available
- **Min Confidence**: Minimum confidence score for auto-approval (0.0-1.0)

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Neo4j separately
# (Download from https://neo4j.com/download/)

# Run tests
pytest tests/ -v

# Run with code quality checks
black src/
flake8 src/
mypy src/
```

### Adding New Features

The system is designed to be extended:

1. **New Asset Types**: Add to Neo4j schema and update parser
2. **New Business Rules**: Modify `BriefcaseAssembler` templates
3. **Real PDF Parsing**: Implement in `ingestion/parser.py`
4. **Real Budget API**: Implement in `dispatcher/budget_api.py`

## Troubleshooting

### Neo4j Connection Issues

```bash
# Check Neo4j is running
docker-compose ps

# View Neo4j logs
docker-compose logs neo4j

# Restart Neo4j
docker-compose restart neo4j
```

### API Key Issues

```bash
# Test Anthropic API key
python -c "from anthropic import Anthropic; client = Anthropic(api_key='your_key'); print('Valid')"
```

### Database Not Initialized

If you get errors about missing nodes:

1. Ensure schema was initialized (`init_schema.cypher`)
2. Ensure sample data was loaded (`sample_data.cypher`)
3. Check Neo4j Browser at http://localhost:7474

## Known Limitations (MVP)

- **Single Project**: Only handles one project at a time
- **Synthetic Data**: Not tested on real construction blueprints
- **Mock Budget API**: No real integration with Procore/Autodesk
- **No Rollback**: Changes are not easily reversible
- **Limited Error Handling**: Assumes perfect data quality

## Roadmap

### Week 2: Real PDF Parsing
- Integrate Reducto.ai or Unstructured.io
- Handle real construction blueprint PDFs

### Week 3: Multi-Project Support
- Project switching and isolation
- Multi-tenant considerations

### Week 4: Procore Integration
- Real budget API integration
- Bidirectional sync

### Week 5: Change History
- Audit trails
- Rollback capability

### Week 6: Real-Time Monitoring
- Webhooks for document changes
- Real-time notifications

## Contributing

This is an MVP. Contributions welcome for:
- Real PDF parsing integration
- Additional test scenarios
- Performance optimizations
- Documentation improvements

## License

[Add your license here]

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review test scenarios in `tests/`
3. Check Neo4j Browser for data issues
4. Review logs: `docker-compose logs`

---

**Built with:**
- Python 3.11
- Neo4j Community Edition
- Claude 3.5 Sonnet (Anthropic)
- Docker & Docker Compose
