import hashlib

def generate_token(doctor):
    raw = f"{doctor.email}:{doctor.password}"
    return hashlib.sha256(raw.encode()).hexdigest()