# app/ai/tools/registry.py
"""
Tool Registry - Secure tool execution system for Coaching Engine.

Implements:
- Tool allowlist (only registered tools can execute)
- Tool authorization requirements
- Input validation against schemas
- Tenant isolation enforcement
- Security context propagation
"""
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from bson import ObjectId
from pydantic import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """Schema definition for tool arguments."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format
    required: List[str]


@dataclass
class ToolAuthorization:
    """Authorization requirements for tool execution."""
    require_user_context: bool = True
    allowed_roles: Optional[List[str]] = None
    require_tenant_isolation: bool = True
    max_arg_size: int = 5000


@dataclass
class ToolDefinition:
    """Complete tool definition with execution logic."""
    name: str
    description: str
    schema: ToolSchema
    authorization: ToolAuthorization
    executor: Callable


class ToolRegistry:
    """
    Registry for allowed tools with validation and authorization.

    Only tools registered here can be executed through the coaching system.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default coaching tools."""
        # Example: Habit tracking tool
        self.register_tool(
            ToolDefinition(
                name="check_habit_status",
                description="Check the current status of a user's habit",
                schema=ToolSchema(
                    name="check_habit_status",
                    description="Check habit completion status",
                    parameters={
                        "type": "object",
                        "properties": {
                            "habit_id": {
                                "type": "string",
                                "description": "ID of the habit to check"
                            }
                        },
                        "required": ["habit_id"]
                    },
                    required=["habit_id"]
                ),
                authorization=ToolAuthorization(
                    require_user_context=True,
                    require_tenant_isolation=True,
                    max_arg_size=1000
                ),
                executor=self._execute_check_habit_status
            )
        )

        # Example: Goal progress tool
        self.register_tool(
            ToolDefinition(
                name="get_goal_progress",
                description="Get progress towards a specific goal",
                schema=ToolSchema(
                    name="get_goal_progress",
                    description="Retrieve goal progress metrics",
                    parameters={
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            }
                        },
                        "required": ["goal_id"]
                    },
                    required=["goal_id"]
                ),
                authorization=ToolAuthorization(
                    require_user_context=True,
                    require_tenant_isolation=True,
                    max_arg_size=1000
                ),
                executor=self._execute_get_goal_progress
            )
        )

        # Example: Journal retrieval tool
        self.register_tool(
            ToolDefinition(
                name="get_recent_journals",
                description="Get recent journal entries for the user",
                schema=ToolSchema(
                    name="get_recent_journals",
                    description="Retrieve recent journal entries",
                    parameters={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of entries to retrieve",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 20
                            }
                        },
                        "required": []
                    },
                    required=[]
                ),
                authorization=ToolAuthorization(
                    require_user_context=True,
                    require_tenant_isolation=True,
                    max_arg_size=500
                ),
                executor=self._execute_get_recent_journals
            )
        )

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a new tool in the registry."""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def is_tool_registered(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: uuid.UUID,
        user_role: str = "authenticated"
    ) -> Dict[str, Any]:
        """
        Execute a tool with full security validation.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            user_id: ID of the user executing the tool
            user_role: Role of the user for authorization

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not registered or validation fails
            PermissionError: If authorization fails
        """
        # Step 1: Check tool is registered
        tool = self.get_tool(tool_name)
        if not tool:
            logger.warning(f"Attempted to execute unregistered tool: {tool_name} by user {user_id}")
            raise ValueError(f"Tool '{tool_name}' is not registered")

        # Step 2: Validate arguments against schema
        try:
            self._validate_arguments(tool.schema, arguments)
        except ValidationError as e:
            logger.warning(f"Tool argument validation failed for {tool_name}: {e}")
            raise ValueError(f"Invalid arguments for tool '{tool_name}': {e}")

        # Step 3: Check authorization
        if not self._check_authorization(tool.authorization, user_id, user_role):
            logger.warning(f"Tool authorization failed for {tool_name} by user {user_id}")
            raise PermissionError(f"User not authorized to execute tool '{tool_name}'")

        # Step 4: Execute tool with user context
        try:
            result = await tool.executor(arguments, user_id)
            logger.info(f"Tool {tool_name} executed successfully by user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}", exc_info=True)
            raise

    def _validate_arguments(self, schema: ToolSchema, arguments: Dict[str, Any]) -> None:
        """Validate arguments against tool schema."""
        # Check required fields
        for field in schema.required:
            if field not in arguments:
                raise ValueError(f"Missing required field: {field}")

        # Check for unexpected fields (security measure)
        allowed_fields = set(schema.parameters.get("properties", {}).keys())
        for field in arguments:
            if field not in allowed_fields:
                raise ValueError(f"Unexpected field in arguments: {field}")

        # Type validation would go here with a proper JSON Schema validator
        # For now, we do basic validation
        properties = schema.parameters.get("properties", {})
        for field, value in arguments.items():
            field_schema = properties.get(field, {})
            expected_type = field_schema.get("type")

            if expected_type == "string" and not isinstance(value, str):
                raise ValueError(f"Field {field} must be string")
            elif expected_type == "integer" and not isinstance(value, int):
                raise ValueError(f"Field {field} must be integer")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Field {field} must be number")
            elif expected_type == "boolean" and not isinstance(value, bool):
                raise ValueError(f"Field {field} must be boolean")

    def _check_authorization(
        self,
        auth: ToolAuthorization,
        user_id: uuid.UUID,
        user_role: str
    ) -> bool:
        """Check if user is authorized to execute tool."""
        # Check role requirements
        if auth.allowed_roles and user_role not in auth.allowed_roles:
            return False

        # User context is always required in our implementation
        if auth.require_user_context and not user_id:
            return False

        return True

    async def _log_security_event(
        self,
        user_id: uuid.UUID,
        event_type: str,
        resource_id: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Log security events for compliance and observability.

        Args:
            user_id: ID of the user involved in the security event
            event_type: Type of security event
            resource_id: ID of the resource being accessed
            details: Additional event details
        """
        try:
            from app.models.domain import ComplianceEvent

            # Create compliance event for security logging
            compliance_event = ComplianceEvent(
                user_id=user_id,
                event_type=event_type,
                severity_level=0.7,  # High severity for cross-tenant attempts
                details={
                    "resource_id": resource_id,
                    **details
                }
            )
            await compliance_event.insert()

            logger.warning(
                f"Security event logged: {event_type} by user {user_id} "
                f"for resource {resource_id}"
            )

        except Exception as e:
            # Don't fail the tool execution if logging fails
            logger.error(f"Failed to log security event: {e}", exc_info=True)

    # Tool executors with real database access and ownership enforcement
    async def _execute_check_habit_status(
        self,
        arguments: Dict[str, Any],
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Execute habit status check with real database access and tenant isolation.

        Security: Enforces ownership at database query level.
        """
        from app.models.domain import Habit

        habit_id = arguments.get("habit_id")

        if not habit_id:
            logger.warning(f"Missing habit_id in tool call by user {user_id}")
            raise ValueError("habit_id is required")

        try:
            # Convert string ID to ObjectId for MongoDB query
            try:
                habit_object_id = ObjectId(habit_id)
            except Exception:
                logger.warning(f"Invalid habit_id format: {habit_id}")
                raise ValueError("Invalid habit_id format")

            # Query habit with ownership filter at database level
            habit = await Habit.find_one(
                {
                    "_id": habit_object_id,
                    "user_id": user_id
                }
            )

            if not habit:
                # Habit either doesn't exist or belongs to another user
                # Return generic not-found to prevent enumeration
                logger.warning(
                    f"Cross-tenant access attempt: User {user_id} attempted to access habit {habit_id}"
                )

                # Log security event for compliance
                await self._log_security_event(
                    user_id=user_id,
                    event_type="cross_tenant_habit_access",
                    resource_id=habit_id,
                    details={"tool": "check_habit_status"}
                )

                raise ValueError("Habit not found")

            # Return actual habit data from database
            return {
                "status": "success",
                "habit_id": str(habit.id),
                "title": habit.title,
                "frequency": habit.frequency,
                "streak_count": habit.streak_count,
                "created_at": habit.created_at.isoformat()
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error checking habit status for user {user_id}: {e}", exc_info=True)
            raise ValueError("Failed to retrieve habit status")

    async def _execute_get_goal_progress(
        self,
        arguments: Dict[str, Any],
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Execute goal progress retrieval with real database access and tenant isolation.

        Security: Enforces ownership at database query level.
        """
        from app.models.domain import Goal

        goal_id = arguments.get("goal_id")

        if not goal_id:
            logger.warning(f"Missing goal_id in tool call by user {user_id}")
            raise ValueError("goal_id is required")

        try:
            # Convert string ID to ObjectId for MongoDB query
            try:
                goal_object_id = ObjectId(goal_id)
            except Exception:
                logger.warning(f"Invalid goal_id format: {goal_id}")
                raise ValueError("Invalid goal_id format")

            # Query goal with ownership filter at database level
            goal = await Goal.find_one(
                {
                    "_id": goal_object_id,
                    "user_id": user_id
                }
            )

            if not goal:
                # Goal either doesn't exist or belongs to another user
                # Return generic not-found to prevent enumeration
                logger.warning(
                    f"Cross-tenant access attempt: User {user_id} attempted to access goal {goal_id}"
                )

                # Log security event for compliance
                await self._log_security_event(
                    user_id=user_id,
                    event_type="cross_tenant_goal_access",
                    resource_id=goal_id,
                    details={"tool": "get_goal_progress"}
                )

                raise ValueError("Goal not found")

            # Calculate progress based on completion status
            progress_percentage = 100 if goal.is_completed else 0

            # Return actual goal data from database
            return {
                "status": "success",
                "goal_id": str(goal.id),
                "title": goal.title,
                "description": goal.description,
                "target_date": goal.target_date.isoformat(),
                "is_completed": goal.is_completed,
                "progress_percentage": progress_percentage,
                "created_at": goal.created_at.isoformat()
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting goal progress for user {user_id}: {e}", exc_info=True)
            raise ValueError("Failed to retrieve goal progress")

    async def _execute_get_recent_journals(
        self,
        arguments: Dict[str, Any],
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Execute recent journals retrieval with real database access and tenant isolation.

        Security: Enforces ownership at database query level.
        """
        from app.models.domain import JournalEntry

        limit = arguments.get("limit", 5)

        # Validate limit bounds
        if limit < 1 or limit > 20:
            logger.warning(f"Invalid limit {limit} in tool call by user {user_id}")
            raise ValueError("limit must be between 1 and 20")

        try:
            # Query journals with ownership filter at database level
            # The user_id filter in the query itself prevents cross-tenant access
            journals = await JournalEntry.find(
                {"user_id": user_id}
            ).sort("-created_at").limit(limit).to_list()

            # Return actual journal data from database
            journal_list = [
                {
                    "id": str(journal.id),
                    "content": journal.content,
                    "mood_score": journal.mood_score,
                    "created_at": journal.created_at.isoformat()
                }
                for journal in journals
            ]

            return {
                "status": "success",
                "journals": journal_list,
                "count": len(journal_list)
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting recent journals for user {user_id}: {e}", exc_info=True)
            raise ValueError("Failed to retrieve recent journals")


# Global tool registry instance
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _tool_registry
