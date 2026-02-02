"""
State Queries Module

High-level queries for retrieving and comparing state from the Neo4j graph database.
Implements the "Librarian" logic for state management.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .graph_client import GraphClient

logger = logging.getLogger(__name__)


class StateQueries:
    """
    High-level interface for querying construction project state from Neo4j.
    Implements the "Librarian" pattern - knows the current state and can calculate deltas.
    """

    def __init__(self, graph_client: GraphClient):
        """
        Initialize StateQueries with a GraphClient.

        Args:
            graph_client: Connected GraphClient instance
        """
        self.client = graph_client
        logger.info("StateQueries initialized")

    def get_object_state(self, object_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a physical object from the graph.

        Args:
            object_id: Unique identifier for the object (e.g., 'Wall_A')

        Returns:
            Dictionary containing object properties and relationships, or None if not found
        """
        logger.info(f"Fetching state for object: {object_id}")

        query = """
        MATCH (obj:Object {id: $object_id})
        OPTIONAL MATCH (obj)-[:LOCATED_ON]->(floor:Floor)
        OPTIONAL MATCH (obj)-[:INFLUENCES]->(lineitem:LineItem)
        OPTIONAL MATCH (lineitem)-[:SOURCED_FROM]->(vendor:Vendor)
        RETURN obj, floor, lineitem, vendor
        """

        results = self.client.execute_query(query, {'object_id': object_id})

        if not results or not results[0].get('obj'):
            logger.warning(f"Object not found: {object_id}")
            return None

        result = results[0]
        state = {
            'object': dict(result['obj']) if result.get('obj') else None,
            'floor': dict(result['floor']) if result.get('floor') else None,
            'lineitem': dict(result['lineitem']) if result.get('lineitem') else None,
            'vendor': dict(result['vendor']) if result.get('vendor') else None
        }

        logger.info(f"Successfully retrieved state for {object_id}")
        return state

    def calculate_delta(
        self,
        object_id: str,
        new_quantity: float,
        new_material: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate the delta (change) between current state and new values.

        Args:
            object_id: Object identifier
            new_quantity: New quantity value
            new_material: Optional new material type

        Returns:
            Dictionary containing delta information including cost impact
        """
        logger.info(f"Calculating delta for {object_id}")

        current_state = self.get_object_state(object_id)

        if not current_state or not current_state['object']:
            return {
                'exists': False,
                'object_id': object_id,
                'is_new_asset': True,
                'new_quantity': new_quantity,
                'new_material': new_material,
                'cost_impact': None,
                'message': 'Asset does not exist in current state (new asset)'
            }

        obj = current_state['object']
        current_quantity = obj.get('quantity', 0)
        current_material = obj.get('material')
        cost_per_unit = obj.get('cost_per_unit', 0)

        quantity_delta = new_quantity - current_quantity
        cost_impact = quantity_delta * cost_per_unit

        material_changed = (new_material is not None and
                          new_material != current_material)

        delta = {
            'exists': True,
            'object_id': object_id,
            'is_new_asset': False,
            'current_quantity': current_quantity,
            'new_quantity': new_quantity,
            'quantity_delta': quantity_delta,
            'current_material': current_material,
            'new_material': new_material,
            'material_changed': material_changed,
            'cost_per_unit': cost_per_unit,
            'cost_impact': cost_impact,
            'current_total_cost': obj.get('total_cost', 0),
            'new_total_cost': new_quantity * cost_per_unit,
            'lineitem': current_state.get('lineitem'),
            'vendor': current_state.get('vendor')
        }

        logger.info(f"Delta calculated: quantity_delta={quantity_delta}, "
                   f"cost_impact=${cost_impact:.2f}")
        return delta

    def get_project_state(self, project_id: str) -> Dict[str, Any]:
        """
        Get complete state of a project including all objects and budget info.

        Args:
            project_id: Project identifier

        Returns:
            Dictionary containing full project state
        """
        logger.info(f"Fetching complete state for project: {project_id}")

        query = """
        MATCH (p:Project {id: $project_id})
        OPTIONAL MATCH (p)<-[:BELONGS_TO]-(f:Floor)
        OPTIONAL MATCH (f)<-[:LOCATED_ON]-(o:Object)
        OPTIONAL MATCH (o)-[:INFLUENCES]->(li:LineItem)
        RETURN p,
               collect(DISTINCT f) as floors,
               collect(DISTINCT o) as objects,
               collect(DISTINCT li) as lineitems
        """

        results = self.client.execute_query(query, {'project_id': project_id})

        if not results or not results[0].get('p'):
            logger.warning(f"Project not found: {project_id}")
            return {}

        result = results[0]
        state = {
            'project': dict(result['p']) if result.get('p') else None,
            'floors': [dict(f) for f in result.get('floors', []) if f],
            'objects': [dict(o) for o in result.get('objects', []) if o],
            'lineitems': [dict(li) for li in result.get('lineitems', []) if li]
        }

        logger.info(f"Project state retrieved: {len(state['objects'])} objects, "
                   f"{len(state['lineitems'])} line items")
        return state

    def upsert_object(
        self,
        object_id: str,
        object_data: Dict[str, Any],
        floor_id: str
    ) -> bool:
        """
        Insert or update an object in the graph (stateful upsert).

        Args:
            object_id: Object identifier
            object_data: Dictionary containing object properties
            floor_id: Floor identifier where object is located

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Upserting object: {object_id}")

        # ASSUMPTION: If object exists, we update it; otherwise, create it
        query = """
        MERGE (obj:Object {id: $object_id})
        SET obj.type = $type,
            obj.material = $material,
            obj.quantity = $quantity,
            obj.unit = $unit,
            obj.cost_per_unit = $cost_per_unit,
            obj.total_cost = $total_cost,
            obj.last_updated = datetime()
        WITH obj
        MATCH (floor:Floor {id: $floor_id})
        MERGE (obj)-[:LOCATED_ON]->(floor)
        RETURN obj
        """

        try:
            total_cost = object_data['quantity'] * object_data.get('cost_per_unit', 0)

            params = {
                'object_id': object_id,
                'type': object_data.get('type'),
                'material': object_data.get('material'),
                'quantity': object_data.get('quantity'),
                'unit': object_data.get('unit'),
                'cost_per_unit': object_data.get('cost_per_unit', 0),
                'total_cost': total_cost,
                'floor_id': floor_id
            }

            self.client.execute_write_transaction(query, params)
            logger.info(f"Successfully upserted object: {object_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to upsert object {object_id}: {e}")
            return False

    def get_blast_radius(self, object_id: str) -> Dict[str, Any]:
        """
        Get the "blast radius" - all entities affected by a change to this object.

        This shows which budget items, vendors, and other objects are impacted.

        Args:
            object_id: Object identifier

        Returns:
            Dictionary containing all affected entities
        """
        logger.info(f"Calculating blast radius for: {object_id}")

        query = """
        MATCH (obj:Object {id: $object_id})-[:LOCATED_ON]->(floor:Floor)
              -[:BELONGS_TO]->(project:Project)
        MATCH (obj)-[:INFLUENCES]->(lineitem:LineItem)
        OPTIONAL MATCH (lineitem)-[:SOURCED_FROM]->(vendor:Vendor)
        OPTIONAL MATCH (floor)<-[:LOCATED_ON]-(related_obj:Object)
        WHERE related_obj.id <> $object_id
        RETURN obj, floor, project, lineitem, vendor,
               collect(DISTINCT related_obj) as related_objects
        """

        results = self.client.execute_query(query, {'object_id': object_id})

        if not results:
            logger.warning(f"No blast radius found for: {object_id}")
            return {}

        result = results[0]
        blast_radius = {
            'object': dict(result['obj']) if result.get('obj') else None,
            'floor': dict(result['floor']) if result.get('floor') else None,
            'project': dict(result['project']) if result.get('project') else None,
            'lineitem': dict(result['lineitem']) if result.get('lineitem') else None,
            'vendor': dict(result['vendor']) if result.get('vendor') else None,
            'related_objects': [dict(o) for o in result.get('related_objects', []) if o]
        }

        logger.info(f"Blast radius calculated: affects {len(blast_radius['related_objects'])} "
                   f"related objects")
        return blast_radius

    def get_all_objects(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all objects, optionally filtered by project.

        Args:
            project_id: Optional project identifier to filter by

        Returns:
            List of object dictionaries
        """
        if project_id:
            query = """
            MATCH (p:Project {id: $project_id})<-[:BELONGS_TO]-(f:Floor)
                  <-[:LOCATED_ON]-(obj:Object)
            RETURN obj
            ORDER BY obj.id
            """
            results = self.client.execute_query(query, {'project_id': project_id})
        else:
            query = """
            MATCH (obj:Object)
            RETURN obj
            ORDER BY obj.id
            """
            results = self.client.execute_query(query)

        objects = [dict(r['obj']) for r in results if r.get('obj')]
        logger.info(f"Retrieved {len(objects)} objects")
        return objects
