import csv
import pickle
import os

__DB__ = os.path.join(os.getcwd(), "db", "db.csv")
__pickle_file__ = os.path.join(os.getcwd(), "db", "db.pickle")

reader = csv.reader(open(__DB__, "r"))
keys = next(reader)


db = []
for row in reader:
    r = dict(zip(keys, row))
    db.append(r)

pickle.dump(db, open(__pickle_file__, "wb"))
