# apps/backend/app/api/endpoints/coaching.py
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError

from app.api.deps import get_current_active_user
from app.core.security import decode_access_token
from app.db.redis import get_redis_client
from app.middleware.rate_limit import RateLimiter
from app.models.domain import CoachingSession, SessionType
from app.models.user import User
from app.schemas.coaching import (
    CoachingHistoryResponse,
    CoachingInsightsRequest,
    CoachingInsightsResponse,
    CoachingSessionRequest,
    CoachingSessionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# WebSocket rate limiting configuration
WS_CONNECTION_LIMIT = 10  # Max connections per user per hour
WS_MESSAGE_LIMIT = 60  # Max messages per minute per user
WS_TOOL_CALL_LIMIT = 10  # Max tool calls per minute per user
WS_MAX_MESSAGE_SIZE = 10000  # Max message size in characters
WS_MAX_TOOL_ARG_SIZE = 5000  # Max tool argument size in characters

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def check_websocket_rate_limit(
    user_id: uuid.UUID,
    limit_type: str = "connection"
) -> tuple[bool, Optional[str]]:
    """
    Check WebSocket rate limits using Redis.

    Args:
        user_id: The user ID to check limits for
        limit_type: Type of limit (connection, message, tool_call)

    Returns:
        Tuple of (is_allowed, error_message)
    """
    try:
        redis_client = get_redis_client()
        rate_limiter = RateLimiter()

        # Map limit types to Redis keys and limits
        limit_configs = {
            "connection": (f"ws_connection:{user_id}", WS_CONNECTION_LIMIT, 3600),
            "message": (f"ws_message:{user_id}", WS_MESSAGE_LIMIT, 60),
            "tool_call": (f"ws_tool_call:{user_id}", WS_TOOL_CALL_LIMIT, 60),
        }

        key, limit, window = limit_configs.get(limit_type, limit_configs["message"])

        # Use sliding window algorithm
        current_time = int(time.time())
        window_start = current_time - window

        # Remove entries outside current window
        await redis_client.zremrangebyscore(key, 0, window_start)

        # Count current entries
        current_count = await redis_client.zcard(key)

        if current_count >= limit:
            return False, f"Rate limit exceeded for {limit_type}"

        # Add current request
        import uuid as uuid_lib
        member_id = f"{current_time}_{uuid_lib.uuid4().hex}"
        await redis_client.zadd(key, {member_id: current_time})
        await redis_client.expire(key, window + 10)

        return True, None

    except Exception as e:
        logger.error(f"WebSocket rate limiting error: {e}")
        # Fail closed for security
        return False, "Rate limiting service unavailable"


async def get_websocket_user(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
) -> User:
    """
    Authenticate WebSocket connection using JWT token from query parameter.

    This dependency validates the JWT token and returns the authenticated user.
    The token should be passed as a query parameter: ws://host/path?token=xyz
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
            raise credentials_exception

    except ExpiredSignatureError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from None
    except (InvalidTokenError, PyJWTError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise credentials_exception from None

    # Import here to avoid circular dependency
    from sqlalchemy import select

    from app.db.postgres import get_postgres_session

    async for session in get_postgres_session():
        result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            raise credentials_exception

        if not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Inactive user")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
            )

        return user

# WebSocket connection manager
class ConnectionManager:
    """Manages active WebSocket connections for coaching sessions."""

    def __init__(self):
        self.active_connections: dict[uuid.UUID, WebSocket] = {}

    async def connect(self, session_id: uuid.UUID, websocket: WebSocket):
        """Accept a WebSocket connection for a coaching session."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: uuid.UUID):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_message(self, session_id: uuid.UUID, message: dict):
        """Send a message to a specific coaching session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {e}")
                self.disconnect(session_id)

manager = ConnectionManager()


@router.post("/session", response_model=CoachingSessionResponse)
async def create_coaching_session(
    request: CoachingSessionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CoachingSessionResponse:
    """
    Create a new coaching session.

    This endpoint creates a coaching session record and returns a WebSocket URL
    for real-time coaching interaction. The session will be handled by the
    appropriate agent based on the session_type.

    Requires authentication. Multi-tenant isolation is enforced by user_id.
    """
    try:
        # Create coaching session document
        session = CoachingSession(
            user_id=current_user.id,
            session_type=request.session_type,
            agent_id=request.agent_id,
            title=request.title,
            metadata=request.metadata,
        )
        await session.insert()

        # Generate WebSocket URL (placeholder for now)
        websocket_url = f"ws://localhost:8000/v1/coaching/ws/{session.id}"

        logger.info(
            f"Created coaching session {session.id} for user {current_user.id}, "
            f"type={request.session_type.value}"
        )

        return CoachingSessionResponse(
            id=session.id,
            user_id=session.user_id,
            session_type=session.session_type,
            agent_id=session.agent_id,
            title=session.title,
            status=session.status,
            metadata=session.metadata,
            started_at=session.started_at,
            ended_at=session.ended_at,
            created_at=session.created_at,
            websocket_url=websocket_url,
        )

    except Exception as e:
        logger.error(f"Failed to create coaching session for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create coaching session. Please try again later."
        )


@router.get("/history", response_model=CoachingHistoryResponse)
async def get_coaching_history(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(default=20, ge=1, le=100, description="Number of results to return"),
    session_type: Optional[str] = Query(None, description="Filter by session type"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
) -> CoachingHistoryResponse:
    """
    Get coaching session history for the current user.

    Supports cursor-based pagination and filtering by session_type.
    All queries are scoped to the authenticated user for multi-tenant isolation.
    """
    try:
        # Build query with tenant isolation
        query = CoachingSession.find(CoachingSession.user_id == current_user.id)

        # Apply session type filter if provided
        if session_type:
            try:
                session_type_enum = SessionType(session_type)
                query = query.find(CoachingSession.session_type == session_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid session_type"
                )

        # Apply cursor pagination if provided
        if cursor:
            try:
                cursor_uuid = uuid.UUID(cursor)
                query = query.find(CoachingSession.id > cursor_uuid)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor format"
                )

        # Sort by started_at descending and apply limit
        query = query.sort("-started_at").limit(limit)

        sessions = await query.to_list()

        # Calculate next cursor
        next_cursor = None
        if len(sessions) == limit:
            next_cursor = str(sessions[-1].id)

        # Get total count
        count_query = CoachingSession.find(CoachingSession.user_id == current_user.id)
        if session_type:
            try:
                session_type_enum = SessionType(session_type)
                count_query = count_query.find(CoachingSession.session_type == session_type_enum)
            except ValueError:
                count_query = count_query
        total_count = await count_query.count()

        # Convert to response models
        session_responses = [
            CoachingSessionResponse(
                id=str(session.id),  # Convert ObjectId to string
                user_id=str(session.user_id) if session.user_id else None,  # Convert UUID to string
                session_type=session.session_type,
                agent_id=session.agent_id,
                title=session.title,
                status=session.status,
                metadata=session.metadata,
                started_at=session.started_at,
                ended_at=session.ended_at,
                created_at=session.created_at,
                websocket_url=None,  # Not included in history
            )
            for session in sessions
        ]

        logger.info(
            f"Retrieved {len(session_responses)} coaching sessions for user {current_user.id}"
        )

        return CoachingHistoryResponse(
            sessions=session_responses,
            next_cursor=next_cursor,
            total_count=total_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve coaching history for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve coaching history. Please try again later."
        )


@router.get("/insights", response_model=CoachingInsightsResponse)
async def get_coaching_insights(
    request: CoachingInsightsRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CoachingInsightsResponse:
    """
    Get coaching insights for the current user.

    Supports filtering by insight_type and pillar.
    All queries are scoped to the authenticated user for multi-tenant isolation.
    """
    try:
        # Build query with tenant isolation
        from app.models.domain import AIInsight
        query = AIInsight.find(AIInsight.user_id == current_user.id)

        # Apply insight type filter if provided
        if request.insight_type:
            query = query.find(AIInsight.insight_type == request.insight_type)

        # Apply pillar filter if provided
        if request.pillar:
            query = query.find(AIInsight.pillar == request.pillar)

        # Sort by generated_at descending and apply limit
        query = query.sort("-generated_at").limit(request.limit)

        insights = await query.to_list()

        # Get total count
        count_query = AIInsight.find(AIInsight.user_id == current_user.id)
        if request.insight_type:
            count_query = count_query.find(AIInsight.insight_type == request.insight_type)
        if request.pillar:
            count_query = count_query.find(AIInsight.pillar == request.pillar)
        total_count = await count_query.count()

        # Convert to response models
        from app.schemas.coaching import InsightResponse
        insight_responses = [
            InsightResponse(
                id=insight.id,
                user_id=insight.user_id,
                insight_type=insight.insight_type,
                pillar=insight.pillar,
                payload=insight.payload,
                confidence=insight.confidence,
                session_id=insight.session_id,
                generated_at=insight.generated_at,
                expires_at=insight.expires_at,
            )
            for insight in insights
        ]

        logger.info(
            f"Retrieved {len(insight_responses)} insights for user {current_user.id}"
        )

        return CoachingInsightsResponse(
            insights=insight_responses,
            total_count=total_count,
        )

    except Exception as e:
        logger.error(f"Failed to retrieve coaching insights for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve coaching insights. Please try again later."
        )


@router.websocket("/ws/{session_id}")
async def coaching_websocket(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time coaching sessions with JWT authentication.

    Authentication:
    - Requires valid JWT token via query parameter: ?token=xyz
    - Validates token expiration and user active status
    - Verifies session ownership (user_id must match)

    Authorization:
    - Only the session owner can connect
    - Tenant isolation enforced at database level

    Supports five message types:
    - assistant_message: AI response
    - tool_call: Request to execute a tool
    - tool_response: Result of tool execution
    - error: Error message
    - heartbeat: Keep-alive ping

    Tool calls have a 5-second timeout with fallback response.
    """
    # Step 1: Authenticate user
    try:
        user = await get_websocket_user(websocket, token)
    except HTTPException:
        # Connection already closed by get_websocket_user
        return

    # Step 2: Check connection rate limit
    is_allowed, rate_limit_error = await check_websocket_rate_limit(user.id, "connection")
    if not is_allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=rate_limit_error or "Rate limit exceeded")
        logger.warning(f"WebSocket connection rate limited for user {user.id}: {rate_limit_error}")
        return

    # Step 3: Accept connection
    await manager.connect(session_id, websocket)

    try:
        # Step 3: Verify session exists and belongs to authenticated user
        session = await CoachingSession.get(session_id)
        if not session:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning(f"WebSocket connection rejected: Session {session_id} not found for user {user.id}")
            return

        # Step 4: Verify session ownership (multi-tenant isolation)
        if session.user_id != user.id:
            await websocket.send_json({
                "type": "error",
                "message": "Unauthorized access to session"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning(
                f"WebSocket connection rejected: User {user.id} attempted to access "
                f"session {session_id} owned by {session.user_id}"
            )
            return

        # Step 5: Send session context
        await websocket.send_json({
            "type": "assistant_message",
            "content": f"Connected to coaching session: {session.title or session.session_type.value}",
            "session_type": session.session_type.value,
            "agent_id": session.agent_id,
            "user_id": str(user.id)  # Include user_id for client reference
        })

        logger.info(
            f"WebSocket connected for session {session_id} by authenticated user {user.id}"
        )

        # Message handling loop
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0  # 30-second timeout for messages
                )

                # Check message rate limit
                is_allowed, rate_limit_error = await check_websocket_rate_limit(user.id, "message")
                if not is_allowed:
                    await websocket.send_json({
                        "type": "error",
                        "message": rate_limit_error or "Message rate limit exceeded"
                    })
                    logger.warning(f"Message rate limited for user {user.id}")
                    continue

                # Validate message size
                message_str = str(data)
                if len(message_str) > WS_MAX_MESSAGE_SIZE:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Message too large (max {WS_MAX_MESSAGE_SIZE} characters)"
                    })
                    logger.warning(f"Oversized message from user {user.id}")
                    continue

                message_type = data.get("type")

                if message_type == "heartbeat":
                    # Respond to heartbeat
                    await websocket.send_json({"type": "heartbeat"})

                elif message_type == "tool_call":
                    # Check tool call rate limit
                    is_allowed, rate_limit_error = await check_websocket_rate_limit(user.id, "tool_call")
                    if not is_allowed:
                        await websocket.send_json({
                            "type": "error",
                            "message": rate_limit_error or "Tool call rate limit exceeded"
                        })
                        logger.warning(f"Tool call rate limited for user {user.id}")
                        continue

                    # Handle tool call with 5-second timeout
                    tool_name = data.get("tool_name")
                    tool_args = data.get("arguments", {})

                    # Validate tool argument size
                    args_str = str(tool_args)
                    if len(args_str) > WS_MAX_TOOL_ARG_SIZE:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Tool arguments too large (max {WS_MAX_TOOL_ARG_SIZE} characters)"
                        })
                        logger.warning(f"Oversized tool arguments from user {user.id}")
                        continue

                    logger.info(f"Tool call received: {tool_name} for session {session_id}")

                    try:
                        # Execute tool through secure registry with user context
                        tool_result = await asyncio.wait_for(
                            execute_tool(tool_name, tool_args, user.id, "authenticated"),
                            timeout=5.0
                        )

                        await websocket.send_json({
                            "type": "tool_response",
                            "tool_name": tool_name,
                            "result": tool_result
                        })
                    except asyncio.TimeoutError:
                        logger.warning(f"Tool call timeout for {tool_name} in session {session_id}")
                        await websocket.send_json({
                            "type": "tool_response",
                            "tool_name": tool_name,
                            "result": {"error": "Tool execution timeout"},
                            "fallback": True
                        })
                    except ValueError as e:
                        # Tool validation/registration error
                        logger.warning(f"Tool validation failed for {tool_name}: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Tool validation failed: {str(e)}"
                        })
                    except PermissionError as e:
                        # Tool authorization error
                        logger.warning(f"Tool authorization failed for {tool_name}: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Tool authorization failed: {str(e)}"
                        })
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Tool execution failed: {str(e)}"
                        })

                elif message_type == "user_message":
                    # Handle user message with coaching service integration
                    user_content = data.get("content", "")
                    logger.info(f"User message in session {session_id}: {user_content[:50]}...")

                    # Use coaching service to generate response
                    try:
                        from app.ai.agent_system.router import AgentRouter
                        from app.ai.memory_engine import MemoryManager
                        from app.services.coaching import CoachingFlowService

                        # Initialize coaching service with real dependencies
                        memory_manager = MemoryManager()
                        agent_router = AgentRouter()
                        coaching_service = CoachingFlowService(
                            memory_manager=memory_manager,
                            agent_router=agent_router
                        )

                        # Generate response based on session type
                        if session.session_type == SessionType.ASSESSMENT:
                            response = await coaching_service.handle_assessment_flow(session, user_content)
                        elif session.session_type == SessionType.NUDGE:
                            response = await coaching_service.handle_nudge_flow(session, user_content)
                        elif session.session_type == SessionType.REFLECTION:
                            response = await coaching_service.handle_reflection_flow(session, user_content)
                        elif session.session_type == SessionType.ESCALATION:
                            response = await coaching_service.handle_escalation_flow(session, user_content)
                        else:
                            response = {
                                "type": "assistant_message",
                                "content": "I'm here to help you. What would you like to discuss?"
                            }

                        await websocket.send_json(response)

                    except Exception as e:
                        logger.error(f"Coaching service error: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Failed to process your message. Please try again."
                        })

                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })

            except asyncio.TimeoutError:
                # Send heartbeat if no message received
                await websocket.send_json({"type": "heartbeat"})

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break

            except Exception as e:
                logger.error(f"Error processing message in session {session_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Error processing message"
                })

    finally:
        manager.disconnect(session_id)
        # Update session status
        session = await CoachingSession.get(session_id)
        if session:
            session.status = "completed"
            session.ended_at = datetime.now()
            await session.save()


async def execute_tool(tool_name: str, tool_args: dict, user_id: uuid.UUID, user_role: str = "authenticated") -> dict:
    """
    Execute a tool call through the secure tool registry.

    This function:
    - Validates tool is registered in the allowlist
    - Validates tool arguments against schema
    - Checks authorization requirements
    - Enforces tenant isolation
    - Executes tool with user context

    Args:
        tool_name: Name of the tool to execute
        tool_args: Tool arguments
        user_id: ID of the user executing the tool
        user_role: Role of the user for authorization

    Returns:
        Tool execution result

    Raises:
        ValueError: If tool is not registered or validation fails
        PermissionError: If authorization fails
    """
    tool_registry = get_tool_registry()

    try:
        result = await tool_registry.execute_tool(
            tool_name=tool_name,
            arguments=tool_args,
            user_id=user_id,
            user_role=user_role
        )
        return result
    except ValueError as e:
        logger.error(f"Tool validation failed: {e}")
        raise
    except PermissionError as e:
        logger.error(f"Tool authorization failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        raise
