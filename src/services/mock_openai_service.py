"""Mock OpenAI service for vision analysis and chat completion."""

import random
import time
from typing import Optional

from src.utils.openai_formatter import format_vision_analysis, format_chat_completion


# Mock vision analysis descriptions
VISION_DESCRIPTIONS = [
    "This image shows a vibrant outdoor scene with lush greenery and bright colors.",
    "I can see a well-composed photograph featuring interesting lighting and shadows.",
    "This appears to be a portrait with good focus on the subject and a blurred background.",
    "The image depicts an urban landscape with architectural elements and geometric shapes.",
    "This is a close-up photograph showcasing intricate details and textures.",
    "I observe a natural scene with organic forms and harmonious color palette.",
    "This image captures a moment in time with dynamic composition and movement.",
    "The photograph features a balanced arrangement of elements with pleasing symmetry.",
]


def mock_openai_vision_analysis(image_path: str, delay: float = 0.1) -> dict:
    """Generate mock vision analysis for an uploaded image.

    Args:
        image_path: Path to the image file
        delay: Simulated processing delay in seconds

    Returns:
        OpenAI-compatible vision analysis response
    """
    # Simulate processing time
    time.sleep(delay)

    # Generate mock description
    description = random.choice(VISION_DESCRIPTIONS)

    # Format as OpenAI vision analysis
    return format_vision_analysis(
        content=description,
        prompt_tokens=100,
        completion_tokens=len(description.split()) * 2,  # Rough token estimate
    )


def mock_openai_chat(
    prompt: str,
    image_id: str,
    stream: bool = False,
    delay: float = 3,
) -> dict:
    """Generate mock chat completion response.

    Args:
        prompt: User's chat prompt
        image_id: ID of image being discussed
        stream: Whether to stream response (not implemented in Phase 1)
        delay: Simulated processing delay in seconds

    Returns:
        OpenAI-compatible chat completion response
    """
    if stream:
        # Streaming implementation deferred to Question 2
        raise NotImplementedError("Streaming responses will be implemented in Question 2")

    # Simulate processing time
    time.sleep(delay)

    # Generate mock response based on prompt
    if "color" in prompt.lower():
        response = "The image has a rich color palette with warm tones and vibrant hues."
    elif "what" in prompt.lower() or "see" in prompt.lower():
        response = "I see a well-composed photograph with interesting visual elements and good lighting."
    elif "describe" in prompt.lower():
        response = "This is a detailed photograph featuring balanced composition, natural lighting, and harmonious colors. The subject is well-defined with good contrast against the background."
    else:
        response = f"I understand your question about the image. The photograph shows interesting visual characteristics and composition."

    # Format as OpenAI chat completion
    return format_chat_completion(
        content=response,
        prompt_tokens=len(prompt.split()) * 2,  # Rough token estimate
        completion_tokens=len(response.split()) * 2,
    )
