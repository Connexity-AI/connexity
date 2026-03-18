const loginActionResponse = {
  data: { message: 'Login successful' },
  response: /* Response */ {
    status: 200,
    statusText: 'OK',
    headers: /* Headers */ {
      date: 'Tue, 28 Oct 2025 20:45:34 GMT',
      server: 'uvicorn',
      'content-length': '30',
      'content-type': 'application/json',
      'set-cookie': 'auth_cookie=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjIzNzU1MzUsInN1YiI6IjBkMDc5MWExLWVjNzMtNGIyNy1iYjg3LWIyMzhiNzM4ZjYyZCJ9.QrePbmqz0zbFIfzt4DL3d3npOnqLXOITafCx82RA2bM; expires=Tue, 28 Oct 2025 21:45:35 GMT; HttpOnly; Max-Age=3600; Path=/; SameSite=lax'
    },
    body: /* ReadableStream */ { locked: true, state: 'closed', supportsBYOB: true },
    bodyUsed: true,
    ok: true,
    redirected: false,
    type: 'default',
    url: 'http://localhost:8000/api/v1/login/access-token'
  }
}
