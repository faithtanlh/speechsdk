

#!pip install matplotlib

#!pip install datasets transformers numpy scikit-learn

#!pip install transformers[torch]

#!pip install datasets



# [Author: Sai Kiran Gandluri(02144549)]
# [Date: 03-22-2024]

import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_fscore_support

def tokenize_function(examples, tokenizer):
    return tokenizer(examples['premise'], examples['hypothesis'], padding="max_length", truncation=True, max_length=512)

def evaluate_model(trainer, dataset):
    predictions = trainer.predict(dataset).predictions
    predictions = np.argmax(predictions, axis=1)
    labels = dataset['label']
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predictions, average='macro')
    return precision, recall, f1

def main():
    # Initialize tokenizer and load pre-trained model
    tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')

    # Load datasets from CSV files
    train_dataset = load_dataset('csv', data_files='C:/Users/adell/OneDrive/Documents/Capstone/SDOH/data/sdoh_nli_train.csv')['train']
    val_dataset = load_dataset('csv', data_files='C:/Users/adell/OneDrive/Documents/Capstone/SDOH/data/sdoh_nli_validation.csv')['train']
    test_dataset = load_dataset('csv', data_files='C:/Users/adell/OneDrive/Documents/Capstone/SDOH/data/sdoh_nli_test.csv')['train']

    # Tokenize datasets
    train_dataset = train_dataset.map(lambda examples: tokenize_function(examples, tokenizer), batched=True)
    val_dataset = val_dataset.map(lambda examples: tokenize_function(examples, tokenizer), batched=True)
    test_dataset = test_dataset.map(lambda examples: tokenize_function(examples, tokenizer), batched=True)

    # Activate GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load pre-trained model for sequence classification and move it to GPU if available
    model = AutoModelForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)
    model.to(device)

    # Define training arguments with 5 epochs and other configurations
    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=5,  
        per_device_train_batch_size=12,
        per_device_eval_batch_size=6,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        evaluation_strategy="epoch",
        save_strategy="epoch",  # Save after every epoch
    )

    # Fine-tune the model
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )
    trainer.train()

    # Save the trained model and tokenizer to the specified directory
    model_dir = "C:/Users/adell/OneDrive/Documents/Capstone/SDOH/Social-Determinants-of-Health-Through-NLP/Models"
    
    # Use trainer.save_model() to save the trained model
    trainer.save_model(model_dir)  # Saves the trained model, not the base model
    tokenizer.save_pretrained(model_dir)  # Saving the tokenizer

    print(f"Trained model and tokenizer saved to {model_dir}")

    # Evaluate the trained model on validation and test datasets
    metrics = []
    for dataset, name in zip([val_dataset, test_dataset], ["Validation", "Test"]):
        precision, recall, f1 = evaluate_model(trainer, dataset)
        metrics.append((precision, recall, f1))
        print(f"{name} Results - Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

    # Plotting the metrics
    datasets = ["Validation", "Test"]
    precisions = [m[0] for m in metrics]
    recalls = [m[1] for m in metrics]
    f1_scores = [m[2] for m in metrics]

    plt.plot(datasets, precisions, label='Precision', marker='o')
    plt.plot(datasets, recalls, label='Recall', marker='x')
    plt.plot(datasets, f1_scores, label='F1 Score', marker='s')

    plt.title('Model Performance Metrics Across Datasets')
    plt.ylabel('Scores')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()

