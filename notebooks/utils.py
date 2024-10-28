# import textgrid
import jiwer
import re

# def extract_text_from_textgrid(file_path, tier_name=None):
#     # Load the TextGrid file
#     tg = textgrid.TextGrid.fromFile(file_path)
    
#     # Find the relevant tier (if tier_name is provided)
#     if tier_name:
#         tier = tg.getFirst(tier_name)
#     else:
#         # If no specific tier is mentioned, extract from the first tier
#         tier = tg[0]

#     # Extract the intervals with text and concatenate them
#     extracted_text = []
#     for interval in tier:
#         if interval.mark.strip():  # Only consider non-empty intervals
#             extracted_text.append(interval.mark)
    
#     # Return all the concatenated text
#     return " ".join(extracted_text)


def extract_text_from_tg(tg):    # uses praat-textgrids package
    # Extract the intervals with text and concatenate them
    extracted_text = []
    for tier in tg.values():
          for interval in tier:
              if interval.text.strip():
                  extracted_text.append(interval.text)

    return " ".join(extracted_text)


def remove_intents(text):
    """
    Remove intents marked by <UNSURE>, <UNIN/>, etc. from the text.
    """
    # Regular expression pattern to match any text within angle brackets including the brackets
    pattern = r'<[^>]*>'
    # Use re.sub to replace matches with an empty string
    cleaned_text = re.sub(pattern, '', text)
    # Optionally, you can remove extra spaces left after removing tags
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def transform(reference_text, hypothesis_text):
    # Normalize the text by transforming it to lower case and removing punctuation
    transformation = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.ExpandCommonEnglishContractions(),
        jiwer.RemoveKaldiNonWords(),
        jiwer.RemovePunctuation()
    ])

    ref = transformation(reference_text)
    hyp = transformation(hypothesis_text)

    return ref, hyp

def get_metrics(ref, hyp):
    ref, hyp = transform(ref, hyp)
    
    # Calculate alignment metrics
    measures = jiwer.compute_measures(ref, hyp)
    return measures['mer'], measures['wil'], measures['wip'], measures['wer']


def visualize_alignment(ref, hyp):
    ref, hyp = transform(ref, hyp)
    # visual alignment 
    out = jiwer.process_words(ref, hyp)
    print(jiwer.visualize_alignment(out))