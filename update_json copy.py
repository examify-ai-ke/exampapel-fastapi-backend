import json
from pathlib import Path


def process_locations(input_file):
    # Load the JSON data
    with open(input_file, "r") as f:
        data = json.load(f)

    # Process each institution
    for institution in data["institutions"]:
        original = institution["name"]
        # # Convert to title case and add County
        # institution["name"] = f"{original.strip().title()}"
        # print(institution["name"])
        # Remove programs field if it exists
        # institution.pop("programs", None)
        # New tags field
        # institution["tags"] = generate_tags(institution)

    # Save back to the same file
    output_file = input_file
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def generate_tags(institution):
    name = institution.get("name", "").lower()
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
    if "ttc" in name:
        tags.append("TTC")
    if "national" in name:
        tags.append("National Institution")

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
    input_json = Path("kuccps_institutions_2025-04-26-master-UPDATED.json")
    process_locations(input_json)
