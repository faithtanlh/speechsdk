import os
import time
import azure.cognitiveservices.speech as speechsdk

def conversation_transcriber_session_started_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStarted event')

def conversation_transcriber_session_stopped_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStopped event')

def conversation_transcriber_recognition_canceled_cb(evt: speechsdk.SessionEventArgs):
    print('Canceled event')

def conversation_transcriber_transcribed_cb(evt: speechsdk.SpeechRecognitionEventArgs):
    print('\nTRANSCRIBED:')
    if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f'\tSpeaker ID={evt.result.speaker_id}')
        print(f'\tText={evt.result.text}')
    elif evt.result.reason == speechsdk.ResultReason.NoMatch:
        print(f'\tNOMATCH: Speech could not be TRANSCRIBED: {evt.result.no_match_details}')

# Initialize variables to hold previously recognized text and speaker ID for comparison
recognized_text = ""
current_speaker_id = None

def conversation_transcriber_transcribing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
    global recognized_text, current_speaker_id
    new_text = evt.result.text.strip()

    # Get speaker ID for current segment
    speaker_id = evt.result.speaker_id if hasattr(evt.result, 'speaker_id') else "Unknown"

    # If the speaker changes or new text is recognized, update and print progressively
    if new_text != recognized_text or speaker_id != current_speaker_id:
        recognized_text = new_text
        current_speaker_id = speaker_id

        # Clear the current line and print progressively with speaker ID in the same line
        print(f'\rTRANSCRIBING : SPEAKER ID = {current_speaker_id} | TEXT = {recognized_text}', end='', flush=True)

def recognize():
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('AZURE_SPEECH_KEY'), region=os.environ.get('AZURE_SPEECH_REGION'))
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-SG", "zh-CN", "ms-MY", "hi-IN"])
    speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')
    speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults, value='true')

    conversation_transcriber = speechsdk.transcription.ConversationTranscriber(
        speech_config=speech_config, 
        audio_config=audio_config, 
        auto_detect_source_language_config=auto_detect_source_language_config
    )

    transcribing_stop = False

    def stop_cb(evt: speechsdk.SessionEventArgs):
        print('CLOSING on {}'.format(evt))
        nonlocal transcribing_stop
        transcribing_stop = True

    # Connect callbacks to the events fired by the conversation transcriber
    conversation_transcriber.transcribed.connect(conversation_transcriber_transcribed_cb)
    conversation_transcriber.transcribing.connect(conversation_transcriber_transcribing_cb)
    conversation_transcriber.session_started.connect(conversation_transcriber_session_started_cb)
    conversation_transcriber.session_stopped.connect(conversation_transcriber_session_stopped_cb)
    conversation_transcriber.canceled.connect(conversation_transcriber_recognition_canceled_cb)
    # stop transcribing on either session stopped or canceled events
    conversation_transcriber.session_stopped.connect(stop_cb)
    conversation_transcriber.canceled.connect(stop_cb)

    conversation_transcriber.start_transcribing_async()

    # Waits for completion.
    while not transcribing_stop:
        time.sleep(.3)   # how fast transcribed text is outputted (how fast each audio segment is processed)

    conversation_transcriber.stop_transcribing_async()

# Main
try:
    recognize()
except KeyboardInterrupt:
    print("Keyboard Interruption.")
    print("Closing websocket...")
except Exception as err:
    print("Encountered exception. {}".format(err))