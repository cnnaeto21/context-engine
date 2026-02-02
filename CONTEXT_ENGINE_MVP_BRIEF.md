# Context Engine MVP - Blue-to-Budget Pipeline
## Project Brief for Claude Code Implementation

---

## 1. EXECUTIVE SUMMARY

**Project Name:** The Context Engine (MVP) - Blue-to-Budget Reconciliation Pipeline

**Strategic Goal:** Build a domain-specific "Librarian & Dispatcher" layer that bridges the gap between unstructured enterprise data (construction blueprints) and autonomous agents (budget management systems).

**Timeline:** 7-day building sprint

**Core Problem Being Solved:**
In construction, a Designer changes a Blueprint (The "Blue"), but the Accountant doesn't find out until weeks later when an invoice arrives (The "Budget"). This creates a dangerous lag where budget overruns are discovered too late. Our engine closes this gap in real-time using a Stateful Ontology.

**Success Criteria:**
A working pipeline that can:
1. Accept a blueprint PDF upload
2. Parse it to structured JSON
3. Compare against existing state in Neo4j graph database
4. Calculate deltas (what changed)
5. Construct a "Briefcase of Truth" for Claude 3.5 Sonnet
6. Receive reasoned action recommendations
7. Dispatch structured Action JSON to update budgets or flag for human approval

---

## 2. ARCHITECTURAL PHILOSOPHY

### Why This Is NOT Standard RAG

**Traditional RAG Systems:**
- Search for relevant documents based on semantic similarity
- Stateless - each query is independent
- Focused on text retrieval and generation

**The Context Engine Approach:**
- Maintains a **Digital Twin** in Neo4j
- **Stateful** - knows the current state and can calculate precise deltas
- Physical relationships are explicitly linked (Wall → Floor → Budget Line Item → Vendor)
- The graph ensures that when a Wall changes, the engine knows *exactly* which budget items and vendors are impacted

### The Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: INGESTION (Document → Structure)                  │
│  - PDF Blueprints come in                                   │
│  - Reducto.ai or Unstructured.io parses to JSON             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: ONTOLOGY (The Digital Twin)                       │
│  - Neo4j Graph Database stores current state                │
│  - Nodes: Projects, Floors, Objects, LineItems, Vendors     │
│  - Relationships: Physical and financial linkages           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: REASONING & DISPATCH (Decision → Action)          │
│  - Claude 3.5 Sonnet receives "Briefcase of Truth"          │
│  - Returns structured Function Call JSON                    │
│  - Python Dispatcher executes actions                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. THE BLUE-TO-BUDGET WORKFLOW (Step-by-Step)

### Step 1: Ingestion
A PDF Blueprint is uploaded to the system.

**What happens:**
- PDF is sent to parser API (Reducto.ai or Unstructured.io)
- Parser returns JSON with physical assets extracted

**Example Output:**
```json
{
  "assets": [
    {
      "id": "Wall_A",
      "type": "Wall",
      "material": "Concrete",
      "quantity": 500,
      "unit": "sqft",
      "floor": "Floor_3"
    }
  ]
}
```

### Step 2: The "Librarian" Check (Neo4j State Query)

**Critical Concept:** We don't blindly update. We query Neo4j to see what the *current state* is.

**Example Query:**
```cypher
MATCH (obj:Object {id: 'Wall_A'})
RETURN obj.quantity AS current_quantity, 
       obj.cost_per_unit AS cost_per_unit
```

**Scenario Result:**
- Neo4j says: `Wall_A` was previously **400 sqft** at **$10/sqft** = **$4,000 budget**
- New blueprint says: **500 sqft**
- **The Delta:** +100 sqft = +$1,000 budget impact

### Step 3: The "Briefcase of Truth" (Context Injection)

We construct a structured prompt for Claude 3.5 Sonnet containing:

**Contents of the Briefcase:**
1. **Existing State from Graph:**
   - `Wall_A: 400 sqft, $10/sqft, currently allocated $4,000`
   - Linked to `Budget_LineItem_B47` 
   - Linked to `Vendor_ConcreteCo`

2. **New Delta from Parser:**
   - `Wall_A: Now shows 500 sqft in blueprint`
   - Change: +100 sqft

