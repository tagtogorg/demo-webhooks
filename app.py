from flask import Flask, request, Response
import json
import spacy
import requests
import os

def get_class_id(label):
  """Translates the spaCy label id into the tagtog entity type id"""
  choices = {'PERSON': 'e_1', 'ORG': 'e_2', 'MONEY': 'e_3'}
  return choices.get(label, None)


def get_entities(spans, pipeline):
  """
  Translates a tuple of named entity Span objects (https://spacy.io/api/span) to list of tagtog entities (https://docs.tagtog.net/anndoc.html#ann-json)
  spans: the named entities in the spaCy doc
  pipeline: trained pipeline name
  """
  default_prob = 1
  default_part_id = 's1v1'
  default_state = 'pre-added'
  tagtog_entities = []
  for span in spans:
    class_id = get_class_id(span.label_)
    if class_id is not None:
      tagtog_entities.append( {# entity type id
                        'classId': class_id,
                        'part': default_part_id,
                        # entity offset
                        'offsets':[{'start': span.start_char, 'text': span.text}],
                        # entity confidence object (annotation status, who created it and probabilty)
                        'confidence': {'state': default_state,'who': ['ml:' + pipeline],'prob': default_prob},
                        # no entity labels (fields)
                        'fields':{},
                        # this is related to the kb_id (knowledge base ID) field from the Span spaCy object
                        'normalizations': {}} )
  return tagtog_entities

# Set your credentials at tagtog
MY_USERNAME = os.environ['MY_TAGTOG_USERNAME']
MY_PASSWORD = os.environ['MY_TAGTOG_PASSWORD']

# Set tagtog project name
MY_PROJECT = 'demo-webhook'

# API authentication
tagtog_API_endpoint = "https://www.tagtog.net/-api/documents/v1"
auth = requests.auth.HTTPBasicAuth(username=MY_USERNAME, password=MY_PASSWORD)

# Parameters for the GET API call to get a document
# (see https://docs.tagtog.net/API_documents_v1.html#examples-get-the-original-document-by-document-id)
get_params_doc = {'owner': MY_USERNAME, 'project': MY_PROJECT, 'output': 'text'}
# Parameters for the POST API call to import a pre-annotated document
# (see https://docs.tagtog.net/API_documents_v1.html#examples-import-pre-annotated-plain-text-file)
post_params_doc = {'owner': MY_USERNAME, 'project': MY_PROJECT, 'output': 'null', 'format': 'default-plus-annjson'}

app = Flask(__name__)

# Handle any POST request coming to the app root path
@app.route('/', methods=['POST'])
def respond():
  print(request.json)
  if request.json['tagtogID']:
    # Add the doc ID to the parameters
    get_params_doc['ids'] = request.json['tagtogID']
    print(request.json['tagtogID'])
    get_response = requests.get(tagtog_API_endpoint, params=get_params_doc, auth=auth)

    # Load the spaCy trained pipeline (https://spacy.io/models/en#en_core_web_sm) and apply it to text
    pipeline = 'en_core_web_sm'
    nlp = spacy.load(pipeline)
    doc = nlp(get_response.text)

    # Initialize ann.json (specification: https://docs.tagtog.net/anndoc.html#ann-json)
    annjson = {}
    # Set the document as not confirmed, an annotator will manually confirm whether the annotations are correct
    annjson['anncomplete'] = False
    annjson['metas'] = {}
    annjson['relations'] = []
    # Transform the spaCy entities into tagtog entities
    annjson['entities'] = get_entities(doc.ents, pipeline)

    # Pre-annotated document composed of the content and the annotations
    files=[('text.txt', get_response.text), ('text.ann.json', json.dumps(annjson))]
    post_response = requests.post(tagtog_API_endpoint, params=post_params_doc, auth=auth, files=files)
    print(post_response.text)

  return Response()

if __name__ == "__main__":
  app.run()






