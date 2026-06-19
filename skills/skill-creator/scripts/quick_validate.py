#!/usr/bin/env python3
"""
Quick validation script for skills - minimal version
"""

import sys
import os
import re
import yaml
from pathlib import Path

COMPATIBILITY_KEYS = {'runtimes'}
RUNTIME_IDS = {'claude_code', 'codex', 'portable'}
UNSPECIFIED_RUNTIME = 'unspecified'

def validate_compatibility(frontmatter):
    """Validate optional runtime compatibility metadata."""
    if 'compatibility' not in frontmatter:
        return None
    compatibility = frontmatter['compatibility']
    if not isinstance(compatibility, dict):
        return f"Compatibility must be a YAML mapping, got {type(compatibility).__name__}"
    unexpected_keys = {str(key) for key in compatibility if key not in COMPATIBILITY_KEYS}
    if unexpected_keys:
        return f"Unexpected compatibility key(s): {', '.join(sorted(unexpected_keys))}"
    runtimes = compatibility.get('runtimes')
    if not isinstance(runtimes, list) or not runtimes:
        return "Compatibility runtimes must be a non-empty list"
    seen = set()
    for runtime in runtimes:
        if not isinstance(runtime, str) or runtime != runtime.strip() or not runtime:
            return "Compatibility runtimes must contain only non-empty strings"
        if runtime == UNSPECIFIED_RUNTIME:
            return "Compatibility must not declare unspecified; omit compatibility metadata instead"
        if runtime not in RUNTIME_IDS:
            return f"Unsupported compatibility runtime '{runtime}'. Allowed runtimes: {', '.join(sorted(RUNTIME_IDS))}"
        if runtime in seen:
            return f"Duplicate compatibility runtime '{runtime}'"
        seen.add(runtime)
    return None

def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Read and validate frontmatter
    content = skill_md.read_text()
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Define allowed properties
    ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    if 'name' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description' not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # Extract name for validation
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        # Check naming convention (kebab-case: lowercase with hyphens)
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        # Check name length (max 64 characters per spec)
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Extract and validate description
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"
        # Check description length (max 1024 characters per spec)
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    # Validate compatibility field if present (optional)
    compatibility_error = validate_compatibility(frontmatter)
    if compatibility_error:
        return False, compatibility_error

    return True, "Skill is valid!"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)
    
    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
