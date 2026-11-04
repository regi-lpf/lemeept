import json
from pathlib import Path

# Step 1: Open the JSON Sample
json_file_path = Path('dados/revisao/classificacao_assistida_6_v4.json')

# Step 2: Load the JSON data
with json_file_path.open('r', encoding='utf-8') as file:
    data = json.load(file)

# Step 3: Review the classifications for specific items
items_to_review = ['EPT-0007', 'EPT-0001', 'EPT-0003', 'EPT-0010', 'EPT-0005']

# Step 4: Update the `valor` field based on manual review decisions
# For demonstration purposes, let's assume we have a dictionary of manual review decisions
manual_review_decisions = {
    'EPT-0007': 'new_value_1',
    'EPT-0001': 'new_value_2',
    'EPT-0003': 'new_value_3',
    'EPT-0010': 'new_value_4',
    'EPT-0005': None  # Preserve null for items without a confirmed base epistemológica
}

for item in data:
    if item['id'] in items_to_review:
        item['valor'] = manual_review_decisions[item['id']]

# Step 5: Save the updated JSON data
with json_file_path.open('w', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=4)

print("JSON sample updated successfully.")