3. **Business Rules & Constraints:**
   - "Concrete costs $10/sqft"
   - "If a change exceeds $500, flag for approval"
   - "Maximum budget contingency is $5,000"

4. **Context:**
   - Project: "Office Building Downtown"
   - Floor: "Floor_3"
   - Last modified: "2024-01-15"

### Step 4: Claude Reasoning

Claude 3.5 Sonnet receives the Briefcase and reasons:

**Example Reasoning:**
```
Wall_A increased by 100 sqft.
Cost impact: 100 sqft × $10/sqft = $1,000
Business rule: Changes over $500 require approval.
Recommendation: Flag for human approval.
Confidence: High (blueprint clearly shows dimension change).
```

### Step 5: The "Dispatcher" (Action Execution)

Claude returns a structured Function Call JSON:

```json
{
  "action_type": "flag_for_approval",
  "asset_id": "Wall_A",
  "delta": {
    "quantity_change": 100,
    "cost_impact": 1000
  },
  "reasoning": "Concrete increased by 100sqft. Exceeds $500 threshold.",
  "requires_human": true,
  "confidence_score": 0.95,
  "linked_budget_code": "B47"
}
```

**Dispatcher Actions:**
- If `requires_human: false` → Update `budget_state.json` automatically
- If `requires_human: true` → Write to approval queue, send notification

---

## 4. TECHNICAL STACK

### Core Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Ingestion** | Reducto.ai or Unstructured.io | High-fidelity PDF-to-JSON parsing |
| **Ontology** | Neo4j Community Edition | Graph database for Digital Twin |
| **Reasoning** | Claude 3.5 Sonnet (Anthropic API) | Stateless reasoning engine |
| **Orchestration** | Python 3.11 | Dispatcher and pipeline logic |
| **Containerization** | Docker Compose | Local development environment |

### Why These Choices?

**Neo4j (Graph Database):**
- **Business Reason:** Construction is inherently relational (walls belong to floors, floors belong to buildings, changes affect budgets)
- **Technical Reason:** Cypher queries can traverse relationships in milliseconds, giving instant "blast radius" analysis
- **Example:** "Show me all budget line items affected by changes to Floor 3" is a single graph traversal

**Claude 3.5 Sonnet:**
- **Business Reason:** Need reasoning about ambiguous changes, not just data transformation
- **Technical Reason:** Function calling capability + 200k context window allows entire state comparison
- **Model Agnostic Design:** The "brain" lives in Neo4j, so we can swap LLMs without data migration

**Docker Compose:**
- **Business Reason:** Easy to demo and hand off to other developers
- **Technical Reason:** Consistent environment across machines, no "works on my machine" issues

---

## 5. SPRINT SCOPE & TIMELINE

### What We ARE Building (Week 1)

✅ **Unidirectional Pipeline:** Document Upload → Parse → State Check → Reason → Action
✅ **Synthetic Mock Data:** JSON files representing "before" and "after" blueprint states
✅ **Local Environment:** Docker Compose with Neo4j + Python services
✅ **Mock Budget API:** Simple JSON file read/write to simulate budget system
✅ **End-to-End Demo:** Prove the concept works with sample data

### What We Are NOT Building (Out of Scope)

