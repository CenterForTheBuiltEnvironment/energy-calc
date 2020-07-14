import csv
import pickle

__DB__ = "db/db.csv"
__pickle_file__ = "db/db.pickle"

reader = csv.reader(open(__DB__, 'r'))
keys = reader.next()

db = [] 
for row in reader:
    r = dict(zip(keys, row))
    db.append(r)

pickle.dump(db, open(__pickle_file__, 'w'))
