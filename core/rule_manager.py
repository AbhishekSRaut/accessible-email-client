
import json
import logging
from typing import List, Dict, Any, Optional
from ..database.db_manager import db_manager

logger = logging.getLogger(__name__)

class RuleManager:
    """
    Manages smart folder rules, scoped per account.
    """
    def __init__(self):
        self.db = db_manager

    def add_rule(self, name: str, conditions: Dict[str, str], actions: Dict[str, str], account_id: int = None) -> bool:
        """
        Add a new rule scoped to an account.
        """
        try:
            query = "INSERT INTO rules (name, condition_json, action_json, account_id, is_active) VALUES (?, ?, ?, ?, 1)"
            cond_json = json.dumps(conditions)
            act_json = json.dumps(actions)
            self.db.execute_commit(query, (name, cond_json, act_json, account_id))
            return True
        except Exception as e:
            logger.error(f"Failed to add rule: {e}")
            return False

    def get_rules(self, account_id: int = None) -> List[Dict[str, Any]]:
        """
        Get active rules, optionally filtered by account.
        If account_id is provided, returns rules for that account + any legacy global rules (account_id IS NULL).
        """
        try:
            if account_id is not None:
                query = "SELECT id, name, condition_json, action_json, account_id FROM rules WHERE is_active = 1 AND (account_id = ? OR account_id IS NULL)"
                rows = self.db.fetch_all(query, (account_id,))
            else:
                query = "SELECT id, name, condition_json, action_json, account_id FROM rules WHERE is_active = 1"
                rows = self.db.fetch_all(query)
            rules = []
            for row in rows:
                rules.append({
                    "id": row["id"],
                    "name": row["name"],
                    "conditions": json.loads(row["condition_json"]),
                    "actions": json.loads(row["action_json"]),
                    "account_id": row["account_id"]
                })
            return rules
        except Exception as e:
            logger.error(f"Failed to get rules: {e}")
            return []

    def update_rule(self, rule_id: int, name: str, conditions: Dict[str, str], actions: Dict[str, str], account_id: int = None) -> bool:
        try:
            query = "UPDATE rules SET name = ?, condition_json = ?, action_json = ?, account_id = ? WHERE id = ?"
            cond_json = json.dumps(conditions)
            act_json = json.dumps(actions)
            self.db.execute_commit(query, (name, cond_json, act_json, account_id, rule_id))
            return True
        except Exception as e:
            logger.error(f"Failed to update rule {rule_id}: {e}")
            return False

    def delete_rule(self, rule_id: int) -> bool:
        try:
            query = "DELETE FROM rules WHERE id = ?"
            self.db.execute_commit(query, (rule_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete rule {rule_id}: {e}")
            return False

    def apply_rules(self, email_data: Dict[str, Any], account_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Check if email matches any rule for the given account.
        Returns the action dict of the first matching rule, or None.
        """
        rules = self.get_rules(account_id=account_id)
        sender = email_data.get("sender", "").lower()
        subject = email_data.get("subject", "").lower()
        to = email_data.get("to", "").lower()
        cc = email_data.get("cc", "").lower()
        recipients = f"{to}, {cc}"  # Combined for matching

        logger.debug(f"[RULES] Checking {len(rules)} rules against email: sender='{sender}', to='{to}', cc='{cc}', subject='{subject[:50]}'")

        for rule in rules:
            conditions = rule["conditions"]
            match = True
            
            # Check all conditions (AND logic)
            for field, value in conditions.items():
                value = value.lower()
                target_values = [v.strip() for v in value.split(',') if v.strip()]
                
                if field == "sender":
                    if not any(tv in sender for tv in target_values):
                        match = False
                        logger.debug(f"[RULES] Rule '{rule['name']}': sender mismatch. Looking for {target_values} in '{sender}'")
                        break
                elif field == "subject":
                    if not any(tv in subject for tv in target_values):
                        match = False
                        break
                elif field == "recipient":
                    if not any(tv in recipients for tv in target_values):
                        match = False
                        logger.debug(f"[RULES] Rule '{rule['name']}': recipient mismatch. Looking for {target_values} in to='{to}' cc='{cc}'")
                        break
                else:
                    logger.warning(f"[RULES] Unknown condition field: '{field}'")
                    match = False
                    break
            
            if match:
                logger.info(f"Email matched rule '{rule['name']}'")
                return rule["actions"]
        
        return None
