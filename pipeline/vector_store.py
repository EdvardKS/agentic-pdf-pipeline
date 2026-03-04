vector_store = []

def add_vectors(vectors):
    global vector_store
    vector_store.extend(vectors)

def get_vectors():
    return vector_store