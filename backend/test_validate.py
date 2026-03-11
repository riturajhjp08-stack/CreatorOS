import time

try:
    print("starting")
    t1 = time.time()
    from utils.auth_security import validate_email_address
    print("imported")
    ok, email, err = validate_email_address("localtest@example.com")
    print("done in", time.time() - t1, "seconds:", ok, email)
except Exception as e:
    print("error:", e)
