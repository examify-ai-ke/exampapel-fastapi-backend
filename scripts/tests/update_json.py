import json
from pathlib import Path


def process_locations(input_file):
    # Load the JSON data
    with open(input_file, "r") as f:
        data = json.load(f)

    # Process each institution
    for institution in data["institutions"]:
        original = institution["county"]
        # # Convert to title case and add County
        if "county" not in original.strip().lower():
            original = original.strip().title() + " County"
        institution["county"] = original
        # institution["name"] = f"{original.strip().title()}"
        
        # print(institution["name"])
        # Remove programs field if it exists
        # institution.pop("location", None)
        # New tags field
        # institution["tags"] = generate_tags(institution)

    # Save back to the same file
    output_file = input_file
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def generate_tags(institution):
    name = institution.get("name", "").lower()
    key = institution.get("key", "").lower()
    description = institution.get("description", "").lower()
    tags = []

    # Institution type tags
    for pattern in ["university", "college", "polytechnic", "institute"]:
        if pattern in name:
            tags.append(pattern.title())

    # Program focus tags
    for subject in [
        "technical",
        "medical",
        "teachers",
        "agriculture",
        "business",
        "engineering",
        "science",
        "technology",
    ]:
        if subject in description or subject in name:
            tags.append(subject.title())

    # Qualification level tags
    for level in ["diploma", "certificate", "degree", "postgraduate"]:
        if level in description:
            tags.append(f"{level.title()} Programs")

    # Unique identifier tags
    if "ttc" in name or "ttc" in key:
        tags.append("TTC")
    if "tvet" in name or "tvet" in key:
        tags.append("TVET")
    if "tvc" in name or "tvc" in key:
        tags.append("TVC")
    if "tti" in name or "tti" in key:
        tags.append("TTI")
    if "national" in name or "national" in key:
        tags.append("National")
    if "vocational" in name or "vocational" in key:
        tags.append("Vocational")
    if "polytechnic" in name or "polytechnic" in key:
        tags.append("Polytechnic")
    if "university" in name or "university" in key:
        tags.append("University")
    if "college" in name or "college" in key:
        tags.append("College")
    if "institute" in name or "institute" in key:
        tags.append("Institute")
    if "technical" in name or "technical" in key:
        tags.append("Technical")

    # Ensure unique tags and fill up to 4
    tags = list(set(tags))[:4]

    # Default tags if empty
    if not tags:
        return [
            "Higher Education",
            "Vocational Training",
            "Accredited",
            "Kenyan Institution",
        ]

    return tags


if __name__ == "__main__":
    input_json = Path(
        "/home/oligarch/WORK/exampapel-fastapi-backend/backend/app/kuccps_institutions_2025-04-26-master-UPDATED.json"
    )
    process_locations(input_json)
