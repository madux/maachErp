import enum
from firebase_admin.db import reference as realtime
from firebase_admin.firestore import client as cfs

from google.cloud import firestore


# CFS io
def fs_client(app) -> firestore.Client:
    # we use firebase_admin.firestore which takes the app info and returns firestore.Client
    return cfs(app)


def cfs_ref(cfs, path, doc_id=None):
    if doc_id:
        path = '%s/%s' %(path, doc_id)
        return cfs.document(path)
    else:
        return cfs.collection(path)


def read_cfs(cfs, path, doc_id=None):
    if doc_id:
        return cfs_ref(cfs, path, doc_id).get().to_dict()
    else:
        return [i.to_dict() for i in cfs_ref(cfs, path, doc_id).get()]


def write_cfs(cfs, path, value, doc_id=None):
    return cfs_ref(cfs, path, doc_id).set(value)