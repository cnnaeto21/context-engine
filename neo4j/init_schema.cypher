// =============================================================================
// Context Engine MVP - Neo4j Schema Initialization
// =============================================================================
// This script creates the graph database schema including:
// - Unique constraints for node IDs
// - Indexes for performance optimization
// - Node labels and relationship types
//
// Execute this script after Neo4j starts for the first time
// =============================================================================

// -----------------------------------------------------------------------------
// DROP EXISTING CONSTRAINTS (for clean re-initialization)
// -----------------------------------------------------------------------------
// Uncomment these lines if you need to reset the schema
// DROP CONSTRAINT project_id IF EXISTS;
// DROP CONSTRAINT floor_id IF EXISTS;
// DROP CONSTRAINT object_id IF EXISTS;
// DROP CONSTRAINT lineitem_id IF EXISTS;
// DROP CONSTRAINT vendor_id IF EXISTS;

// -----------------------------------------------------------------------------
// CREATE UNIQUE CONSTRAINTS
// -----------------------------------------------------------------------------
// These constraints ensure that each node has a unique ID
// and automatically create an index for fast lookups

// Project nodes must have unique IDs
CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

// Floor nodes must have unique IDs
CREATE CONSTRAINT floor_id IF NOT EXISTS
FOR (f:Floor) REQUIRE f.id IS UNIQUE;

// Object nodes (physical assets) must have unique IDs
CREATE CONSTRAINT object_id IF NOT EXISTS
FOR (o:Object) REQUIRE o.id IS UNIQUE;

// LineItem nodes (budget entries) must have unique IDs
CREATE CONSTRAINT lineitem_id IF NOT EXISTS
FOR (l:LineItem) REQUIRE l.id IS UNIQUE;

// Vendor nodes must have unique IDs
CREATE CONSTRAINT vendor_id IF NOT EXISTS
FOR (v:Vendor) REQUIRE v.id IS UNIQUE;

// -----------------------------------------------------------------------------
// CREATE INDEXES FOR PERFORMANCE
// -----------------------------------------------------------------------------
// These indexes speed up common queries

// Index on Object type for filtering by asset type
CREATE INDEX object_type_index IF NOT EXISTS
FOR (o:Object) ON (o.type);

// Index on Object material for material-based queries
CREATE INDEX object_material_index IF NOT EXISTS
FOR (o:Object) ON (o.material);

// Index on LineItem code for budget code lookups
CREATE INDEX lineitem_code_index IF NOT EXISTS
FOR (l:LineItem) ON (l.code);

// Index on Vendor material_type for vendor filtering
CREATE INDEX vendor_material_index IF NOT EXISTS
FOR (v:Vendor) ON (v.material_type);

// Index on Project status for active project queries
CREATE INDEX project_status_index IF NOT EXISTS
FOR (p:Project) ON (p.status);

// Index on Object last_updated for temporal queries
CREATE INDEX object_updated_index IF NOT EXISTS
FOR (o:Object) ON (o.last_updated);

// -----------------------------------------------------------------------------
// SCHEMA VALIDATION QUERIES
// -----------------------------------------------------------------------------
// These queries can be used to verify the schema was created correctly

// Show all constraints
// SHOW CONSTRAINTS;

// Show all indexes
// SHOW INDEXES;

// =============================================================================
// Schema Definition Complete
// =============================================================================
// Next step: Run sample_data.cypher to populate the database with test data
// =============================================================================
