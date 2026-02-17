"""Chat processing service with queuing and photo relevance."""

import random
import threading
import uuid
from typing import Dict, List, Optional, Tuple

from src.models.chat import ChatRequest, QueuedRequest
from src.models.session import SessionContext


class ChatService:
    """Service for chat processing, queuing, and photo relevance analysis."""

    def __init__(self, silly_excuses: List[str]):
        """Initialize chat service.

        Args:
            silly_excuses: List of silly excuse messages for upload-in-progress
        """
        self.silly_excuses = silly_excuses
        self._queued_requests: Dict[str, List[QueuedRequest]] = {}  # Key: upload_image_id
        self._completed_queues: Dict[str, QueuedRequest] = {}  # Key: queue_id
        self._upload_status: Dict[str, str] = {}  # Key: image_id, Value: "uploading" | "complete"
        self._lock = threading.RLock()

    def resolve_image_id(
        self, session: SessionContext, explicit_image_id: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve which image to use for chat.

        Args:
            session: Current session
            explicit_image_id: Explicit image ID override (optional)

        Returns:
            Tuple of (image_id, error_message)
        """
        # Check explicit override first
        if explicit_image_id:
            return explicit_image_id, None

        # Use session default
        if session.current_image_id:
            return session.current_image_id, None

        # No image available
        return None, "Please upload an image first"

    def check_upload_in_progress(self, image_id: str) -> bool:
        """Check if an image upload is in progress.

        Args:
            image_id: Image ID to check

        Returns:
            True if upload is in progress
        """
        with self._lock:
            return self._upload_status.get(image_id) == "uploading"

    def mark_upload_in_progress(self, image_id: str) -> None:
        """Mark an image as uploading.

        Args:
            image_id: Image ID
        """
        with self._lock:
            self._upload_status[image_id] = "uploading"

    def mark_upload_complete(self, image_id: str) -> None:
        """Mark an image upload as complete.

        Args:
            image_id: Image ID
        """
        with self._lock:
            self._upload_status[image_id] = "complete"

    def generate_silly_excuse(self) -> str:
        """Generate a random silly excuse.

        Returns:
            Random excuse message
        """
        return random.choice(self.silly_excuses)

    def queue_request(
        self, chat_request: ChatRequest, upload_image_id: str
    ) -> str:
        """Queue a chat request during upload.

        Args:
            chat_request: Chat request to queue
            upload_image_id: ID of image being uploaded

        Returns:
            Queue ID for polling
        """
        queue_id = str(uuid.uuid4())

        queued_request = QueuedRequest(
            id=queue_id,
            chat_request=chat_request,
            upload_image_id=upload_image_id,
            queued_at=chat_request.created_at,
            session_id=chat_request.session_id,
            status="pending",
        )

        with self._lock:
            if upload_image_id not in self._queued_requests:
                self._queued_requests[upload_image_id] = []

            self._queued_requests[upload_image_id].append(queued_request)

        return queue_id

    def get_queued_request(self, queue_id: str) -> Optional[QueuedRequest]:
        """Retrieve a queued request by queue ID.

        Args:
            queue_id: Queue ID

        Returns:
            QueuedRequest or None if not found
        """
        with self._lock:
            # Check completed queues first
            if queue_id in self._completed_queues:
                return self._completed_queues[queue_id]

            # Search in pending queues
            for queued_list in self._queued_requests.values():
                for queued_req in queued_list:
                    if queued_req.id == queue_id:
                        return queued_req

            return None

    def process_queued_requests(
        self, image_id: str, process_callback
    ) -> None:
        """Process all queued requests for an image after upload completes.

        Args:
            image_id: Image ID that just completed upload
            process_callback: Callable that processes a ChatRequest and returns response dict
        """
        with self._lock:
            if image_id not in self._queued_requests:
                return

            queued_list = self._queued_requests[image_id]

            for queued_req in queued_list:
                # Process the request
                response = process_callback(queued_req.chat_request)

                # Mark as completed
                queued_req.response = response
                queued_req.status = "completed"

                # Move to completed queues for polling
                self._completed_queues[queued_req.id] = queued_req

            # Clear from pending
            del self._queued_requests[image_id]

    def analyze_photo_relevance(
        self, conversation_topic: Optional[str], new_image_id: str
    ) -> bool:
        """Analyze if new photo is relevant to current conversation (mock).

        Args:
            conversation_topic: Current conversation topic (optional)
            new_image_id: ID of newly uploaded image

        Returns:
            True if related, False if unrelated
        """
        # If no current topic, always related (first image)
        if not conversation_topic:
            return True

        # Mock heuristic: random with 70% related, 30% unrelated
        # In production, this would use actual vision model similarity
        similarity_score = random.random()

        # Threshold: < 0.3 similarity = unrelated
        return similarity_score >= 0.3

    def generate_relevance_prompt(self) -> str:
        """Generate photo relevance confirmation prompt.

        Returns:
            Relevance prompt message
        """
        return (
            "This looks like a different topic - would you like to start a new conversation?"
        )

    def chat(
        self,
        prompt: str,
        image_id: Optional[str] = None,
        history: Optional[list] = None,
        delay: float = 0.2,
    ) -> dict:
        """Generate chat response with optional conversation history.

        Args:
            prompt: User's chat prompt
            image_id: ID of image being discussed (None for text-only)
            history: Optional conversation history in OpenAI messages format
            delay: Simulated processing delay

        Returns:
            OpenAI-compatible chat completion response
        """
        from src.services.mock_openai_service import mock_openai_chat

        return mock_openai_chat(
            prompt=prompt, image_id=image_id, history=history, stream=False, delay=delay
        )

    def stream_chat(
        self,
        prompt: str,
        image_id: Optional[str] = None,
        history: Optional[list] = None,
        delay: float = 0.2,
        timeout_seconds: float = 30,
    ):
        """Generate streaming chat response with optional conversation history.

        Args:
            prompt: User's chat prompt
            image_id: ID of image being discussed (None for text-only)
            history: Optional conversation history in OpenAI messages format
            delay: Simulated processing delay
            timeout_seconds: Max stream duration

        Returns:
            Generator yielding SSE-formatted chunks
        """
        from src.services.mock_openai_service import mock_openai_chat

        return mock_openai_chat(
            prompt=prompt,
            image_id=image_id,
            history=history,
            stream=True,
            delay=delay,
            timeout_seconds=timeout_seconds,
        )
