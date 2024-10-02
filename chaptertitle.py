from openai import AzureOpenAI

# Set up Azure OpenAI client
def setup_openai_client(api_key, api_endpoint, api_version="2024-02-01"):
    client = AzureOpenAI(
        api_version=api_version,
        api_key=api_key,
        azure_endpoint=api_endpoint,
    )
    return client

# Function to generate chapter titles using Azure OpenAI
def generate_chapter_title(text, api_key, api_endpoint):
    # Initialize Azure OpenAI client
    client = setup_openai_client(api_key, api_endpoint)

    # Slightly modify the text (add a space or character to break any potential caching)
    text = text + " "

    # The prompt asks for a brief summary suitable as a chapter title
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that generates concise chapter titles based on text."
        },
        {
            "role": "user",
            "content": f"Generate a concise chapter title for the following text:\n\n{text}. Don't include a heading such as 'Chapter Title:'."
        }
    ]

    # Request to the Azure OpenAI API using chat completions
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Replace with your Azure GPT model deployment name, e.g., 'gpt-35-turbo'
        messages=messages,
        max_tokens=20,  # Limit tokens for shorter, concise titles
        temperature=0.7,  # Adjust to control creativity level
        n=1,  # Number of responses
    )

    # Extract and return the generated title
    title = completion.choices[0].message.content.strip()
    return title
