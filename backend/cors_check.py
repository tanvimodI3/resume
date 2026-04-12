import httpx
import traceback

url = 'http://127.0.0.1:8000/auth/signup'
headers = {
    'Origin': 'http://localhost:5175',
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'content-type'
}

try:
    with httpx.Client() as client:
        opt = client.options(url, headers=headers, timeout=10)
        print('OPTIONS', opt.status_code)
        print(dict(opt.headers))
        resp = client.post(
            url,
            headers={'Origin': 'http://localhost:5175', 'Content-Type': 'application/json'},
            json={'name':'test','email':'test@example.com','password':'pass'},
            timeout=10
        )
        print('POST', resp.status_code)
        print(dict(resp.headers))
        print(resp.text)
except Exception:
    traceback.print_exc()
