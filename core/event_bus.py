import logging
from collections import defaultdict
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)

class EventBus:
    """
    A simple Publish-Subscribe event bus to decouple components.
    Allows different parts of the application to communicate without direct dependencies.
    """
    _subscribers: Dict[str, List[Callable]] = defaultdict(list)

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable):
        """
        Subscribe a callback function to a specific event type.
        """
        cls._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed {callback} to {event_type}")

    @classmethod
    def publish(cls, event_type: str, data: Any = None):
        """
        Publish an event, notifying all subscribers.
        """
        logger.debug(f"Publishing event: {event_type} with data: {data}")
        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in subscriber {callback} for event {event_type}: {e}")

    @classmethod
    def unsubscribe(cls, event_type: str, callback: Callable):
        """
        Unsubscribe a callback from an event type.
        """
        if event_type in cls._subscribers:
            try:
                cls._subscribers[event_type].remove(callback)
            except ValueError:
                pass


# Global Event Types
class Events:
    STATUS_UPDATE = "status_update"
    ERROR_OCCURRED = "error_occurred"
    ACCOUNT_ADDED = "account_added"
    EMAIL_RECEIVED = "email_received"
    FOLDER_UPDATED = "folder_updated"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    EMAIL_SELECTED = "email_selected"
    EMAIL_OPENED = "email_opened"
