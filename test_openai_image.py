"""
Test script for OpenAI image analysis API
Tests the full response format from GPT-4.1 vision endpoint
Includes user text input alongside image upload (realistic usage)
"""
import base64
import json
import os
from openai import OpenAI

# Initialize the OpenAI client with your API key
api_key = "key"
client = OpenAI(api_key=api_key)

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Path to your image - using existing photo.jpg
image_path = "photo.jpg"

# User input that accompanies the photo upload
user_text = "This is my headshot photo for the application. Please analyze it."

print(f"Encoding image: {image_path}")
base64_image = encode_image(image_path)
print(f"Image encoded successfully (length: {len(base64_image)} chars)")
print(f"User text: '{user_text}'\n")

print("Sending request to OpenAI Responses API (image + user text)...")
response = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": [
                { "type": "input_text", "text": user_text },
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                },
            ],
        }
    ],
)

# Convert response to dict for format comparison
response_dict = response.to_dict()

print("\n" + "="*80)
print("FULL RESPONSE AS DICT (JSON):")
print("="*80)
print(json.dumps(response_dict, indent=2, default=str))

print("\n" + "="*80)
print("KEY PATH: output[0]['content'][0]['text']")
print("(This is how upload.py extracts the vision analysis)")
print("="*80)
print(response_dict["output"][0]["content"][0]["text"])

print("\n" + "="*80)
print("OUTPUT STRUCTURE BREAKDOWN:")
print("="*80)
for i, output_item in enumerate(response_dict["output"]):
    print(f"\noutput[{i}]:")
    print(f"  id: {output_item.get('id')}")
    print(f"  type: {output_item.get('type')}")
    print(f"  role: {output_item.get('role')}")
    print(f"  status: {output_item.get('status')}")
    for j, content_item in enumerate(output_item.get("content", [])):
        print(f"  content[{j}]:")
        print(f"    type: {content_item.get('type')}")
        print(f"    text: {content_item.get('text')}")
        print(f"    annotations: {content_item.get('annotations')}")

print("\n" + "="*80)
print("USAGE:")
print("="*80)
print(json.dumps(response_dict.get("usage", {}), indent=2))
