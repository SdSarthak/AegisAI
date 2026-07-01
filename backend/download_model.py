import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# We use the tiny HuggingFace stub model from your test suite
model_id = "hf-internal-testing/tiny-random-DebertaV2ForSequenceClassification"
save_path = "./app/modules/guard/models/classifier"

print(f"Downloading stub model to {save_path}...")
os.makedirs(save_path, exist_ok=True)

# Fetch and save the tokenizer and model
tok = AutoTokenizer.from_pretrained(model_id)

# ADDED ignore_mismatched_sizes=True to force a new 3-label classification head
mdl = AutoModelForSequenceClassification.from_pretrained(
    model_id, 
    num_labels=3, 
    ignore_mismatched_sizes=True
)

tok.save_pretrained(save_path)
mdl.save_pretrained(save_path)

print("Model downloaded and saved successfully!")