// =============================================================================
// Context Engine MVP - Sample Data Population
// =============================================================================
// This script populates the graph database with initial test data
// Data corresponds to the "before.json" state from the MVP brief
//
// The data represents:
// - 1 Project: Office Building Downtown
// - 1 Floor: Floor 3
// - 2 Objects: Wall_A (400 sqft concrete), Beam_B1 (50 linear ft steel)
// - 2 Budget LineItems with vendors
// =============================================================================

// -----------------------------------------------------------------------------
// CLEAR EXISTING DATA (Optional - use for clean re-initialization)
// -----------------------------------------------------------------------------
// Uncomment to delete all existing nodes and relationships
// WARNING: This will delete ALL data in the database
// MATCH (n) DETACH DELETE n;

// -----------------------------------------------------------------------------
// CREATE PROJECT
// -----------------------------------------------------------------------------
CREATE (p:Project {
  id: 'proj_001',
  name: 'Office Building Downtown',
  budget_total: 5000000.00,
  start_date: date('2024-01-01'),
  status: 'active',
  created_at: datetime('2024-01-01T08:00:00Z')
});

// -----------------------------------------------------------------------------
// CREATE FLOOR
// -----------------------------------------------------------------------------
CREATE (f:Floor {
  id: 'floor_3',
  level: 3,
  area_sqft: 10000.0,
  project_id: 'proj_001',
  created_at: datetime('2024-01-01T08:00:00Z')
});

// -----------------------------------------------------------------------------
// CREATE OBJECTS (Physical Assets)
// -----------------------------------------------------------------------------
// Wall_A - Concrete wall (400 sqft)
CREATE (o1:Object {
  id: 'Wall_A',
  type: 'Wall',
  material: 'Concrete',
  quantity: 400.0,
  unit: 'sqft',
  cost_per_unit: 10.00,
  total_cost: 4000.00,
  last_updated: datetime('2024-01-01T08:00:00Z'),
  dimensions: '{"length": 40, "height": 10}'
});

// Beam_B1 - Steel beam (50 linear ft)
CREATE (o2:Object {
  id: 'Beam_B1',
  type: 'Beam',
  material: 'Steel',
  quantity: 50.0,
  unit: 'linear_ft',
  cost_per_unit: 25.00,
  total_cost: 1250.00,
  last_updated: datetime('2024-01-01T08:00:00Z')
});

// -----------------------------------------------------------------------------
// CREATE BUDGET LINE ITEMS
// -----------------------------------------------------------------------------
// LineItem for Concrete work
CREATE (li1:LineItem {
  id: 'B47',
  code: '03-30-00',
  description: 'Cast-in-Place Concrete',
  allocated_budget: 50000.00,
  spent_to_date: 30000.00,
  contingency: 5000.00,
  remaining: 20000.00,
  created_at: datetime('2024-01-01T08:00:00Z')
});

// LineItem for Structural Steel
CREATE (li2:LineItem {
  id: 'B48',
  code: '05-12-00',
  description: 'Structural Steel Framing',
  allocated_budget: 75000.00,
  spent_to_date: 45000.00,
  contingency: 7500.00,
  remaining: 30000.00,
  created_at: datetime('2024-01-01T08:00:00Z')
});

// -----------------------------------------------------------------------------
// CREATE VENDORS
// -----------------------------------------------------------------------------
// Concrete vendor
CREATE (v1:Vendor {
  id: 'vendor_concrete_co',
  name: 'ConcreteCo Inc',
  rate_per_unit: 10.00,
  material_type: 'Concrete',
  contact_email: 'sales@concreteco.example.com',
  phone: '555-0100',
  created_at: datetime('2024-01-01T08:00:00Z')
});

// Steel vendor
CREATE (v2:Vendor {
  id: 'vendor_steel_works',
  name: 'SteelWorks LLC',
  rate_per_unit: 25.00,
  material_type: 'Steel',
  contact_email: 'orders@steelworks.example.com',
  phone: '555-0200',
  created_at: datetime('2024-01-01T08:00:00Z')
});

