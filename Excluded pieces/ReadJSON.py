import json
import ast
base = []

with open('DB.json') as json_data:
    print "Loading. . ."
    openedJson = json.load(json_data)
for listitem in openedJson:
    print listitem

with open("taskBase127.0.0.1_19114.json", 'w') as outfile: #czyszczenie jsona
    json.dump(base, outfile)
