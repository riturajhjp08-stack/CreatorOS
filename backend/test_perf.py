import time
from werkzeug.security import generate_password_hash
from email_validator import validate_email

def test():
    t0 = time.time()
    validate_email("test@example.com", check_deliverability=False)
    print("validate_email took:", time.time() - t0)

    t0 = time.time()
    generate_password_hash("Password123!")
    print("generate_password_hash took:", time.time() - t0)

if __name__ == "__main__":
    test()
