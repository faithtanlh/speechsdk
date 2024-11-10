import torch 
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def main():
    # Define the paths
    model_dir = "C:/Users/adell/OneDrive/Documents/Capstone/SDOH/Social-Determinants-of-Health-Through-NLP/TrainedBase5"

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)

    # Move model to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Function to predict a premise and hypothesis
    def predict_single(premise, hypothesis):
        # Tokenize the input
        inputs = tokenizer(premise, hypothesis, return_tensors="pt", padding="max_length", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Model inference
        with torch.no_grad():
            outputs = model(**inputs)

        # Get the predicted label
        prediction = torch.argmax(outputs.logits, dim=-1).item()

        return prediction

    # Manually input your premise
    premise = """
    He does consume alcohol, mostly on the weekends. He drinks about 2 alcoholic beverages per day. 
    He is also a smoker. The patient is currently a working adult in Singhealth.
    """


    # List of hypotheses
    hypotheses = [
        "Patient consumes alcohol",
        "Patient smokes",
        "Patient is a student"
    ]

    # Loop through each hypothesis and make a prediction
    for i, hypothesis in enumerate(hypotheses):
        predicted_label = predict_single(premise, hypothesis)
        print(f"Hypothesis {i+1}: {hypothesis}")
        print(f"Predicted Label: {predicted_label}\n")

if __name__ == "__main__":
    main()
