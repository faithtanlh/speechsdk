import os
from openai import AzureOpenAI
    
client = AzureOpenAI(
    api_key='9a7214af1f5a46eb8f4fb91f8745d4d5',
    api_version="2024-02-01",
    azure_endpoint = 'https://shs-openai-01.openai.azure.com/'
)

deployment_id = 'shs-whisper' #This will correspond to the custom name you chose for your deployment when you deployed a model."
audio_test_file = '/Users/lihuicham/Documents/GitHub/speechsdk/data/nsc/3010_short.wav'

result = client.audio.transcriptions.create(
    file=open(audio_test_file, "rb"),            
    model=deployment_id,
    # Specify the language. Enter the language to translate here too. 
    # For Singlish, we might need to specify "en", else default might be transcripted to malay
    language="zh",  # en
    prompt="This is a medical consultation between a doctor and a patient.",  # You can give a prompt to guide the transcription
    response_format="text",  # Format options could be "text", "json", etc.
)

print(result)