// -----------------------------------------------------------------------------
// CREATE RELATIONSHIPS
// -----------------------------------------------------------------------------
// Connect Floor to Project
MATCH (f:Floor {id: 'floor_3'})
MATCH (p:Project {id: 'proj_001'})
CREATE (f)-[:BELONGS_TO]->(p);

// Connect Objects to Floor
MATCH (o1:Object {id: 'Wall_A'})
MATCH (f:Floor {id: 'floor_3'})
CREATE (o1)-[:LOCATED_ON]->(f);

MATCH (o2:Object {id: 'Beam_B1'})
MATCH (f:Floor {id: 'floor_3'})
CREATE (o2)-[:LOCATED_ON]->(f);

// Connect Objects to Budget LineItems
MATCH (o1:Object {id: 'Wall_A'})
MATCH (li1:LineItem {id: 'B47'})
CREATE (o1)-[:INFLUENCES {
  impact_factor: 1.0,
  last_calculated: datetime('2024-01-01T08:00:00Z')
}]->(li1);

MATCH (o2:Object {id: 'Beam_B1'})
MATCH (li2:LineItem {id: 'B48'})
CREATE (o2)-[:INFLUENCES {
  impact_factor: 1.0,
  last_calculated: datetime('2024-01-01T08:00:00Z')
}]->(li2);

// Connect LineItems to Vendors
MATCH (li1:LineItem {id: 'B47'})
MATCH (v1:Vendor {id: 'vendor_concrete_co'})
CREATE (li1)-[:SOURCED_FROM {
  contract_start: date('2024-01-01'),
  contract_end: date('2024-12-31'),
  payment_terms: 'Net 30'
}]->(v1);

MATCH (li2:LineItem {id: 'B48'})
MATCH (v2:Vendor {id: 'vendor_steel_works'})
CREATE (li2)-[:SOURCED_FROM {
  contract_start: date('2024-01-01'),
  contract_end: date('2024-12-31'),
  payment_terms: 'Net 30'
}]->(v2);

// =============================================================================
// DATA VERIFICATION QUERIES
// =============================================================================
// Run these queries to verify the data was loaded correctly

// Count all nodes
// MATCH (n) RETURN labels(n) as NodeType, count(n) as Count;

// Show the complete graph structure
// MATCH (p:Project)<-[:BELONGS_TO]-(f:Floor)<-[:LOCATED_ON]-(o:Object)
// MATCH (o)-[:INFLUENCES]->(li:LineItem)-[:SOURCED_FROM]->(v:Vendor)
// RETURN p, f, o, li, v;

// Show all Wall_A relationships (for testing the main scenario)
// MATCH (o:Object {id: 'Wall_A'})-[r]->(connected)
// RETURN o, type(r) as relationship_type, connected;

// Calculate current project budget allocation
// MATCH (p:Project {id: 'proj_001'})<-[:BELONGS_TO]-(f:Floor)<-[:LOCATED_ON]-(o:Object)
// MATCH (o)-[:INFLUENCES]->(li:LineItem)
// RETURN p.name as Project,
//        sum(o.total_cost) as TotalAssetCost,
//        sum(li.allocated_budget) as TotalBudgetAllocated,
//        sum(li.spent_to_date) as TotalSpent,
//        sum(li.remaining) as TotalRemaining;

// =============================================================================
// Sample Data Population Complete
// =============================================================================
// The database now contains:
// - 1 Project (Office Building Downtown)
// - 1 Floor (Floor 3)
// - 2 Objects (Wall_A: 400 sqft concrete, Beam_B1: 50 ft steel)
// - 2 Budget LineItems (Concrete: $50k allocated, Steel: $75k allocated)
// - 2 Vendors (ConcreteCo, SteelWorks)
// - All necessary relationships established
//
// Next step: Start the Python application to test the pipeline
// =============================================================================
