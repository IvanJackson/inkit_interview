#!/usr/bin/env python3
"""Test Flask app initialization and route registration."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Set environment
os.environ['FLASK_ENV'] = 'development'

# Create app
app = create_app('development')

print('✓ Flask app created successfully')
print(f'✓ Upload folder: {app.config["UPLOAD_FOLDER"]}')
print(f'✓ Max file size: {app.config["MAX_CONTENT_LENGTH"] / (1024*1024):.0f}MB')
print(f'✓ Session timeout: {app.config["SESSION_TIMEOUT_HOURS"]}h')
print(f'\n✓ Configured routes:')
for rule in app.url_map.iter_rules():
    if rule.endpoint not in ['static']:
        methods = rule.methods - {"HEAD", "OPTIONS"}
        print(f'  - {rule.rule:<30} {sorted(methods)}')

print('\n✅ App initialization test PASSED')