❌ Bi-directional syncing with real construction software (Procore, Autodesk)
❌ Real-time webhook monitoring of document changes
❌ Multi-user authentication and permissions
❌ Production deployment infrastructure (AWS/GCP)
❌ Advanced error handling and retry logic
❌ Full parser comparison (we'll pick one and move forward)

### 7-Day Roadmap

| Day | Focus Area | Deliverables |
|-----|-----------|--------------|
| **Day 1** | Environment & Schema | `docker-compose.yml`, `requirements.txt`, Cypher init scripts, project structure |
| **Day 2** | Ingestion R&D | Parser integration (Unstructured.io or Reducto), sample PDF processing |
| **Day 3** | Neo4j Logic | "Stateful Upsert" functions, delta calculation, query patterns |
| **Day 4** | Context Assembly | "Briefcase of Truth" prompt engineering, template system |
| **Day 5** | Claude Integration | Function calling loop, Dispatcher logic, Action JSON generation |
| **Day 6** | End-to-End Testing | Full pipeline test with multiple scenarios, logging |
| **Day 7** | Cleanup & Demo | Documentation, demo script, known issues list |

---

## 6. IMPLEMENTATION SPECIFICATIONS

### Development Environment

**Technology Stack:**
- **Runtime:** Python 3.11
- **Database:** Neo4j Community Edition (latest)
- **Container Orchestration:** Docker Compose
- **API Access:** Direct Anthropic API (not AWS Bedrock for Week 1)

**Environment Structure:**
```
context-engine-mvp/
├── docker-compose.yml          # Container orchestration
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variable template
├── README.md                  # Setup instructions
├── data/
│   ├── mock_blueprints/       # Synthetic JSON data
│   │   ├── before.json        # Initial state
│   │   └── after.json         # Changed state
│   └── budget_state.json      # Mock budget API storage
├── neo4j/
│   ├── init_schema.cypher     # Graph schema initialization
│   └── sample_data.cypher     # Sample data for testing
├── src/
│   ├── ingestion/             # PDF parsing module
│   ├── librarian/             # Neo4j query logic
│   ├── briefcase/             # Context assembly
│   ├── reasoner/              # Claude API integration
│   └── dispatcher/            # Action execution
└── tests/
    └── test_pipeline.py       # Integration tests
```

### Data Models

#### Neo4j Graph Schema

**Node Types:**

1. **Project**
```cypher
(:Project {
  id: STRING,              // e.g., "proj_001"
  name: STRING,            // e.g., "Office Building Downtown"
  budget_total: FLOAT,     // e.g., 5000000.00
  start_date: DATE,
  status: STRING           // e.g., "active"
})
```

2. **Floor**
```cypher
(:Floor {
  id: STRING,              // e.g., "floor_3"
  level: INTEGER,          // e.g., 3
  area_sqft: FLOAT,
  project_id: STRING       // Foreign key reference
})
```

3. **Object** (Physical Assets)
```cypher
(:Object {
  id: STRING,              // e.g., "Wall_A"
  type: STRING,            // e.g., "Wall", "Beam", "HVAC"
  material: STRING,        // e.g., "Concrete", "Steel"
  quantity: FLOAT,         // e.g., 500
  unit: STRING,            // e.g., "sqft", "linear_ft"
  cost_per_unit: FLOAT,    // e.g., 10.00
  last_updated: DATETIME
})
```

4. **LineItem** (Budget Entries)
```cypher
(:LineItem {
  id: STRING,              // e.g., "B47"
  code: STRING,            // e.g., "03-30-00" (MasterFormat)
  description: STRING,     // e.g., "Cast-in-Place Concrete"
  allocated_budget: FLOAT, // e.g., 50000.00
  spent_to_date: FLOAT,    // e.g., 30000.00
  contingency: FLOAT       // e.g., 5000.00
})
```

5. **Vendor**
```cypher
(:Vendor {
  id: STRING,              // e.g., "vendor_concrete_co"
  name: STRING,            // e.g., "ConcreteCo Inc"
  rate_per_unit: FLOAT,    // e.g., 10.00
  material_type: STRING    // e.g., "Concrete"
})
```

**Relationship Types:**

```cypher
// Hierarchy
(:Floor)-[:BELONGS_TO]->(:Project)
(:Object)-[:LOCATED_ON]->(:Floor)

// Financial Impact
(:Object)-[:INFLUENCES]->(:LineItem)
(:LineItem)-[:SOURCED_FROM]->(:Vendor)

// Change Tracking
(:Object)-[:CHANGED_FROM {
  previous_quantity: FLOAT,
  change_date: DATETIME,
  change_reason: STRING
}]->(:Object)
```

#### Action JSON Schema (Claude Output)

**Structure:**
```json
{
  "action_type": "update_budget" | "flag_for_approval",
  "asset_id": "Wall_A",
  "delta": {
    "quantity_change": 100,
    "cost_impact": 1000.00
  },
  "reasoning": "Concrete increased by 100sqft. Exceeds $500 threshold.",
  "requires_human": true | false,
  "confidence_score": 0.0-1.0,
  "linked_budget_code": "B47"
}
```

**Field Definitions:**

- `action_type`: The recommended action
- `asset_id`: The graph node ID that changed
- `delta.quantity_change`: Numeric change in units
- `delta.cost_impact`: Calculated budget impact in dollars
- `reasoning`: Human-readable explanation of decision
- `requires_human`: Boolean flag for approval requirement
- `confidence_score`: 0.0-1.0 representing Claude's certainty
- `linked_budget_code`: The budget line item ID from Neo4j

#### Mock Budget API Schema

**File:** `data/budget_state.json`

**Structure:**
```json
{
  "project_id": "proj_001",
  "last_updated": "2024-01-20T10:30:00Z",
  "line_items": [
    {
      "code": "B47",
      "description": "Cast-in-Place Concrete",
      "allocated": 50000.00,
      "spent": 30000.00,
      "pending_changes": [
        {
          "asset_id": "Wall_A",
          "delta": 1000.00,
          "status": "pending_approval",
          "timestamp": "2024-01-20T10:25:00Z"
        }
      ]
    }
  ]
}
```

#### Synthetic Mock Data (Blueprint Changes)

**File:** `data/mock_blueprints/before.json`
```json
{
  "blueprint_id": "BP_001_rev_A",
  "project_id": "proj_001",
  "revision": "A",
  "date": "2024-01-01",
  "assets": [
    {
      "id": "Wall_A",
      "type": "Wall",
      "material": "Concrete",
      "quantity": 400,
      "unit": "sqft",
      "floor": "floor_3",
      "dimensions": {
        "length": 40,
        "height": 10
      }
    },
    {
      "id": "Beam_B1",
      "type": "Beam",
      "material": "Steel",
      "quantity": 50,
      "unit": "linear_ft",
      "floor": "floor_3"
    }
  ]
}
```

**File:** `data/mock_blueprints/after.json`
```json
{
  "blueprint_id": "BP_001_rev_B",
  "project_id": "proj_001",
  "revision": "B",
  "date": "2024-01-15",
  "assets": [
    {
      "id": "Wall_A",
      "type": "Wall",
      "material": "Concrete",
      "quantity": 500,
      "unit": "sqft",
      "floor": "floor_3",
      "dimensions": {
        "length": 50,
        "height": 10
      }
    },
    {
      "id": "Beam_B1",
      "type": "Beam",
      "material": "Steel",
      "quantity": 50,
      "unit": "linear_ft",
      "floor": "floor_3"
    },
    {
      "id": "HVAC_Unit_1",
      "type": "HVAC",
      "material": "Commercial_AC",
      "quantity": 1,
      "unit": "unit",
      "floor": "floor_3"
    }
  ]
}
```

**Key Changes in Mock Data:**
1. Wall_A: 400 → 500 sqft (quantity increase)
2. HVAC_Unit_1: New asset added

---

## 7. DAY 1 DELIVERABLES

### Task 1: Docker Compose Configuration

**Create:** `docker-compose.yml`

**Requirements:**
- Neo4j Community Edition service
- Expose Neo4j browser on port 7474
- Expose Bolt protocol on port 7687
- Python service container
- Shared volume for data persistence
- Environment variables for API keys

**Expected Services:**
1. `neo4j` - Graph database
2. `context-engine` - Python application

### Task 2: Python Dependencies

**Create:** `requirements.txt`

**Required Packages:**
- `neo4j` - Official Neo4j Python driver
- `anthropic` - Claude API client
- `python-dotenv` - Environment variable management
- `pydantic` - Data validation
- `requests` - HTTP client (for mock API calls)
- `pytest` - Testing framework

### Task 3: Neo4j Initialization

**Create:** `neo4j/init_schema.cypher`

**Requirements:**
- Create constraints for unique IDs
- Create indexes for performance
- Define node labels
- Set up initial relationships

**Expected Constraints:**
```cypher
CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT floor_id IF NOT EXISTS FOR (f:Floor) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT object_id IF NOT EXISTS FOR (o:Object) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT lineitem_id IF NOT EXISTS FOR (l:LineItem) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT vendor_id IF NOT EXISTS FOR (v:Vendor) REQUIRE v.id IS UNIQUE;
```

**Create:** `neo4j/sample_data.cypher`

**Requirements:**
- Populate graph with initial project data
- Create sample objects matching `before.json`
- Link objects to floors and line items
- Seed budget line items

### Task 4: Project Structure

**Create:** Basic Python module structure with placeholder files

**Directory Structure:**
```
src/
├── __init__.py
├── ingestion/
│   ├── __init__.py
│   └── parser.py              # PDF parsing logic
├── librarian/
│   ├── __init__.py
│   ├── graph_client.py        # Neo4j connection
│   └── state_queries.py       # Cypher query functions
├── briefcase/
│   ├── __init__.py
│   ├── assembler.py           # Context construction
│   └── templates.py           # Prompt templates
├── reasoner/
│   ├── __init__.py
│   └── claude_client.py       # Claude API integration
└── dispatcher/
    ├── __init__.py
    ├── actions.py             # Action execution logic
    └── budget_api.py          # Mock budget API client
```

### Task 5: Environment Configuration

**Create:** `.env.example`

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# Anthropic API
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Application Settings
LOG_LEVEL=INFO
MOCK_MODE=true
BUDGET_API_FILE=./data/budget_state.json
```

---

## 8. THE "BRIEFCASE OF TRUTH" TEMPLATE

### Context Assembly Logic

**Purpose:** Construct a rich, structured prompt for Claude that contains all necessary context to make a reasoned decision.

**Template Structure:**

```python
BRIEFCASE_TEMPLATE = """
You are a construction budget analyst. You have been given information about a blueprint change.

# CURRENT STATE (from Graph Database)
Asset: {asset_id}
Type: {asset_type}
Material: {material}
Current Quantity: {current_quantity} {unit}
Current Cost per Unit: ${cost_per_unit}
Current Budget Allocation: ${current_budget}
Linked Budget Code: {budget_code}
Linked Vendor: {vendor_name}
Last Updated: {last_updated}

# DETECTED CHANGE (from New Blueprint)
New Quantity: {new_quantity} {unit}
Change Delta: {quantity_delta} {unit}
Calculated Cost Impact: ${cost_impact}

# BUSINESS RULES
- Concrete costs ${cost_per_unit} per {unit}
- Changes exceeding ${approval_threshold} require human approval
- Maximum contingency available: ${contingency_available}

# YOUR TASK
Analyze this change and provide a recommendation using the following function call format:

Function: recommend_action
Parameters:
  - action_type: "update_budget" or "flag_for_approval"
  - requires_human: true or false
  - confidence_score: 0.0 to 1.0
  - reasoning: explanation of your decision

Consider:
1. Is the cost impact within acceptable thresholds?
2. Is there sufficient contingency to cover this change?
3. Is this change consistent with typical construction modifications?
4. What is your confidence level in the detected change?
"""
```

---

## 9. TESTING SCENARIOS

### Scenario 1: Minor Change (Auto-Approve)
- **Input:** Wall_A increases from 400 to 450 sqft
- **Cost Impact:** $500
- **Expected Action:** `update_budget` (at threshold, auto-approve)
- **Confidence:** High (>0.9)

### Scenario 2: Major Change (Flag for Approval)
- **Input:** Wall_A increases from 400 to 600 sqft
- **Cost Impact:** $2,000
- **Expected Action:** `flag_for_approval`
- **Reasoning:** Exceeds $500 threshold

### Scenario 3: New Asset Added
- **Input:** HVAC_Unit_1 appears in new blueprint
- **Cost Impact:** Unknown (no cost_per_unit in graph)
- **Expected Action:** `flag_for_approval`
- **Reasoning:** New asset requires budget allocation review

### Scenario 4: Asset Removed
- **Input:** Beam_B1 disappears from new blueprint
- **Cost Impact:** -$X (cost savings)
- **Expected Action:** `flag_for_approval`
- **Reasoning:** Removal requires architectural review

---

## 10. SUCCESS METRICS

### Technical Metrics
- ✅ Pipeline processes blueprint changes in <5 seconds
- ✅ Neo4j queries return in <100ms
- ✅ Claude API calls complete in <3 seconds
- ✅ Zero data loss in state transitions
- ✅ 100% of test scenarios pass

### Business Metrics
- ✅ Can detect quantity changes with >90% accuracy
- ✅ Correctly flags changes requiring approval
- ✅ Provides reasoning that a non-technical person can understand
- ✅ Successfully demonstrates "lag elimination" (instant budget impact visibility)

---

## 11. KEY DESIGN PRINCIPLES

### 1. State Over Search
**Principle:** The graph knows the *exact* current state, not just "relevant documents"

**Implementation:**
- Every asset has a current state in Neo4j
- Deltas are calculated by comparing old vs new
- No fuzzy matching or semantic search needed for state

### 2. Explicit Relationships
**Principle:** Physical relationships are modeled as graph edges

**Example:**
```cypher
MATCH (wall:Object {id: 'Wall_A'})-[:LOCATED_ON]->(floor:Floor)
      -[:BELONGS_TO]->(project:Project)
MATCH (wall)-[:INFLUENCES]->(budget:LineItem)
      -[:SOURCED_FROM]->(vendor:Vendor)
RETURN wall, floor, project, budget, vendor
```

This single query gives the complete "blast radius" of a change.

### 3. Model Agnostic
**Principle:** The intelligence lives in the graph structure, not the LLM

**Benefits:**
- Can swap Claude for GPT-5, Gemini, or Llama
- Graph schema persists across model changes
- Relationships encoded in data, not in prompts

### 4. Human-in-the-Loop
**Principle:** Automation with oversight, not full autonomy

**Implementation:**
- Confidence scores guide when humans review
- Reasoning is always provided for auditability
- Approval thresholds are configurable business rules

---

## 12. KNOWN LIMITATIONS & FUTURE WORK

### MVP Limitations
1. **Single Project:** Only handles one project at a time
2. **Synthetic Data:** Not tested on real construction blueprints
3. **Mock Budget API:** No real integration with Procore/Autodesk
4. **No Rollback:** Changes are not easily reversible
5. **Limited Error Handling:** Assumes perfect data quality

### Post-MVP Roadmap
- **Week 2:** Real PDF parsing with Reducto/Unstructured
- **Week 3:** Multi-project support and project switching
- **Week 4:** Procore API integration
- **Week 5:** Change history and rollback capability
- **Week 6:** Real-time monitoring with webhooks
- **Month 2:** Production deployment on AWS

---

## 13. GETTING STARTED (For Claude Code)

### Your Mission

You are implementing the **Blue-to-Budget Pipeline** for a construction context engine. This is a focused, 7-day sprint to prove the concept works.

### Day 1 Instructions

Please create the following files:

1. **`docker-compose.yml`**
   - Neo4j service with proper configuration
   - Python service (can be empty for now, we'll build it out)
   - Shared volumes for data persistence

2. **`requirements.txt`**
   - All necessary Python packages
   - Pin versions for reproducibility

3. **`neo4j/init_schema.cypher`**
   - Constraints for node IDs
   - Indexes for performance
   - Initial schema setup

4. **`neo4j/sample_data.cypher`**
   - Sample project, floor, objects matching `before.json`
   - Sample line items and vendors
   - Relationships between entities

5. **Project Directory Structure**
   - Create all folders and `__init__.py` files
   - Add placeholder files for each module

6. **`.env.example`**
   - Template for environment variables
   - Comments explaining each variable

7. **`README.md`**
   - Quick start instructions
   - How to run the environment
   - Testing instructions

### Coding Standards

- **Type Hints:** Use Python type hints everywhere
- **Docstrings:** Google-style docstrings for all functions
- **Error Handling:** Explicit try/except blocks
- **Logging:** Use Python `logging` module
- **Configuration:** All magic numbers in constants or config files

### Questions to Clarify

If anything is ambiguous, make reasonable assumptions and document them in code comments prefixed with `# ASSUMPTION:`.

### Let's Build

Start with Day 1 deliverables. Once that's complete and the environment is running, we'll move to Day 2: ingestion and parsing logic.

---

## 14. GLOSSARY

**Blue:** The blueprint or design documents
**Budget:** The financial allocation for construction work
**Digital Twin:** A real-time graph representation of physical construction assets
**Briefcase of Truth:** The contextual prompt given to Claude containing current state, changes, and business rules
**Dispatcher:** The Python service that executes actions based on Claude's recommendations
**Librarian:** The Neo4j query layer that knows the current state
**Ontology:** The graph schema defining relationships between construction entities
**Stateful Upsert:** Updating the graph only after comparing current vs new state
**Delta:** The calculated difference between old and new values

---

**End of Context Document**
