"""
Briefcase Templates

Prompt templates for constructing Claude's "Briefcase of Truth".
"""

from typing import Dict, Any


class BriefcaseTemplates:
    """
    Template strings for Claude reasoning prompts.
    """

    @staticmethod
    def asset_change_template() -> str:
        """
        Template for analyzing an asset change (quantity or material modification).

        Returns:
            Formatted prompt template string
        """
        return """You are a construction budget analyst. You have been given information about a blueprint change.

# CURRENT STATE (from Graph Database)
Asset ID: {asset_id}
Type: {asset_type}
Material: {material}
Current Quantity: {current_quantity} {unit}
Current Cost per Unit: ${cost_per_unit:.2f}
Current Total Cost: ${current_total_cost:.2f}
Linked Budget Code: {budget_code}
Linked Vendor: {vendor_name}
Last Updated: {last_updated}

# DETECTED CHANGE (from New Blueprint)
New Quantity: {new_quantity} {unit}
Change Delta: {quantity_delta:+.2f} {unit}
Calculated Cost Impact: ${cost_impact:+.2f}
Material Changed: {material_changed}

# DATA QUALITY (from Parser)
Extraction Confidence: {extraction_confidence:.2f} (0.0-1.0)
Parser Source: {parser_source}
Data Trustworthiness: {data_trustworthiness}

# BUDGET CONTEXT
Budget Line Item: {budget_code} - {budget_description}
Allocated Budget: ${allocated_budget:.2f}
Spent to Date: ${spent_to_date:.2f}
Remaining Budget: ${remaining_budget:.2f}
Available Contingency: ${contingency:.2f}

# BUSINESS RULES
- {material} costs ${cost_per_unit:.2f} per {unit}
- Changes exceeding ${approval_threshold:.2f} require human approval
- Maximum contingency available: ${max_contingency:.2f}
- Minimum confidence threshold for auto-approval: {min_confidence_threshold}

# YOUR TASK
Analyze this change and provide a recommendation. Consider:
1. Is the cost impact within acceptable thresholds?
2. Is there sufficient budget to cover this change?
3. Is this change consistent with typical construction modifications?
4. How trustworthy is the extracted data? (Extraction confidence: {extraction_confidence:.2f})
5. What is your confidence level in the detected change?

**IMPORTANT**: Your confidence_score should account for BOTH:
- Your reasoning confidence (business logic)
- The extraction confidence from the parser (data quality)

If extraction confidence is low (<0.80), consider flagging for human review even if business logic seems sound.

Provide your recommendation using the recommend_action function with these parameters:
- action_type: "update_budget" or "flag_for_approval"
- requires_human: true or false
- confidence_score: 0.0 to 1.0 (combine your reasoning + extraction confidence)
- reasoning: clear explanation of your decision, including data quality concerns if any
"""

    @staticmethod
    def new_asset_template() -> str:
        """
        Template for analyzing a new asset addition.

        Returns:
            Formatted prompt template string
        """
        return """You are a construction budget analyst. A new asset has been detected in the blueprint.

# NEW ASSET DETECTED
Asset ID: {asset_id}
Type: {asset_type}
Material: {material}
Quantity: {quantity} {unit}
Floor: {floor_id}

# DATA QUALITY (from Parser)
Extraction Confidence: {extraction_confidence:.2f} (0.0-1.0)
Parser Source: {parser_source}
Data Trustworthiness: {data_trustworthiness}

# PROJECT CONTEXT
Project: {project_name}
Floor: {floor_name}
Blueprint Revision: {revision}
Date: {date}

# CURRENT BUDGET STATUS
Total Project Budget: ${project_budget:.2f}
Total Allocated: ${total_allocated:.2f}
Total Spent: ${total_spent:.2f}
Total Remaining: ${total_remaining:.2f}
Available Contingency: ${total_contingency:.2f}

# BUSINESS RULES
- New assets always require human review for budget allocation
- Maximum contingency available: ${max_contingency:.2f}
- Estimated cost per unit for {material}: ${estimated_cost_per_unit:.2f}

# YOUR TASK
Analyze this new asset and provide a recommendation. Consider:
1. Is this a typical asset for this type of construction project?
2. What is the likely budget impact?
3. Which budget line item should this be allocated to?
4. Does this indicate a significant scope change?
5. How trustworthy is the extracted data? (Extraction confidence: {extraction_confidence:.2f})

**IMPORTANT**: Your confidence_score should reflect the extraction confidence.
If extraction confidence is low, note this in your reasoning.

Provide your recommendation using the recommend_action function with these parameters:
- action_type: "flag_for_approval" (required for new assets)
- requires_human: true
- confidence_score: 0.0 to 1.0 (should reflect extraction confidence)
- reasoning: clear explanation including budget allocation recommendation and data quality assessment
"""

    @staticmethod
    def asset_removal_template() -> str:
        """
        Template for analyzing an asset removal.

        Returns:
            Formatted prompt template string
        """
        return """You are a construction budget analyst. An asset has been removed from the blueprint.

# REMOVED ASSET
Asset ID: {asset_id}
Type: {asset_type}
Material: {material}
Quantity: {quantity} {unit}
Cost per Unit: ${cost_per_unit:.2f}
Total Cost: ${total_cost:.2f}
Linked Budget Code: {budget_code}

# DATA QUALITY (from Parser)
Extraction Confidence: {extraction_confidence:.2f} (0.0-1.0)
Parser Source: {parser_source}

# BUDGET IMPACT
Potential Cost Savings: ${cost_savings:.2f}
Current Budget Line Item: {budget_code} - {budget_description}
Allocated Budget: ${allocated_budget:.2f}
Spent to Date: ${spent_to_date:.2f}

# PROJECT CONTEXT
Project: {project_name}
Floor: {floor_name}
Blueprint Revision: {revision}

# BUSINESS RULES
- Asset removals always require human review
- Cost savings may be reallocated or returned to contingency
- Removal may indicate design changes requiring architectural review

# YOUR TASK
Analyze this asset removal and provide a recommendation. Consider:
1. Why might this asset have been removed?
2. Should the cost savings be reallocated or returned to contingency?
3. Does this removal indicate a significant design change?
4. Are there dependencies on other assets?

Provide your recommendation using the recommend_action function with these parameters:
- action_type: "flag_for_approval" (required for removals)
- requires_human: true
- confidence_score: 0.0 to 1.0
- reasoning: clear explanation including cost savings recommendation
"""

    @staticmethod
    def get_function_definition() -> Dict[str, Any]:
        """
        Get the Claude function calling definition for recommend_action.

        Returns:
            Function definition dictionary for Claude API
        """
        return {
            "name": "recommend_action",
            "description": "Recommend an action for a blueprint change",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": ["update_budget", "flag_for_approval"],
                        "description": "The type of action to take"
                    },
                    "requires_human": {
                        "type": "boolean",
                        "description": "Whether human approval is required"
                    },
                    "confidence_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence in the recommendation (0.0-1.0)"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Clear explanation of the decision"
                    },
                    "recommended_budget_code": {
                        "type": "string",
                        "description": "Budget line item code for new assets (optional)"
                    }
                },
                "required": ["action_type", "requires_human", "confidence_score", "reasoning"]
            }
        }
